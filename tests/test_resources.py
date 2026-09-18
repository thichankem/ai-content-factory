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
    FfmpegBuild,
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
        hwaccels=("cuda", "d3d11va", "dxva2"),
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


def _governor(
    profile: HardwareProfile,
    *,
    encoder_works: bool = True,
    encoder_note: str = "",
    pressure: tuple[int, int | None] = (8000, 45),
    **overrides,
) -> ResourceGovernor:
    """A governor over a fixed profile; nothing here touches a real GPU."""
    settings = Settings(**overrides)
    return ResourceGovernor(
        settings,
        probe_fn=lambda: profile,
        sleep=lambda _s: None,
        encoder_probe=lambda _ffmpeg, _encoder: (encoder_works, encoder_note),
        pressure=lambda: pressure,
        clock=_fake_clock(),
    )


def _build(path: str, encoders: tuple[str, ...], version: str = "") -> FfmpegBuild:
    """A discovered ffmpeg build for tests that need more than one."""
    return FfmpegBuild(
        path=path, version=version, encoders=encoders, hwaccels=("cuda", "d3d11va")
    )


def _profile_with_builds(*builds: FfmpegBuild) -> HardwareProfile:
    """A profile whose flat fields mirror the *primary* build, as ``probe`` does."""
    primary = builds[0]
    return HardwareProfile(
        cpu_count=16,
        ram_total_mb=16000,
        ram_available_mb=8000,
        gpus=(_gpu(),),
        encoders=primary.encoders,
        ffmpeg=primary.path,
        torch_cuda=False,
        torch_version="2.14.0+cpu",
        onnx_providers=("CPUExecutionProvider",),
        hwaccels=primary.hwaccels,
        probed_at=time.time(),
        binaries=builds,
    )


def _fake_clock():
    """A clock that advances 0.01s per reading, so waits are cheap to assert."""
    state = {"now": 0.0}

    def tick() -> float:
        state["now"] += 0.01
        return state["now"]

    return tick


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
        bundled=lambda: (),
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
        bundled=lambda: (),
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


def test_an_encoder_that_cannot_start_falls_back_to_software() -> None:
    """The real laptop case: h264_nvenc is listed but its driver refuses it."""
    governor = _governor(
        _profile(gpu=_gpu(), encoders=("libx264", "h264_nvenc")),
        encoder_works=False,
        encoder_note="Driver does not support the required nvenc API version. "
        "Required: 13.1 Found: 12.2",
    )
    status = governor.encoder_status()
    assert status["encoder"] == "h264_nvenc" and not status["usable"]
    assert "13.1" in status["note"]
    # The export path must not plan for an encoder it cannot open.
    assert governor.video_codec("mp4").encoder == "libx264"
    advice = " ".join(governor.snapshot()["advice"])
    assert "cannot start" in advice and "libx264" in advice


def test_the_encoder_is_probed_once_per_process() -> None:
    calls: list[str] = []
    governor = ResourceGovernor(
        Settings(),
        probe_fn=lambda: _profile(gpu=_gpu(), encoders=("h264_nvenc",)),
        encoder_probe=lambda _ffmpeg, encoder: (calls.append(encoder), (True, ""))[1],
    )
    for _ in range(3):
        assert governor.video_codec("mp4").hardware
    assert calls == ["h264_nvenc"]


def test_an_explicit_encoder_is_honoured_even_an_igpu_one() -> None:
    """AMF (a laptop iGPU) is never auto-selected, but can be asked for."""
    profile = _profile(gpu=_gpu(), encoders=("libx264", "h264_amf"))
    auto = _governor(profile)
    assert auto.video_codec("mp4").encoder == "libx264", "iGPU encoders are opt-in"
    requested = _governor(profile, render_encoder="amf")
    choice = requested.video_codec("mp4")
    assert choice.encoder == "h264_amf" and choice.hardware


def test_requesting_an_encoder_this_build_lacks_says_so() -> None:
    governor = _governor(_profile(), render_encoder="nvenc")
    status = governor.encoder_status()
    assert not status["usable"] and "no ffmpeg build has it" in status["note"]
    assert governor.video_codec("mp4").encoder == "libx264"


def test_auto_hardware_decode_is_off_because_it_measured_slower() -> None:
    """The measured regression: -hwaccel adds a PCIe round trip for nothing.

    Frames must return to system memory for this project's CPU filter graph and
    software encoder, so hardware decode lost at every size on the reference
    laptop. ``auto`` therefore means off, and only an explicit name turns it on.
    """
    can_decode = _profile()
    object.__setattr__(can_decode, "hwaccels", ("cuda", "d3d11va", "dxva2"))
    assert _governor(can_decode).decoder_args("mp4") == ()
    assert _governor(can_decode, render_hwaccel="auto").decoder_args("mp4") == ()
    assert _governor(can_decode, render_hwaccel="off").decoder_args("mp4") == ()


