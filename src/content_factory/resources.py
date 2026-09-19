"""Resource policy: admit, serialize, accelerate or abort a heavy job.

:mod:`content_factory.hardware` measures the machine; this module decides what to
do with it. This project runs on a laptop with one 8 GB GPU that is also driving
the desktop, so the question is never "can this use the GPU?" but "should this use
the GPU **right now**, and what happens if the machine changes its mind halfway?".

Three decisions, each with a different timescale:

* **Which encoder, and on which ffmpeg build.** ``resolve_hardware_encoder``
  opens every *(build, encoder)* pair it can find and keeps the first that really
  starts. Builds matter because they target different NVENC API versions: a
  current ffmpeg can be refused by the installed driver while a bundled older
  build encodes on the same GPU without complaint.
* **Whether the job may start now.** :meth:`ResourceGovernor.begin` serializes
  heavy work, then walks a degradation ladder:

  1. **No GPU, or policy says CPU** → run on CPU.
  2. **Another heavy job is running** → wait for the slot, so the machine stays
     responsive; the wait is reported.
  3. **GPU too hot, saturated, or short of free VRAM** → poll with a backoff
     until it cools or frees, up to ``gpu_wait_seconds``.
  4. **Still busy after that** → run on CPU and record *why*, instead of blocking
     forever or failing the job.

* **Whether a job already running must stop.**
  :meth:`ResourceGovernor.pressure_violation` answers that against much more
  serious thresholds than admission uses, so ordinary load never kills work —
  only a machine walking into swap or past its thermal ceiling does.

Nothing here is a guess about correctness: the profile is measured, every decision
carries its reason, and the counters are exposed through ``GET /resources`` so the
behaviour can be inspected rather than believed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from .compute import (
    _AUTO_ENCODER_PREFERENCE,
    _HEAVY,
    _REQUESTABLE_ENCODERS,
    _VRAM_MB,
    Admission,
    CodecChoice,
    Decision,
    FfmpegBuild,
    GpuInfo,
    HardwareProfile,
    JobKind,
)
from .config import Settings, get_settings
from .hardware import discover_binaries, machine_pressure, probe, probe_encoder

__all__ = [
    # Re-exported so the many modules (and tests) that have always imported the
    # compute vocabulary from here keep working unchanged.
    "Admission",
    "CodecChoice",
    "Decision",
    "FfmpegBuild",
    "GpuInfo",
    "HardwareProfile",
    "JobKind",
    "ResourceGovernor",
    "default_governor",
    "discover_binaries",
    "machine_pressure",
    "probe",
    "probe_encoder",
]


@dataclass
class _Stats:
    jobs_started: int = 0
    gpu_jobs: int = 0
    cpu_jobs: int = 0
    degraded_jobs: int = 0
    serialized_jobs: int = 0
    total_wait_seconds: float = 0.0
    longest_wait_seconds: float = 0.0
    encoder_fallbacks: int = 0
    last_encoder: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobs_started": self.jobs_started,
            "gpu_jobs": self.gpu_jobs,
            "cpu_jobs": self.cpu_jobs,
            "degraded_jobs": self.degraded_jobs,
            "serialized_jobs": self.serialized_jobs,
            "total_wait_seconds": round(self.total_wait_seconds, 2),
            "longest_wait_seconds": round(self.longest_wait_seconds, 2),
            "encoder_fallbacks": self.encoder_fallbacks,
            "last_encoder": self.last_encoder,
        }


class ResourceGovernor:
    """Serialize heavy jobs and decide, per job, between GPU and CPU.

    One instance per service. All decisions are recorded, so ``snapshot()`` can
    answer "why is this render slow?" with the actual reason.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        probe_fn: Callable[[], HardwareProfile] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        encoder_probe: Callable[[str, str], tuple[bool, str]] = probe_encoder,
        pressure: Callable[[], tuple[int, int | None]] | None = None,
    ) -> None:
        self._settings = settings
        self._pressure = pressure or machine_pressure
        self._probe = probe_fn or (
            lambda: probe(
                ffmpeg_binary=settings.ffmpeg_binary,
                extra_binaries=settings.ffmpeg_extra_binaries,
            )
        )
        self._clock = clock
        self._sleep = sleep
        self._encoder_probe = encoder_probe
        #: (ffmpeg path, encoder name) -> (usable, note), checked once with a
        #: real one-frame encode. Keyed by the pair, never the name alone: the
        #: same encoder name is a different capability on a different build.
        self._encoder_checks: dict[tuple[str, str], tuple[bool, str]] = {}
        self._lock = threading.Lock()
        self._slot_free = threading.Condition(self._lock)
        self._profile: HardwareProfile | None = None
        self._profile_age = 0.0
        self._heavy_active = 0
        self._gpu_active = 0
        self._stats = _Stats()
        self._last_decision: Decision | None = None

    # --- profile -------------------------------------------------------------

    def profile(self, *, refresh: bool = False) -> HardwareProfile:
        """Cached hardware profile (``profile_ttl_seconds``), re-probed on demand."""
        now = self._clock()
        with self._lock:
            fresh = (
                self._profile is not None
                and now - self._profile_age < self._settings.profile_ttl_seconds
            )
            if fresh and not refresh:
                return self._profile  # type: ignore[return-value]
        measured = self._probe()
        with self._lock:
            self._profile = measured
            self._profile_age = now
        return measured

    # --- policy --------------------------------------------------------------

    @property
    def gpu_allowed(self) -> bool:
        """Whether the configuration permits GPU work at all."""
        return self._settings.compute_policy != "cpu"

    @property
    def settings(self) -> Settings:
        return self._settings

    def decoder_args(self, export_format: str = "mp4") -> tuple[str, ...]:
        """Hardware *decode* flags for source video. Empty unless asked for.

        ``auto`` means **off**, and that is a measured decision rather than
        caution. Decode acceleration only pays when the decoded frames stay on
        the GPU for the rest of the pipeline. This project's filter graph (scale,
        crop, drawtext) and its software encoder both run on the CPU, so every
        frame is uploaded and then downloaded again over PCIe — a full round trip
        bought for nothing. Measured on the RTX 4060 laptop this targets, reading
        one clip and discarding it:

        ====================  ==========  ==========  ==========
        source                software    -cuda       -d3d11va
        ====================  ==========  ==========  ==========
        3s 720p               120ms       955ms       273ms
        60s 1080p             626ms       1914ms      2139ms
        20s 4K                812ms       2292ms      2604ms
        ====================  ==========  ==========  ==========

        Hardware decode loses at every size here, so opting in is the only way
        to get it. Pass an explicit name (``render_hwaccel: "cuda"``) when the
        graph is GPU-resident, and the render will still retry without it.
        """
        mode = (self._settings.render_hwaccel or "auto").strip().lower()
        if mode in {"off", "none", "cpu", "", "auto"} or not self.gpu_allowed:
            return ()
        if export_format != "mp4":
            return ()
        available = self.profile().hwaccels
        return ("-hwaccel", mode) if mode in available else ()

    # --- encoder selection ---------------------------------------------------

    def _wanted_encoders(self) -> tuple[str, ...]:
        """Encoders to try, in order, given ``render_encoder``."""
        requested = (self._settings.render_encoder or "auto").strip().lower()
        named = _REQUESTABLE_ENCODERS.get(requested)
        return (named,) if named else _AUTO_ENCODER_PREFERENCE

    def _builds_for(self, encoder: str) -> tuple[str, ...]:
        """Paths of discovered builds that list ``encoder``, primary first."""
        profile = self.profile()
        if not profile.binaries:
            # A profile built by hand (tests, or a caller passing its own
            # profile object) describes exactly one build through the flat
            # fields. Treat it as that build instead of finding nothing.
            if profile.ffmpeg and encoder in profile.encoders:
                return (profile.ffmpeg,)
            return ()
        return tuple(
            build.path for build in profile.binaries if encoder in build.encoders
        )

    def resolve_hardware_encoder(self) -> tuple[str, str] | None:
        """``(binary, encoder)`` that provably starts, or ``None`` for software.

        An encoder name is not a capability: the same ``h264_nvenc`` may start on
        one ffmpeg build and be refused by the driver on another, because builds
        target different NVENC API versions. So every *(build, encoder)* pair is
        opened for real (one frame, cacheable) and only a pair that succeeds is
        returned. Encoder preference outranks build preference — a GPU encoder on
        a secondary build beats a software fallback on the primary one.
        """
        requested = (self._settings.render_encoder or "").strip().lower()
        if requested == "cpu" or not self.gpu_allowed:
            return None
        for encoder in self._wanted_encoders():
            for binary in self._builds_for(encoder):
                usable, _note = self.check_encoder(encoder, binary)
                if usable:
                    return binary, encoder
        return None

    def encoder_status(self) -> dict[str, Any]:
        """Whether a hardware encoder exists *and* can really start on this machine.

        Reports the first *wanted* encoder that any build lists, together with the
        verdict for the best build carrying it — so a machine where NVENC exists
        but the driver refuses it still answers ``h264_nvenc / unusable + why``
        rather than a vague "no hardware encoder".
        """
        requested = (self._settings.render_encoder or "").strip().lower()
        named = _REQUESTABLE_ENCODERS.get(requested)
        for encoder in self._wanted_encoders():
            builds = self._builds_for(encoder)
            if not builds:
                continue
            usable, note = self.check_encoder(encoder, builds[0])
            return {
                "encoder": encoder,
                "binary": builds[0],
                "usable": usable,
                "note": note,
            }
        if named is not None:
            return {
                "encoder": None,
                "binary": None,
                "usable": False,
                "note": f"{named} is requested but no ffmpeg build has it",
            }
        return {
            "encoder": None,
            "binary": None,
            "usable": False,
            "note": "no ffmpeg build exposes a hardware H.264 encoder",
        }

    def check_encoder(
        self, encoder: str, binary: str | None = None
    ) -> tuple[bool, str]:
        """Probe one *(binary, encoder)* pair once per process, sharing the cache.

        ``binary=None`` means the primary build. A probe costs a real ffmpeg
        start, so the verdict is cached: an encoder the driver refuses will not
        start on the next export either.
        """
        target = binary or self.profile().ffmpeg or "ffmpeg"
        key = (target, encoder)
        with self._lock:
            cached = self._encoder_checks.get(key)
        if cached is None:
            cached = self._encoder_probe(target, encoder)
            with self._lock:
                self._encoder_checks[key] = cached
        return cached

    def video_codec(self, export_format: str) -> CodecChoice:
        """Pick the encoder for an export: hardware when it really starts.

        Hardware encode is preferred even though the raw speed-up over software
        is modest at 1080p, because the point on a laptop is *where* the work
        happens: an NVENC export leaves the CPU free, so the machine stays
        responsive while it encodes. Measured with this pipeline's own
        single-threaded setting (600 frames at 1080x1920): libx264 4791ms versus
        h264_nvenc 3095ms, and 4697ms versus 2072ms once the filter threads are
        counted too.
        """
        cpu = _cpu_codec(export_format)
        if export_format != "mp4":
            # VP9 has no NVENC path, so WebM stays on the software encoder.
            return cpu
        resolved = self.resolve_hardware_encoder()
        if resolved is None:
            return cpu
        binary, encoder = resolved
        default_binary = self.profile().ffmpeg or ""
        return CodecChoice(
            encoder=encoder,
            hardware=True,
            args=tuple(_hardware_codec_args(encoder)),
            binary="" if binary == default_binary else binary,
        )

    def model_device(self, preferred: str = "auto") -> tuple[str, str]:
        """``(device, reason)`` for a torch/ctranslate2 model.

        ``device`` is ``"cuda"`` only when the policy allows it *and* the
        installed torch build reports CUDA, so nothing is ever told to use a GPU
        that is not there — the single most common source of "it worked on my
        machine" failures.
        """
        mode = (preferred or "auto").strip().lower()
        if mode == "cpu":
            return "cpu", "requested_cpu"
        if not self.gpu_allowed:
            return "cpu", "policy"
        if mode == "cuda":
            return (
                ("cuda", "requested_cuda")
                if self._cuda_ready()
                else (
                    "cpu",
                    "no_cuda",
                )
            )
        return ("cuda", "auto") if self._cuda_ready() else ("cpu", "no_cuda")

    def _cuda_ready(self) -> bool:
        """True when a CUDA build of torch is installed and can see a device."""
        return bool(self.profile().torch_cuda)

    def whisper_compute(self, preferred: str = "auto") -> tuple[str, str, str]:
        """``(device, compute_type, reason)`` for faster-whisper / CTranslate2."""
        device, reason = self.model_device(preferred)
        return device, ("float16" if device == "cuda" else "int8"), reason

    def software_video_codec(self, export_format: str) -> CodecChoice:
        """The CPU encoder for a format: the safety net when hardware fails."""
        return _cpu_codec(export_format)

    def note_encoder_fallback(self, failed: str) -> None:
        """Record that a hardware encoder failed and the job fell back."""
        with self._lock:
            self._stats.encoder_fallbacks += 1
            self._stats.last_encoder = f"{failed}->cpu"

    def note_encoder(self, encoder: str) -> None:
        with self._lock:
            self._stats.last_encoder = encoder

    def explain(self, kind: JobKind, *, refresh: bool = False) -> dict[str, Any]:
        """What would happen to this job right now — without starting it.

        An agent can ask before committing to a long job, and an operator can see
        whether a GPU is actually free instead of guessing from a slow render.

        ``refresh`` decides whether the answer re-probes the machine. A status
        question answers from the cached profile (``profile_ttl_seconds``); the
        *admission path* (:meth:`begin`) always re-probes, because it is the one
        that must not act on a stale temperature.
        """
        need = _VRAM_MB.get(kind, 0)
        blocker = self._gpu_blocker(need, refresh=refresh)
        return {
            "kind": str(kind),
            "admission": str(Admission.CPU if blocker else Admission.GPU),
            "blocked_by": blocker or "ready",
            "vram_needed_mb": need,
            "would_wait_seconds": 0.0
            if blocker in {"", "policy", "no_gpu"}
            else float(self._settings.gpu_wait_seconds),
        }

    # --- admission -----------------------------------------------------------

    def recommended_threads(self) -> int:
        """Threads for ffmpeg: the configured cap, trimmed under memory pressure."""
        configured = int(self._settings.render_threads)
        profile = self.profile()
        floor = int(self._settings.ram_min_available_mb)
        if floor and profile.ram_available_mb and profile.ram_available_mb < floor:
            return 1
        return max(1, min(configured, max(1, profile.cpu_count // 2)))

    def pressure_violation(self) -> str:
        """Emergency state that must stop a *running* job, or ``""`` when sane.

        Admission control decides whether a job may start; this decides whether
        one already running has to be killed. They are different questions: a
        render that began on a healthy machine can still walk the system into
        swap or push the GPU past its thermal limit an hour later. The thresholds
        here are deliberately outside the admission thresholds and much more
        serious, so ordinary load never aborts work — only a machine in real
        trouble does.
        """
        available_mb, temperature_c = self._pressure()
        floor = int(self._settings.ram_abort_mb)
        if floor and available_mb and available_mb < floor:
            return (
                f"free RAM fell to {available_mb}MB, below the {floor}MB floor "
                "(the machine is about to swap)"
            )
        ceiling = int(self._settings.gpu_abort_temperature_c)
        if temperature_c is not None and temperature_c >= ceiling:
            return (
                f"the GPU reached {temperature_c}C, at or above the "
                f"{ceiling}C abort threshold"
            )
        return ""

    def _gpu_blocker(self, vram_mb: int, *, refresh: bool = True) -> str:
        """Why the GPU is not usable right now, or an empty string when it is."""
        if not self.gpu_allowed:
            return "policy"
        profile = self.profile(refresh=refresh)
        gpu = profile.gpu
        if gpu is None:
            return "no_gpu"
        if self._gpu_active >= self._settings.gpu_max_jobs:
            return "gpu_busy"
        needed = vram_mb + self._settings.gpu_memory_headroom_mb
        if gpu.vram_free_mb < needed:
            return "vram"
        if gpu.utilization_pct >= self._settings.gpu_max_utilization_pct:
            return "utilization"
        limit = self._settings.gpu_max_temperature_c
        if gpu.temperature_c is not None and gpu.temperature_c >= limit:
            return "temperature"
        return ""

    def begin(self, kind: JobKind, *, vram_mb: int | None = None) -> Decision:
        """Acquire the slots this job needs. Blocks (bounded) while the machine is busy.

        ``JobKind.RENDER`` is admitted through the same machinery so two exports
        cannot run at once on a laptop; the device part only decides whether the
        *encoder* is hardware or software.
        """
        started = self._clock()
        need = _VRAM_MB.get(kind, 0) if vram_mb is None else vram_mb
        heavy = kind in _HEAVY
        if heavy:
            self._wait_for_heavy_slot()
        blocker = self._gpu_blocker(need)
        admission = Admission.CPU if blocker else Admission.GPU
        if blocker and blocker not in {"policy", "no_gpu"}:
            admission = self._wait_for_gpu(blocker, need)
        if admission is Admission.CPU and blocker not in {"policy", "no_gpu"}:
            blocker = f"{blocker}_timeout"
        waited = self._clock() - started
        if admission is Admission.GPU:
            with self._lock:
                self._gpu_active += 1
        decision = Decision(
            kind=kind,
            admission=admission,
            encoder=None,
            waited_seconds=waited,
            serialized=heavy,
            reason=blocker or "ready",
            vram_mb=need,
        )
        with self._lock:
            self._stats.jobs_started += 1
            if admission is Admission.GPU:
                self._stats.gpu_jobs += 1
            else:
                self._stats.cpu_jobs += 1
                if decision.degraded:
                    self._stats.degraded_jobs += 1
            if heavy:
                self._stats.serialized_jobs += 1
            self._stats.total_wait_seconds += waited
            self._stats.longest_wait_seconds = max(
                self._stats.longest_wait_seconds, waited
            )
            self._last_decision = decision
        return decision

    def _wait_for_heavy_slot(self) -> None:
        """At most ``max_heavy_jobs`` heavy jobs run at once on this machine."""
        deadline = self._clock() + self._settings.heavy_wait_seconds
        with self._slot_free:
            while self._heavy_active >= self._settings.max_heavy_jobs:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    # Queued work still has to run: proceed and record the wait.
                    break
                self._slot_free.wait(timeout=min(remaining, 5.0))
            self._heavy_active += 1

    def _wait_for_gpu(self, blocker: str, vram_mb: int) -> Admission:
        """Wait for headroom, then give up honestly and use the CPU."""
        deadline = self._clock() + self._settings.gpu_wait_seconds
        delay = self._settings.gpu_poll_seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                return Admission.CPU
            self._sleep(min(delay, remaining))
            delay = min(delay * 2, 10.0)
            if not self._gpu_blocker(vram_mb):
                return Admission.GPU

    def end(self, decision: Decision) -> None:
        """Release whatever :meth:`begin` acquired."""
        with self._slot_free:
            if decision.kind in _HEAVY:
                self._heavy_active = max(0, self._heavy_active - 1)
            if decision.admission is Admission.GPU:
                self._gpu_active = max(0, self._gpu_active - 1)
            self._slot_free.notify_all()

    @contextmanager
    def job(self, kind: JobKind, *, vram_mb: int | None = None) -> Iterator[Decision]:
        """Use as ``with governor.job(JobKind.OCR) as decision:``."""
        decision = self.begin(kind, vram_mb=vram_mb)
        try:
            yield decision
        finally:
            self.end(decision)

    # --- reporting -----------------------------------------------------------

    def _advice(
        self,
        last_encoder: str,
        profile: HardwareProfile,
        encoder_status: dict[str, Any],
        resolved: tuple[str, str] | None,
    ) -> list[str]:
        """Advice that knows the *probed and resolved* state, not just the build."""
        notes = _advice(
            profile,
            self._settings,
            encoder_status,
            last_encoder,
            resolved=resolved,
        )
        primary = profile.ffmpeg
        if resolved is not None:
            binary, encoder = resolved
            if primary and binary != primary:
                found = profile.build(binary)
                label = (
                    f"ffmpeg {found.short_version}"
                    if found and found.version
                    else binary
                )
                notes.append(
                    f"{encoder} does not start on the machine's own ffmpeg, but it "
                    f"does on a second build ({label}): exports use that build for "
                    "the encode, and nothing else is redirected. That build matched "
                    "this driver's NVENC API where the primary one expects a newer "
                    "one — so the GPU is in use despite the driver being older than "
                    "the system ffmpeg wants."
                )
        if resolved is not None or self._settings.render_encoder != "auto":
            return notes
        # A working integrated-GPU encoder is a real option, just not the
        # automatic one: it is faster but spends bits much faster too.
        for name, label in (("h264_amf", "AMD AMF"), ("h264_qsv", "Intel Quick Sync")):
            if name not in profile.encoders or not self.gpu_allowed:
                continue
            usable, _note = self.check_encoder(name)
            if usable:
                notes.append(
                    f"{label} ({name}) works on this machine and encodes roughly "
                    "twice as fast as libx264, at the cost of noticeably larger "
                    "files at the same quality setting. It is never chosen "
                    "automatically: set CONTENT_FACTORY_RENDER_ENCODER=amf (or "
                    "'qsv') to opt in."
                )
                break
        return notes

    def snapshot(self, *, refresh: bool = False) -> dict[str, Any]:
        """Everything an operator or an agent needs to explain current behaviour.

        The hardware profile is served from cache (``profile_ttl_seconds``)
        unless ``refresh`` is asked for. Re-probing on *every* call made a
        status query cost 1.5–2 s of subprocess work for data that is
        effectively static — an agent that asks the machine whether it is free
        before every job paid that per job. Counters, admission and the last
        decision are always live; only the measured profile is cached.
        """
        profile = self.profile(refresh=refresh)
        with self._lock:
            stats = self._stats.to_dict()
            gpu_active = self._gpu_active
            heavy_active = self._heavy_active
            last = self._last_decision.to_dict() if self._last_decision else None
        encoder_status = self.encoder_status()
        resolved = self.resolve_hardware_encoder()
        return {
            "compute_policy": self._settings.compute_policy,
            "render_encoder": self._settings.render_encoder,
            "hardware_encoder": None
            if resolved is None
            else {"encoder": resolved[1], "binary": resolved[0]},
            "recommended_threads": self.recommended_threads(),
            "limits": {
                "gpu_max_jobs": self._settings.gpu_max_jobs,
                "max_heavy_jobs": self._settings.max_heavy_jobs,
                "gpu_max_temperature_c": self._settings.gpu_max_temperature_c,
                "gpu_max_utilization_pct": self._settings.gpu_max_utilization_pct,
                "gpu_memory_headroom_mb": self._settings.gpu_memory_headroom_mb,
                "gpu_wait_seconds": self._settings.gpu_wait_seconds,
                "ram_min_available_mb": self._settings.ram_min_available_mb,
            },
            "abort_limits": {
                "ram_abort_mb": self._settings.ram_abort_mb,
                "gpu_abort_temperature_c": self._settings.gpu_abort_temperature_c,
                "render_monitor_seconds": self._settings.render_monitor_seconds,
            },
            "active": {"gpu_jobs": gpu_active, "heavy_jobs": heavy_active},
            "hardware": profile.to_dict(),
            "stats": stats,
            "last_decision": last,
            # One profile read covers the whole report: it was just refreshed
            # (or read from cache) above, so the per-kind answers reuse it
            # instead of re-probing the machine once per job kind.
            "admission_now": {str(kind): self.explain(kind) for kind in JobKind},
            "advice": self._advice(
                stats["last_encoder"], profile, encoder_status, resolved
            ),
        }


#: One governor per process, for code paths that run without a service.
_DEFAULT: ResourceGovernor | None = None
_DEFAULT_LOCK = threading.Lock()


def default_governor() -> ResourceGovernor:
    """Process-wide governor, built from the cached settings on first use."""
    global _DEFAULT
    if _DEFAULT is None:
        with _DEFAULT_LOCK:
            if _DEFAULT is None:
                _DEFAULT = ResourceGovernor(get_settings())
    return _DEFAULT


def _cpu_codec(export_format: str) -> CodecChoice:
    if export_format == "mp4":
        return CodecChoice(
            encoder="libx264",
            hardware=False,
            args=(
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-movflags",
                "+faststart",
            ),
        )
    return CodecChoice(
        encoder="libvpx-vp9",
        hardware=False,
        args=(
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "8",
            "-b:v",
            "1M",
        ),
    )


def _hardware_codec_args(encoder: str) -> list[str]:
    """Encoder args for a GPU H.264 encoder (quality ~x264 crf 23)."""
    if encoder == "h264_nvenc":
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            "23",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ]
    if encoder == "h264_qsv":
        return [
            "-c:v",
            "h264_qsv",
            "-global_quality",
            "23",
            "-pix_fmt",
            "nv12",
            "-movflags",
            "+faststart",
        ]
    return [
        "-c:v",
        encoder,
        "-quality",
        "balanced",
        "-qp_i",
        "23",
        "-qp_p",
        "23",
        "-movflags",
        "+faststart",
    ]


def _advice(
    profile: HardwareProfile,
    settings: Settings,
    encoder_status: dict[str, Any] | None = None,
    last_encoder: str = "",
    *,
    resolved: tuple[str, str] | None = None,
) -> list[str]:
    """Plain-language notes: what is fast, what is slow, what is missing."""
    notes: list[str] = []
    status = encoder_status or {"encoder": None, "usable": False, "note": ""}
    # ``resolved`` is the truth about where encoding will land. When a hardware
    # encoder was found on some build, the primary build's refusal is history,
    # not a reason to tell the operator their exports fell back to software.
    if status.get("encoder") and not status.get("usable") and resolved is None:
        notes.append(
            f"{status['encoder']} is listed by ffmpeg but cannot start on this "
            f"machine ({status.get('note')}), so MP4 exports use libx264. Either "
            "fix works: a GPU driver newer than the NVENC API the ffmpeg build "
            "was compiled against, or a second ffmpeg build compiled against the "
            "older API. The governor already probes every build it can find; "
            "CONTENT_FACTORY_FFMPEG_EXTRA_BINARIES points it at one more."
        )
    if last_encoder.endswith("->cpu"):
        notes.append(
            f"The last export fell back mid-job: {last_encoder}. The render "
            "still completed, in software."
        )
    gpu = profile.gpu
    if gpu is None:
        notes.append(
            "No NVIDIA GPU detected (nvidia-smi absent or failing): everything "
            "runs on the CPU."
        )
    else:
        notes.append(
            f"{gpu.name} with {gpu.vram_total_mb} MB VRAM detected "
            f"({gpu.vram_free_mb} MB free, {gpu.temperature_c}°C)."
        )
        if settings.compute_policy == "cpu":
            notes.append("compute_policy is 'cpu', so the GPU is deliberately unused.")
    encoder = status.get("encoder") if resolved is None else resolved[1]
    usable = bool(status.get("usable")) or resolved is not None
    hardware_enabled = (
        usable and settings.render_encoder != "cpu" and settings.compute_policy != "cpu"
    )
    if encoder and usable and not hardware_enabled:
        notes.append(
            f"{encoder} is available but disabled by configuration, so MP4 "
            "exports use libx264."
        )
    elif encoder and usable:
        notes.append(
            f"MP4 exports encode with {encoder}: the CPU stays free for the "
            "filter graph, and a hardware failure falls back to libx264."
        )
    if settings.render_hwaccel not in {"auto", "off", "none", "cpu", ""}:
        notes.append(
            f"Hardware decode is forced on ({settings.render_hwaccel}). That only "
            "pays when the decoded frames stay on the GPU; with a CPU filter graph "
            "it adds a PCIe round trip per frame and measures slower, so the render "
            "retries in software if it fails."
        )
    if not profile.torch_cuda:
        notes.append(
            "torch is CPU-only"
            + (f" ({profile.torch_version})" if profile.torch_version else "")
            + ", so torch-based models (OCR, background removal, upscaling) "
            "cannot use the GPU. Installing the CUDA build is what unlocks them; "
            "see docs/COMPUTE-RESOURCES.md."
        )
    if profile.torch_cuda and profile.onnx_providers:
        accelerated = [p for p in profile.onnx_providers if "GPU" in p or "CUDA" in p]
        if accelerated:
            notes.append(f"ONNX Runtime GPU provider available: {accelerated[0]}.")
    if settings.ram_min_available_mb and profile.ram_available_mb:
        if profile.ram_available_mb < settings.ram_min_available_mb:
            notes.append(
                f"Only {profile.ram_available_mb} MB RAM free; heavy jobs are "
                "trimmed to one thread and run one at a time."
            )
    return notes
