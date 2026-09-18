"""Hardware probe and resource governor.

This project runs on a laptop with one 8 GB GPU that is also driving the desktop,
so the interesting question is never "can this use the GPU?" but "should this use
the GPU **right now**?".

The module answers two questions:

* :func:`probe` — what does this machine actually have? CPU count, RAM, GPU
  name/VRAM/temperature, which hardware encoders ffmpeg exposes, whether torch
  has CUDA. Standard library only (``nvidia-smi`` + ``ctypes``), so nothing new
  has to be installed and it degrades to "no GPU" on a machine without one.
* :class:`ResourceGovernor` — may this job take the GPU, or should it wait, or
  should it honestly fall back to CPU?

The degradation ladder, in order:

1. **No GPU, or policy says CPU** → run on CPU.
2. **Another heavy job is running** → wait for the slot (jobs are serialized, so
   the machine stays responsive; the wait is reported).
3. **GPU too hot, saturated, or short of free VRAM** → poll with a backoff until
   it cools or frees, up to ``gpu_wait_seconds``.
4. **Still busy after that** → run on CPU and record *why*, instead of blocking
   forever or failing the job.

Nothing here is a guess about correctness: the profile is measured, every
decision carries its reason, and the counters are exposed through
``GET /resources`` so the behaviour can be inspected rather than believed.
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import Settings, get_settings

__all__ = [
    "default_governor",
    "Admission",
    "CodecChoice",
    "Decision",
    "GpuInfo",
    "HardwareProfile",
    "JobKind",
    "ResourceGovernor",
    "probe",
]

#: Encoder names ffmpeg may expose that put the work on the GPU.
_HARDWARE_ENCODERS = ("h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "h264_amf")


class JobKind(StrEnum):
    """The heavy job families this project schedules."""

    TRANSCRIBE = "transcribe"
    OCR = "ocr"
    VISION = "vision"
    RENDER = "render"


#: Rough VRAM each kind needs *in addition to* whatever is already resident.
#: Deliberately generous: the point is to refuse a job that would swap the GPU,
#: not to be exact. Overridable per call.
_VRAM_MB: dict[JobKind, int] = {
    JobKind.TRANSCRIBE: 1200,
    JobKind.OCR: 1600,
    JobKind.VISION: 2500,
    JobKind.RENDER: 700,
}

#: Kinds that must never overlap with each other on a laptop.
_HEAVY: frozenset[JobKind] = frozenset(
    {JobKind.TRANSCRIBE, JobKind.OCR, JobKind.VISION, JobKind.RENDER}
)

#: GPU blockers that mean "there is no GPU to use", not "the GPU was busy".
_NON_GPU: frozenset[str] = frozenset({"policy", "no_gpu"})


class Admission(StrEnum):
    """Where a job was told to run."""

    GPU = "gpu"
    CPU = "cpu"


@dataclass(frozen=True)
class GpuInfo:
    """One GPU as reported by ``nvidia-smi``."""

    index: int
    name: str
    driver: str
    vram_total_mb: int
    vram_used_mb: int
    utilization_pct: int
    temperature_c: int | None

    @property
    def vram_free_mb(self) -> int:
        return max(0, self.vram_total_mb - self.vram_used_mb)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "driver": self.driver,
            "vram_total_mb": self.vram_total_mb,
            "vram_used_mb": self.vram_used_mb,
            "vram_free_mb": self.vram_free_mb,
            "utilization_pct": self.utilization_pct,
            "temperature_c": self.temperature_c,
        }


@dataclass(frozen=True)
class HardwareProfile:
    """What this machine can do, measured once (pressure parts re-read live)."""

    cpu_count: int
    ram_total_mb: int
    ram_available_mb: int
    gpus: tuple[GpuInfo, ...]
    encoders: tuple[str, ...]
    ffmpeg: str | None
    torch_cuda: bool
    torch_version: str
    onnx_providers: tuple[str, ...]
    probed_at: float

    @property
    def gpu(self) -> GpuInfo | None:
        return self.gpus[0] if self.gpus else None

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpus)

    def has_encoder(self, name: str) -> bool:
        return name in self.encoders

    def hardware_video_encoder(self) -> str | None:
        """Best hardware H.264 encoder this ffmpeg build exposes, if any."""
        for name in ("h264_nvenc", "h264_qsv", "h264_amf"):
            if name in self.encoders:
                return name
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_count": self.cpu_count,
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_available_mb,
            "gpus": [gpu.to_dict() for gpu in self.gpus],
            "encoders": [name for name in self.encoders if name in _HARDWARE_ENCODERS],
            "ffmpeg": self.ffmpeg,
            "torch_cuda": self.torch_cuda,
            "torch_version": self.torch_version,
            "onnx_providers": list(self.onnx_providers),
            "probed_at": round(self.probed_at, 3),
        }


@dataclass(frozen=True)
class CodecChoice:
    """The video encoder an export will use."""

    encoder: str
    hardware: bool
    args: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder": self.encoder,
            "hardware": self.hardware,
            "args": list(self.args),
        }


@dataclass(frozen=True)
class Decision:
    """Where one job was allowed to run, and why."""

    kind: JobKind
    admission: Admission
    encoder: str | None
    waited_seconds: float
    serialized: bool
    reason: str
    vram_mb: int

    @property
    def degraded(self) -> bool:
        """True when the CPU was used *instead* of a GPU that could not be had.

        A machine without a GPU, or a policy that forbids one, is not degraded —
        that is simply the configuration. A busy, hot or VRAM-starved GPU is.
        """
        return self.admission is Admission.CPU and self.reason not in _NON_GPU

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": str(self.kind),
            "admission": str(self.admission),
            "encoder": self.encoder,
            "waited_seconds": round(self.waited_seconds, 2),
            "serialized": self.serialized,
            "degraded": self.degraded,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------


def _system_memory_mb() -> tuple[int, int]:
    """``(total_mb, available_mb)`` using only the standard library."""
    if platform.system() == "Windows":

        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys // 1048576), int(
                    status.ullAvailPhys // 1048576
                )
        except (AttributeError, OSError):  # pragma: no cover - non-Windows
            return 0, 0
        return 0, 0
    try:  # pragma: no cover - POSIX
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        return 0, 0
    values: dict[str, int] = {}
    for line in meminfo.splitlines():
        key, _, rest = line.partition(":")
        number = rest.strip().split(" ")[0]
        if number.isdigit():
            values[key] = int(number)
    return values.get("MemTotal", 0) // 1024, values.get("MemAvailable", 0) // 1024


def _nvidia_smi_gpus(binary: str) -> tuple[GpuInfo, ...]:
    """Read GPU state; an absent or failing ``nvidia-smi`` is simply no GPU."""
    query = (
        "index,name,driver_version,memory.total,memory.used,utilization.gpu,"
        "temperature.gpu"
    )
    try:
        completed = subprocess.run(
            [binary, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    gpus: list[GpuInfo] = []
    for line in completed.stdout.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            gpus.append(
                GpuInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    driver=parts[2],
                    vram_total_mb=int(float(parts[3])),
                    vram_used_mb=int(float(parts[4])),
                    utilization_pct=int(float(parts[5])),
                    temperature_c=int(float(parts[6])),
                )
            )
        except ValueError:
            continue
    return tuple(gpus)


def _ffmpeg_encoders(binary: str) -> tuple[str, ...]:
    """Names of the video encoders this ffmpeg build supports."""
    try:
        completed = subprocess.run(
            [binary, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    names: list[str] = []
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].startswith("V"):
            names.append(fields[1])
    return tuple(names)


def probe_encoder(ffmpeg: str, encoder: str) -> tuple[bool, str]:
    """Prove a hardware encoder really works by encoding one frame.

    Listing encoders is not enough: an ffmpeg build can carry ``h264_nvenc`` and
    still refuse to start it (an NVENC API newer than the installed driver, a
    headless session, a busy encoder slot). This runs the smallest possible real
    encode and returns ``(usable, note)``, so the export path never plans for an
    encoder the machine cannot actually open.
    """
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:size=64x64:duration=0.1:rate=10",
        "-frames:v",
        "1",
        "-c:v",
        encoder,
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"probe could not run: {exc}"
    if completed.returncode == 0:
        return True, ""
    lines = [line.strip() for line in completed.stderr.splitlines() if line.strip()]
    return False, " ".join(lines[-2:])[:300] or "the encoder refused the job"


def _torch_state() -> tuple[bool, str]:
    """``(cuda_available, version)`` without importing torch unless installed."""
    try:
        import torch  # noqa: PLC0415 - optional, heavy import on purpose

        return bool(torch.cuda.is_available()), str(torch.__version__)
    except Exception:  # noqa: BLE001 - any failure means "no torch"
        return False, ""


def _onnx_providers() -> tuple[str, ...]:
    try:
        import onnxruntime  # type: ignore[import-untyped]  # noqa: PLC0415

        return tuple(onnxruntime.get_available_providers())
    except Exception:  # noqa: BLE001 - optional dependency
        return ()


def probe(
    *,
    which: Callable[[str], str | None] = shutil.which,
    nvidia_smi: Callable[[str], tuple[GpuInfo, ...]] = _nvidia_smi_gpus,
    encoders: Callable[[str], tuple[str, ...]] = _ffmpeg_encoders,
    memory: Callable[[], tuple[int, int]] = _system_memory_mb,
    torch_state: Callable[[], tuple[bool, str]] = _torch_state,
    onnx: Callable[[], tuple[str, ...]] = _onnx_providers,
    cpu_count: Callable[[], int | None] = os.cpu_count,
) -> HardwareProfile:
    """Measure this machine. Every probe is injectable so tests need no GPU."""
    smi = which("nvidia-smi")
    ffmpeg = which("ffmpeg")
    total_mb, available_mb = memory()
    cuda, torch_version = torch_state()
    return HardwareProfile(
        cpu_count=int(cpu_count() or 1),
        ram_total_mb=total_mb,
        ram_available_mb=available_mb,
        gpus=nvidia_smi(smi) if smi else (),
        encoders=encoders(ffmpeg) if ffmpeg else (),
        ffmpeg=ffmpeg,
        torch_cuda=cuda,
        torch_version=torch_version,
        onnx_providers=onnx(),
        probed_at=time.time(),
    )


# ---------------------------------------------------------------------------
# The governor
# ---------------------------------------------------------------------------


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
        probe_fn: Callable[[], HardwareProfile] = probe,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        encoder_probe: Callable[[str, str], tuple[bool, str]] = probe_encoder,
    ) -> None:
        self._settings = settings
        self._probe = probe_fn
        self._clock = clock
        self._sleep = sleep
        self._encoder_probe = encoder_probe
        #: encoder name -> (usable, note), checked once with a real encode.
        self._encoder_checks: dict[str, tuple[bool, str]] = {}
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

    def encoder_status(self) -> dict[str, Any]:
        """Whether a hardware encoder exists *and* can really start on this machine."""
        profile = self.profile()
        encoder = profile.hardware_video_encoder()
        if encoder is None:
            return {
                "encoder": None,
                "usable": False,
                "note": "this ffmpeg build exposes no hardware H.264 encoder",
            }
        with self._lock:
            cached = self._encoder_checks.get(encoder)
        if cached is None:
            cached = self._encoder_probe(profile.ffmpeg or "ffmpeg", encoder)
            with self._lock:
                self._encoder_checks[encoder] = cached
        usable, note = cached
        return {"encoder": encoder, "usable": usable, "note": note}

    def video_codec(self, export_format: str) -> CodecChoice:
        """Pick the encoder for an export: hardware when available and allowed."""
        cpu = _cpu_codec(export_format)
        if export_format != "mp4":
            # VP9 has no NVENC path, so WebM stays on the software encoder.
            return cpu
        if self._settings.render_encoder == "cpu" or not self.gpu_allowed:
            return cpu
        status = self.encoder_status()
        encoder = status["encoder"]
        if encoder is None or not status["usable"]:
            return cpu
        return CodecChoice(
            encoder=encoder,
            hardware=True,
            args=tuple(_hardware_codec_args(encoder)),
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

    def explain(self, kind: JobKind) -> dict[str, Any]:
        """What would happen to this job right now — without starting it.

        An agent can ask before committing to a long job, and an operator can see
        whether a GPU is actually free instead of guessing from a slow render.
        """
        need = _VRAM_MB.get(kind, 0)
        blocker = self._gpu_blocker(need)
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

    def _gpu_blocker(self, vram_mb: int) -> str:
        """Why the GPU is not usable right now, or an empty string when it is."""
        if not self.gpu_allowed:
            return "policy"
        profile = self.profile(refresh=True)
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

    def snapshot(self) -> dict[str, Any]:
        """Everything an operator or an agent needs to explain current behaviour."""
        profile = self.profile(refresh=True)
        with self._lock:
            stats = self._stats.to_dict()
            gpu_active = self._gpu_active
            heavy_active = self._heavy_active
            last = self._last_decision.to_dict() if self._last_decision else None
        return {
            "compute_policy": self._settings.compute_policy,
            "render_encoder": self._settings.render_encoder,
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
            "active": {"gpu_jobs": gpu_active, "heavy_jobs": heavy_active},
            "hardware": profile.to_dict(),
            "stats": stats,
            "last_decision": last,
            "admission_now": {str(kind): self.explain(kind) for kind in JobKind},
            "advice": _advice(profile, self._settings),
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


def _advice(profile: HardwareProfile, settings: Settings) -> list[str]:
    """Plain-language notes: what is fast, what is slow, what is missing."""
    notes: list[str] = []
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
    encoder = profile.hardware_video_encoder()
    hardware_enabled = (
        encoder is not None
        and settings.render_encoder != "cpu"
        and settings.compute_policy != "cpu"
    )
    if encoder and hardware_enabled:
        notes.append(
            f"MP4 exports encode with {encoder}: the CPU stays free for the "
            "filter graph, and a hardware failure falls back to libx264."
        )
    elif encoder:
        notes.append(
            f"{encoder} is available but disabled by configuration, so MP4 "
            "exports use libx264."
        )
    elif profile.ffmpeg:
        notes.append(
            "This ffmpeg build exposes no hardware H.264 encoder, so exports "
            "use libx264."
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