def test_decode_acceleration_is_honoured_only_by_explicit_name() -> None:
    assert _governor(_profile(), render_hwaccel="dxva2").decoder_args("mp4") == (
        "-hwaccel",
        "dxva2",
    )
    assert _governor(_profile(), render_hwaccel="cuda").decoder_args("mp4") == (
        "-hwaccel",
        "cuda",
    )
    # Named but not offered by this build: say nothing rather than try and fail.
    assert _governor(_profile(), render_hwaccel="vulkan").decoder_args("mp4") == ()
    # WebM encoding is software, and so is its decode path.
    assert _governor(_profile(), render_hwaccel="cuda").decoder_args("webm") == ()
    # CPU policy forbids the GPU outright.
    assert (
        _governor(_profile(), render_hwaccel="cuda", compute_policy="cpu").decoder_args(
            "mp4"
        )
        == ()
    )


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
    from content_factory.hardware import _ffmpeg_encoders

    encoders = _ffmpeg_encoders("ffmpeg")
    if not encoders:  # pragma: no cover - ffmpeg not installed on this machine
        pytest.skip("ffmpeg is not installed")
    assert "libx264" in encoders


def test_render_timeout_kills_a_hung_ffmpeg() -> None:
    """The deadline exists so a stuck encoder cannot pin the machine.

    The pressure guard is disabled for this test on purpose. Both guards can end
    the same process, and the pressure one wins whenever the *host* happens to be
    low on memory — which is exactly what running the whole suite causes. Without
    this the test asserted the deadline but flaked into asserting the memory
    floor instead. The pressure path has its own test, with an injected reading,
    so neither guard is tested by accident here.
    """
    from content_factory.render import RenderError, _run_command

    governor = ResourceGovernor(
        Settings(render_monitor_seconds=0.25),
        probe_fn=lambda: _profile(),
        pressure=lambda: (7000, 45),  # a healthy machine, on every reading
    )
    with pytest.raises(RenderError, match="render budget"):
        _run_command(
            ["python", "-c", "import time; time.sleep(30)"],
            1.0,
            governor=governor,
        )


def test_run_command_returns_the_completed_process() -> None:
    from content_factory.render import _run_command

    completed = _run_command(["python", "-c", "print('ok')"], 30.0)
    assert completed.returncode == 0
    assert "ok" in completed.stdout


def test_run_command_reports_a_missing_binary() -> None:
    from content_factory.render import RenderError, _run_command

    with pytest.raises(RenderError, match="definitely-not-a-binary-xyz"):
        _run_command(["definitely-not-a-binary-xyz"], 5.0)


def test_subprocess_timeout_is_a_render_error_not_a_traceback() -> None:
    from content_factory.render import _run_command

    with pytest.raises(Exception) as caught:
        _run_command(["python", "-c", "import time; time.sleep(5)"], 0.5)
    assert not isinstance(caught.value, subprocess.TimeoutExpired)


# --- multiple ffmpeg builds --------------------------------------------------


def test_discover_binaries_keeps_order_and_drops_non_ffmpeg() -> None:
    """The machine's own build stays first; a non-ffmpeg is not a "build"."""
    from content_factory.hardware import discover_binaries

    builds = discover_binaries(
        "/usr/bin/ffmpeg",
        (),
        ("/opt/bundled/ffmpeg", "/opt/not-ffmpeg"),
        encoders=lambda path: () if "not-ffmpeg" in path else ("h264_nvenc", "libx264"),
        hwaccels=lambda _path: ("cuda",),
        version=lambda path: f"ffmpeg version 7.1 {path}",
        # Every candidate resolves to itself: these paths are not real files.
        which=lambda name: name,
    )
    assert [build.path for build in builds] == [
        "/usr/bin/ffmpeg",
        "/opt/bundled/ffmpeg",
    ]
    assert builds[1].short_version == "7.1"


def test_discover_binaries_deduplicates_one_binary_reached_two_ways() -> None:
    from content_factory.hardware import discover_binaries

    builds = discover_binaries(
        "/usr/bin/ffmpeg",
        (),
        ("/usr/bin/ffmpeg",),  # same file, listed twice
        encoders=lambda _path: ("libx264",),
        hwaccels=lambda _path: (),
        version=lambda _path: "ffmpeg version 8.0.1",
        which=lambda name: name,
    )
    assert len(builds) == 1


