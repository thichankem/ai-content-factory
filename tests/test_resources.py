"""Tests for the hardware probe and the resource governor.

No GPU is required: every probe is injected, so a "hot 8 GB laptop GPU" is a
dataclass literal and a "machine with nothing" is an empty tuple.
"""

from __future__ import annotations

import subprocess
import threading
import time

import pytest

from content_factory.config import Settings
from content_factory.resources import (
    Admission,
    GpuInfo,
    HardwareProfile,
    JobKind,
    ResourceGovernor,
    default_governor,
    probe,
)


def _profile(
    *,
    gpu: GpuInfo | None = None,
    encoders: tuple[str, ...] = ("libx264", "libvpx-vp9"),
    torch_cuda: bool = False,
    ram_available_mb: int = 8000,
    cpu_count: int = 16,
) -> HardwareProfile:
    return HardwareProfile(
        cpu_count=cpu_count,
        ram_total_mb=16000,
        ram_available_mb=ram_available_mb,
        gpus=(gpu,) if gpu else (),
        encoders=encoders,
        ffmpeg="/usr/bin/ffmpeg",
        torch_cuda=torch_cuda,
        torch_version="2.14.0" if torch_cuda else "2.14.0+cpu",
        onnx_providers=("CPUExecutionProvider",),
        probed_at=time.time(),
    )


def _gpu(
    *,
    used: int = 100,
    total: int = 8188,
    utilization: int = 3,
    temperature: int = 45,
) -> GpuInfo:
    return GpuInfo(
        index=0,
        name="NVIDIA GeForce RTX 4060 Laptop GPU",
        driver="566.24",
        vram_total_mb=total,
        vram_used_mb=used,
        utilization_pct=utilization,
        temperature_c=temperature,
    )


def _governor(profile: HardwareProfile, **overrides) -> ResourceGovernor:
    settings = Settings(**overrides)
    return ResourceGovernor(settings, probe_fn=lambda: profile, sleep=lambda _s: None)


# --- probe -------------------------------------------------------------------


def test_probe_reads_every_injected_source() -> None:
    profile = probe(
        which=lambda name: f"/usr/bin/{name}",
        nvidia_smi=lambda _binary: (_gpu(),),
        encoders=lambda _binary: ("h264_nvenc", "libx264"),
        memory=lambda: (16000, 9000),
        torch_state=lambda: (True, "2.14.0+cu126"),
        onnx=lambda: ("CUDAExecutionProvider",),
        cpu_count=lambda: 16,
    )
    assert profile.has_gpu
    assert profile.gpu is not None and profile.gpu.name.endswith("RTX 4060 Laptop GPU")
    assert profile.gpu.vram_free_mb == 8088
    assert profile.hardware_video_encoder() == "h264_nvenc"
    assert profile.torch_cuda
    assert profile.ram_available_mb == 9000
    assert profile.cpu_count == 16


def test_probe_without_a_gpu_or_ffmpeg_is_not_an_error() -> None:
    profile = probe(
        which=lambda _name: None,
        nvidia_smi=lambda _binary: (_gpu(),),
        encoders=lambda _binary: ("h264_nvenc",),
        memory=lambda: (0, 0),
        torch_state=lambda: (False, ""),
        onnx=lambda: (),
        cpu_count=lambda: None,
    )
    assert not profile.has_gpu  # nvidia-smi was not on PATH
    assert profile.encoders == ()
    assert profile.ffmpeg is None
    assert profile.hardware_video_encoder() is None
    assert profile.to_dict()["gpus"] == []


def test_probe_reports_only_hardware_encoders_in_the_summary() -> None:
    profile = _profile(gpu=_gpu(), encoders=("libx264", "libvpx-vp9", "hevc_nvenc"))
    assert profile.to_dict()["encoders"] == ["hevc_nvenc"]


# --- encoder policy ---------------------------------------------------------


def test_mp4_prefers_nvenc_when_the_gpu_is_present() -> None:
    governor = _governor(_profile(gpu=_gpu(), encoders=("libx264", "h264_nvenc")))
    choice = governor.video_codec("mp4")
    assert choice.encoder == "h264_nvenc"
    assert choice.hardware
    assert "-c:v" in choice.args and "h264_nvenc" in choice.args


def test_webm_stays_on_the_software_encoder() -> None:
    governor = _governor(_profile(gpu=_gpu(), encoders=("libx264", "h264_nvenc")))
    assert governor.video_codec("webm").encoder == "libvpx-vp9"


def test_render_encoder_cpu_forces_software_evan_on_a_gpu_machine() -> None:
    governor = _governor(
        _profile(gpu=_gpu(), encoders=("libx264", "h264_nvenc")), render_encoder="cpu"
    )
    choice = governor.video_codec("mp4")
    assert choice.encoder == "libx264" and not choice.hardware


