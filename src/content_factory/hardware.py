"""What this machine actually is: a measured hardware profile.

Every function here is a *reading*, never a decision — :mod:`content_factory.
resources` turns these readings into policy. Keeping them apart is what lets the
governor be tested against a fixed profile without a GPU, a driver or ffmpeg.

The one idea worth knowing before reading on: **an encoder is a property of a
ffmpeg build, not of its name.** The same ``h264_nvenc`` that a build advertises
may be refused by the installed driver because that build was compiled against a
newer NVENC API. So the profile records every usable ffmpeg binary it can find —
the machine's own, operator-supplied extras, and a build bundled inside an
installed Python package — and the governor opens each candidate for real before
believing it.

Standard library only (``nvidia-smi`` plus ``ctypes`` for RAM), so nothing has to
be installed and a machine without a GPU degrades to "no GPU" rather than failing.
"""

from __future__ import annotations

import ctypes
import importlib
import os
import platform
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from .compute import FfmpegBuild, GpuInfo, HardwareProfile

__all__ = [
    "discover_binaries",
    "machine_pressure",
    "probe",
    "probe_encoder",
]

#: Extra builds to look for when the primary ffmpeg cannot start an encoder.
#: ``imageio-ffmpeg`` pins a gyan.dev build; it is a transitive extra of this
#: project rather than a declared dependency, so it is used only when the package
#: happens to be installed (exactly like torch and onnxruntime below).
_BUNDLED_FFMPEGS: tuple[str, ...] = ("imageio_ffmpeg",)


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