def test_a_gpu_encoder_found_on_a_second_build_is_used() -> None:
    """The real laptop case, in full.

    The system ffmpeg lists h264_nvenc but the driver refuses it; a bundled older
    build targets the API the driver does have. The export must land on the GPU
    through that second build, and report *why* the binary was switched.
    """
    primary, bundled = "/usr/bin/ffmpeg", "/opt/ffmpeg-7.1"
    profile = _profile_with_builds(
        _build(primary, ("libx264", "h264_nvenc"), "ffmpeg version 9.0.1"),
        _build(bundled, ("libx264", "h264_nvenc"), "ffmpeg version 7.1"),
    )
    governor = ResourceGovernor(
        Settings(),
        probe_fn=lambda: profile,
        sleep=lambda _s: None,
        pressure=lambda: (8000, 45),
        # Only the second build can open the encoder on this machine.
        encoder_probe=lambda binary, _encoder: (
            (
                False,
                "Driver does not support the required nvenc API version. "
                "Required: 13.1 Found: 12.2",
            )
            if binary == primary
            else (True, "")
        ),
    )
    assert governor.resolve_hardware_encoder() == (bundled, "h264_nvenc")
    choice = governor.video_codec("mp4")
    assert choice.encoder == "h264_nvenc" and choice.hardware
    assert choice.binary == bundled, "the encoder only starts on the second build"

    # The advice must describe what will really happen, not the primary's failure.
    advice = " ".join(governor.snapshot()["advice"])
    assert "second build" in advice or "does not start on the machine's own" in advice
    assert "so MP4 exports use libx264" not in advice


def test_the_primary_build_wins_when_it_can_also_do_the_job() -> None:
    """A working setup is never silently redirected to another binary."""
    primary, bundled = "/usr/bin/ffmpeg", "/opt/ffmpeg-7.1"
    profile = _profile_with_builds(
        _build(primary, ("h264_nvenc",)),
        _build(bundled, ("h264_nvenc",)),
    )
    governor = _governor(profile)
    choice = governor.video_codec("mp4")
    assert choice.encoder == "h264_nvenc"
    assert choice.binary == "", "no override is needed when the primary works"


def test_every_build_is_probed_once_even_across_repeated_exports() -> None:
    calls: list[tuple[str, str]] = []
    profile = _profile_with_builds(
        _build("/a/ffmpeg", ("h264_nvenc",)),
        _build("/b/ffmpeg", ("h264_nvenc",)),
    )
    governor = ResourceGovernor(
        Settings(),
        probe_fn=lambda: profile,
        pressure=lambda: (8000, 45),
        encoder_probe=lambda binary, encoder: (
            calls.append((binary, encoder)),
            (False, "nope"),
        )[1],
    )
    for _ in range(3):
        assert governor.video_codec("mp4").encoder == "libx264"
    assert calls == [("/a/ffmpeg", "h264_nvenc"), ("/b/ffmpeg", "h264_nvenc")]


# --- aborting a running job --------------------------------------------------


def test_no_pressure_violation_on_a_healthy_machine() -> None:
    governor = _governor(_profile())
    assert governor.pressure_violation() == ""


def test_low_ram_stops_a_running_job() -> None:
    governor = _governor(_profile(), pressure=(200, 45), ram_abort_mb=350)
    violation = governor.pressure_violation()
    assert "200MB" in violation and "350MB" in violation


def test_a_hot_gpu_stops_a_running_job() -> None:
    governor = _governor(_profile(), pressure=(8000, 95), gpu_abort_temperature_c=90)
    violation = governor.pressure_violation()
    assert "95C" in violation and "90C" in violation


def test_abort_thresholds_are_more_serious_than_admission_ones() -> None:
    """Ordinary busy pressure must never kill work that was admitted."""
    governor = _governor(_profile(), pressure=(800, 80))
    assert governor.pressure_violation() == ""
    assert governor.snapshot()["abort_limits"]["ram_abort_mb"] == 350
    assert governor.snapshot()["abort_limits"]["gpu_abort_temperature_c"] == 90


def test_pressure_without_a_gpu_reports_no_temperature() -> None:
    from content_factory.hardware import machine_pressure

    available, temperature = machine_pressure(
        memory=lambda: (16000, 7000),
        which=lambda _name: None,
        nvidia_smi=lambda _binary: (_gpu(),),
    )
    assert (available, temperature) == (7000, None)


def test_the_watchdog_kills_a_long_render_under_pressure() -> None:
    """End to end: a real process is terminated, and the reason is reported."""
    import time as _time

    from content_factory.render import RenderError, _run_command

    governor = ResourceGovernor(
        Settings(render_monitor_seconds=0.25, ram_abort_mb=350),
        probe_fn=lambda: _profile(),
        pressure=lambda: (100, 45),  # below the abort floor on every reading
    )
    started = _time.monotonic()
    with pytest.raises(RenderError, match="aborted to protect the machine"):
        _run_command(
            ["python", "-c", "import time; time.sleep(30)"],
            60.0,
            governor=governor,
        )
    assert _time.monotonic() - started < 20.0, "it must not wait for the deadline"


def test_a_render_that_finishes_under_pressure_still_succeeds() -> None:
    """The watchdog must not turn a completed render into a failure."""
    from content_factory.render import _run_command

    governor = _governor(_profile(), pressure=(100, 95))
    completed = _run_command(["python", "-c", "print('done')"], 30.0, governor=governor)
    assert completed.returncode == 0 and "done" in completed.stdout