def test_compute_policy_cpu_disables_the_gpu_everywhere() -> None:
    governor = _governor(
        _profile(gpu=_gpu(), encoders=("h264_nvenc",), torch_cuda=True),
        compute_policy="cpu",
    )
    assert governor.video_codec("mp4").encoder == "libx264"
    assert governor.model_device()[0] == "cpu"
    assert not governor.gpu_allowed


# --- device policy ----------------------------------------------------------


def test_model_device_requires_a_cuda_build_of_torch() -> None:
    without = _governor(_profile(gpu=_gpu(), torch_cuda=False))
    assert without.model_device() == ("cpu", "no_cuda")
    with_cuda = _governor(_profile(gpu=_gpu(), torch_cuda=True))
    assert with_cuda.model_device() == ("cuda", "auto")
    assert with_cuda.model_device("cpu") == ("cpu", "requested_cpu")


def test_whisper_compute_type_follows_the_device() -> None:
    governor = _governor(_profile(gpu=_gpu(), torch_cuda=True))
    assert governor.whisper_compute() == ("cuda", "float16", "auto")
    cpu = _governor(_profile(gpu=None))
    assert cpu.whisper_compute() == ("cpu", "int8", "no_cuda")


def test_asking_for_cuda_without_cuda_is_reported_not_assumed() -> None:
    governor = _governor(_profile(gpu=None))
    assert governor.model_device("cuda") == ("cpu", "no_cuda")


# --- admission --------------------------------------------------------------


def test_gpu_job_is_admitted_when_the_card_is_free() -> None:
    governor = _governor(_profile(gpu=_gpu(), torch_cuda=True))
    with governor.job(JobKind.OCR) as decision:
        assert decision.admission is Admission.GPU
        assert decision.reason == "ready"
        assert not decision.degraded


def test_hot_gpu_degrades_to_cpu_after_waiting() -> None:
    governor = _governor(
        _profile(gpu=_gpu(temperature=95), torch_cuda=True), gpu_wait_seconds=0.01
    )
    with governor.job(JobKind.OCR) as decision:
        assert decision.admission is Admission.CPU
        assert decision.reason == "temperature_timeout"
        assert decision.degraded


def test_busy_gpu_waits_then_degrades_instead_of_blocking_forever() -> None:
    governor = _governor(
        _profile(gpu=_gpu(utilization=99), torch_cuda=True), gpu_wait_seconds=0.01
    )
    decision = governor.begin(JobKind.VISION)
    try:
        assert decision.admission is Admission.CPU
        assert decision.reason == "utilization_timeout"
    finally:
        governor.end(decision)


def test_vram_guard_refuses_a_job_that_would_swap() -> None:
    governor = _governor(
        _profile(gpu=_gpu(used=7900), torch_cuda=True), gpu_wait_seconds=0.01
    )
    decision = governor.begin(JobKind.VISION, vram_mb=2500)
    try:
        assert decision.admission is Admission.CPU
        assert decision.reason == "vram_timeout"
    finally:
        governor.end(decision)


def test_no_gpu_is_a_normal_answer_not_a_failure() -> None:
    governor = _governor(_profile(gpu=None))
    with governor.job(JobKind.TRANSCRIBE) as decision:
        assert decision.admission is Admission.CPU
        assert decision.reason == "no_gpu"
        # "no GPU" is the machine's nature, not a degraded decision.
        assert not decision.degraded


def test_heavy_jobs_are_serialized() -> None:
    """Two concurrent exports must not run at the same time on one laptop."""
    governor = _governor(_profile(gpu=None))
    order: list[str] = []
    started = threading.Event()

    def first() -> None:
        with governor.job(JobKind.RENDER):
            order.append("first-in")
            started.set()
            time.sleep(0.2)
            order.append("first-out")

    def second() -> None:
        started.wait(timeout=2)
        with governor.job(JobKind.RENDER):
            order.append("second-in")

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert order == ["first-in", "first-out", "second-in"]


def test_the_longest_wait_is_recorded() -> None:
    governor = _governor(_profile(gpu=None), heavy_wait_seconds=0.0)
    decision = governor.begin(JobKind.RENDER)
    # A second job cannot get the slot and proceeds after the bounded wait.
    second = governor.begin(JobKind.RENDER)
    try:
        assert second.serialized
        assert governor.snapshot()["stats"]["serialized_jobs"] == 2
    finally:
        governor.end(second)
        governor.end(decision)