def _ffmpeg_hwaccels(binary: str) -> tuple[str, ...]:
    """Hardware decode methods this ffmpeg build advertises."""
    try:
        completed = subprocess.run(
            [binary, "-hide_banner", "-hwaccels"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    lines = completed.stdout.splitlines()
    return tuple(
        line.strip()
        for line in lines[1:]
        if line.strip() and not line.lower().startswith("hardware")
    )


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


def _ffmpeg_version(binary: str) -> str:
    """The banner of an ffmpeg build (``ffmpeg version 8.0.1-…``), or ``""``."""
    try:
        completed = subprocess.run(
            [binary, "-hide_banner", "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    first = completed.stdout.splitlines()[:1]
    return first[0].strip() if first else ""


def machine_pressure(
    *,
    memory: Callable[[], tuple[int, int]] = _system_memory_mb,
    which: Callable[[str], str | None] = shutil.which,
    nvidia_smi: Callable[[str], tuple[GpuInfo, ...]] = _nvidia_smi_gpus,
) -> tuple[int, int | None]:
    """``(ram_available_mb, gpu_temperature_c)`` — cheap enough to poll.

    Deliberately *not* :func:`probe`. This runs every few seconds while a render
    is in flight, and the full probe spawns six ffmpeg processes to read encoder
    and hwaccel tables — overhead the watchdog would then be adding to the very
    machine it is watching. Reading RAM and a GPU temperature costs one syscall
    and one ``nvidia-smi`` call.
    """
    _, available_mb = memory()
    smi = which("nvidia-smi")
    gpus = nvidia_smi(smi) if smi else ()
    return available_mb, (gpus[0].temperature_c if gpus else None)


def _bundled_ffmpeg_candidates() -> tuple[str, ...]:
    """ffmpeg binaries shipped inside installed Python packages.

    ``imageio-ffmpeg`` pins a specific gyan.dev build. Different builds target
    different NVENC API versions, so an older bundled build can start a GPU
    encoder that a newer system build cannot — which is the whole reason this
    exists. Absent package, absent candidate: never an error.
    """
    found: list[str] = []
    for module_name in _BUNDLED_FFMPEGS:
        try:
            module = importlib.import_module(module_name)
            exe = module.get_ffmpeg_exe()
        except Exception:  # noqa: BLE001 - optional dependency of any shape
            continue
        if exe and Path(exe).is_file():
            found.append(str(exe))
    return tuple(found)


def _extra_binaries(setting: str) -> tuple[str, ...]:
    """Operator-supplied extra ffmpeg builds (``os.pathsep``-separated).

    This is the escape hatch for a machine whose working build is neither on
    ``PATH`` nor bundled: point ``CONTENT_FACTORY_FFMPEG_EXTRA_BINARIES`` at it
    and the governor will prefer it whenever it starts an encoder the primary
    one cannot.
    """
    if not setting:
        return ()
    parts = [part.strip().strip('"') for part in setting.split(os.pathsep)]
    return tuple(part for part in parts if part)


def _binary_key(path: str) -> str:
    """Identity for de-duplicating binaries across spellings of one path."""
    return os.path.normcase(os.path.abspath(path))


def discover_binaries(
    primary: str | None,
    extras: tuple[str, ...],
    bundled: tuple[str, ...] = (),
    *,
    encoders: Callable[[str], tuple[str, ...]] = _ffmpeg_encoders,
    hwaccels: Callable[[str], tuple[str, ...]] = _ffmpeg_hwaccels,
    version: Callable[[str], str] = _ffmpeg_version,
    which: Callable[[str], str | None] = shutil.which,
) -> tuple[FfmpegBuild, ...]:
    """Probe each distinct ffmpeg build once, primary first.

    Ordering is the policy: the machine's own ffmpeg wins unless it cannot do
    the job, so a working setup is never silently redirected to another build.
    A candidate that cannot list encoders is not an ffmpeg at all and is dropped
    rather than reported as a build.
    """
    ordered: list[str] = []
    keys: set[str] = set()
    for candidate in (primary, *extras, *bundled):
        if not candidate:
            continue
        resolved = candidate if Path(candidate).is_file() else which(candidate)
        if not resolved or _binary_key(resolved) in keys:
            continue
        keys.add(_binary_key(resolved))
        ordered.append(resolved)
    builds: list[FfmpegBuild] = []
    for path in ordered:
        names = encoders(path)
        if not names:
            continue
        builds.append(
            FfmpegBuild(
                path=path,
                version=version(path),
                encoders=names,
                hwaccels=hwaccels(path),
            )
        )
    return tuple(builds)


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
        # 320x240, not 64x64: some encoders (AMD AMF) refuse tiny frames, and a
        # probe that fails for the wrong reason would hide a working GPU.
        "color=c=black:size=320x240:duration=0.1:rate=10",
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
    # Keep the line that explains *why* (driver/API mismatch reads much better
    # than the thread-teardown noise that follows it).
    hints = ("nvenc api", "minimum required", "driver", "cannot load", "no capable")
    preferred = [line for line in lines if any(hint in line.lower() for hint in hints)]
    return False, " ".join((preferred or lines)[-2:])[:300] or "the encoder refused job"


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
    hwaccels: Callable[[str], tuple[str, ...]] = _ffmpeg_hwaccels,
    memory: Callable[[], tuple[int, int]] = _system_memory_mb,
    torch_state: Callable[[], tuple[bool, str]] = _torch_state,
    onnx: Callable[[], tuple[str, ...]] = _onnx_providers,
    cpu_count: Callable[[], int | None] = os.cpu_count,
    discover: Callable[..., tuple[FfmpegBuild, ...]] = discover_binaries,
    bundled: Callable[[], tuple[str, ...]] = _bundled_ffmpeg_candidates,
    ffmpeg_binary: str | None = None,
    extra_binaries: str = "",
) -> HardwareProfile:
    """Measure this machine. Every probe is injectable so tests need no GPU."""
    smi = which("nvidia-smi")
    builds = discover(
        ffmpeg_binary or which("ffmpeg"),
        _extra_binaries(extra_binaries),
        bundled(),
        encoders=encoders,
        hwaccels=hwaccels,
        which=which,
    )
    primary = builds[0] if builds else None
    total_mb, available_mb = memory()
    cuda, torch_version = torch_state()
    return HardwareProfile(
        cpu_count=int(cpu_count() or 1),
        ram_total_mb=total_mb,
        ram_available_mb=available_mb,
        gpus=nvidia_smi(smi) if smi else (),
        encoders=primary.encoders if primary else (),
        ffmpeg=primary.path if primary else None,
        torch_cuda=cuda,
        torch_version=torch_version,
        onnx_providers=onnx(),
        hwaccels=primary.hwaccels if primary else (),
        probed_at=time.time(),
        binaries=builds,
    )