def test_counters_separate_gpu_cpu_and_degraded_work() -> None:
    gpu_machine = _governor(_profile(gpu=_gpu(), torch_cuda=True))
    with gpu_machine.job(JobKind.OCR):
        pass
    stats = gpu_machine.snapshot()["stats"]
    assert stats["gpu_jobs"] == 1 and stats["cpu_jobs"] == 0

    cpu_machine = _governor(_profile(gpu=None))
    with cpu_machine.job(JobKind.OCR):
        pass
    stats = cpu_machine.snapshot()["stats"]
    assert stats["cpu_jobs"] == 1 and stats["degraded_jobs"] == 0


def test_encoder_fallback_is_counted() -> None:
    governor = _governor(_profile(gpu=_gpu(), encoders=("h264_nvenc",)))
    governor.note_encoder("h264_nvenc")
    governor.note_encoder_fallback("h264_nvenc")
    stats = governor.snapshot()["stats"]
    assert stats["encoder_fallbacks"] == 1
    assert stats["last_encoder"] == "h264_nvenc->cpu"


# --- reporting --------------------------------------------------------------


def test_explain_answers_before_the_job_starts() -> None:
    governor = _governor(_profile(gpu=_gpu(), torch_cuda=True))
    ready = governor.explain(JobKind.RENDER)
    assert ready["admission"] == "gpu" and ready["blocked_by"] == "ready"
    assert ready["vram_needed_mb"] > 0

    busy = _governor(_profile(gpu=_gpu(utilization=99)), gpu_wait_seconds=30.0)
    explanation = busy.explain(JobKind.OCR)
    assert explanation["admission"] == "cpu"
    assert explanation["blocked_by"] == "utilization"
    assert explanation["would_wait_seconds"] == 30.0
    # Explaining must not consume the slot or change the counters.
    assert busy.snapshot()["active"]["heavy_jobs"] == 0
    assert busy.snapshot()["stats"]["jobs_started"] == 0


def test_snapshot_names_the_hardware_and_advice() -> None:
    machine = _profile(gpu=_gpu(), encoders=("h264_nvenc",), torch_cuda=False)
    snapshot = _governor(machine).snapshot()
    assert snapshot["hardware"]["gpus"][0]["name"].endswith("RTX 4060 Laptop GPU")
    assert snapshot["admission_now"]["render"]["admission"] == "gpu"
    advice = " ".join(snapshot["advice"])
    assert "h264_nvenc" in advice
    assert "torch is CPU-only" in advice


def test_memory_pressure_trims_threads() -> None:
    governor = _governor(
        _profile(ram_available_mb=200), render_threads=4, ram_min_available_mb=700
    )
    assert governor.recommended_threads() == 1
    relaxed = _governor(
        _profile(ram_available_mb=8000), render_threads=4, ram_min_available_mb=700
    )
    assert relaxed.recommended_threads() == 4


def test_recommended_threads_never_exceeds_half_the_cores() -> None:
    governor = _governor(_profile(cpu_count=4, ram_available_mb=8000), render_threads=8)
    assert governor.recommended_threads() == 2


def test_default_governor_is_a_process_singleton() -> None:
    assert default_governor() is default_governor()


# --- the real machine --------------------------------------------------------


def test_probe_of_this_machine_never_raises() -> None:
    """The probe must be safe on Windows, Linux and a machine with no GPU."""
    profile = probe()
    assert profile.cpu_count >= 1
    assert isinstance(profile.encoders, tuple)
    assert profile.to_dict()["probed_at"] > 0


def test_ffmpeg_encoder_probe_parses_a_real_build() -> None:
    from content_factory.resources import _ffmpeg_encoders

    encoders = _ffmpeg_encoders("ffmpeg")
    if not encoders:  # pragma: no cover - ffmpeg not installed on this machine
        pytest.skip("ffmpeg is not installed")
    assert "libx264" in encoders


def test_render_timeout_kills_a_hung_ffmpeg() -> None:
    """The watchdog exists so a stuck encoder cannot pin the machine."""
    from content_factory.render import RenderError, _run_command

    with pytest.raises(RenderError, match="render budget"):
        _run_command(
            ["python", "-c", "import time; time.sleep(30)"],
            1.0,
        )


def test_run_command_returns_the_completed_process() -> None:
    from content_factory.render import _run_command

    completed = _run_command(["python", "-c", "print('ok')"], 30.0)
    assert completed.returncode == 0
    assert "ok" in completed.stdout


def test_run_command_reports_a_missing_binary() -> None:
    from content_factory.render import _run_command

    with pytest.raises(OSError):
        _run_command(["definitely-not-a-binary-xyz"], 5.0)


def test_subprocess_timeout_is_a_render_error_not_a_traceback() -> None:
    from content_factory.render import _run_command

    with pytest.raises(Exception) as caught:
        _run_command(["python", "-c", "import time; time.sleep(5)"], 0.5)
    assert not isinstance(caught.value, subprocess.TimeoutExpired)
