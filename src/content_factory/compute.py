"""Value types for compute scheduling: what the machine is, what a job needs.

These carry no behaviour beyond parsing and serialising themselves, which is what
lets :mod:`content_factory.hardware` (readings) and
:mod:`content_factory.resources` (policy) share one vocabulary without importing
each other. Nothing here touches the machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "Admission",
    "CodecChoice",
    "Decision",
    "FfmpegBuild",
    "GpuInfo",
    "HardwareProfile",
    "JobKind",
]

#: Encoder names ffmpeg may expose that put the work on the GPU.
_HARDWARE_ENCODERS = ("h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "h264_amf")

#: Encoders ``auto`` will choose. Only discrete-class encoders are here on
#: purpose: an integrated GPU's encoder (AMF/QSV on a laptop iGPU) is much
#: slower per bit and produces far bigger files at equal quality, so it is an
#: explicit choice (``render_encoder: "amf"``), never a silent one.
_AUTO_ENCODER_PREFERENCE = ("h264_nvenc", "h264_qsv")

#: Encoders an operator may request by name in ``render_encoder``.
_REQUESTABLE_ENCODERS = {
    "nvenc": "h264_nvenc",
    "qsv": "h264_qsv",
    "amf": "h264_amf",
}

#: Decode accelerations worth reporting (``ffmpeg -hwaccels`` lists more).
_HWACCEL_NAMES = frozenset(
    {
        "cuda",
        "d3d11va",
        "dxva2",
        "d3d12va",
        "qsv",
        "vaapi",
        "vulkan",
        "amf",
        "opencl",
    }
)


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
class FfmpegBuild:
    """One ffmpeg binary and what it can do.

    Builds are not interchangeable. The interesting case is real and common: a
    brand-new ffmpeg requires a newer NVENC API than the installed NVIDIA driver
    provides, so its ``h264_nvenc`` exists but refuses to start — while an older
    build shipped alongside a Python package targets the older API and encodes
    on the GPU happily. The encoder is a property of the *(binary, encoder)*
    pair, never of the encoder name alone, so both travel together.
    """

    path: str
    version: str
    encoders: tuple[str, ...]
    hwaccels: tuple[str, ...]

    @property
    def short_version(self) -> str:
        """``8.0.1`` from ``ffmpeg version 8.0.1-full_build-…``."""
        for token in self.version.split():
            if token[:1].isdigit():
                return token.split("-")[0]
        return self.version

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "version": self.short_version,
            "encoders": [name for name in self.encoders if name in _HARDWARE_ENCODERS],
            "hwaccels": [name for name in self.hwaccels if name in _HWACCEL_NAMES],
        }


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
    hwaccels: tuple[str, ...] = ()
    probed_at: float = 0.0
    #: Every usable ffmpeg binary, primary first (``ffmpeg`` and ``encoders``
    #: above mirror ``binaries[0]`` so older callers keep working).
    binaries: tuple[FfmpegBuild, ...] = ()

    @property
    def gpu(self) -> GpuInfo | None:
        return self.gpus[0] if self.gpus else None

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpus)

    def hardware_video_encoder(self) -> str | None:
        """Discrete-class hardware H.264 encoder this build exposes, if any.

        This only reads the build's encoder table — it says nothing about
        whether the driver lets the encoder start. ``ResourceGovernor.
        resolve_hardware_encoder`` is the one that proves it.
        """
        for name in _AUTO_ENCODER_PREFERENCE:
            if name in self.encoders:
                return name
        return None

    def build(self, path: str | None) -> FfmpegBuild | None:
        """The discovered build at ``path``, if it was probed."""
        for item in self.binaries:
            if item.path == path:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_count": self.cpu_count,
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_available_mb,
            "gpus": [gpu.to_dict() for gpu in self.gpus],
            "encoders": [name for name in self.encoders if name in _HARDWARE_ENCODERS],
            "ffmpeg": self.ffmpeg,
            "binaries": [item.to_dict() for item in self.binaries],
            "torch_cuda": self.torch_cuda,
            "torch_version": self.torch_version,
            "onnx_providers": list(self.onnx_providers),
            "hwaccels": list(self.hwaccels),
            "probed_at": round(self.probed_at, 3),
        }


#: Prefix used in ``CodecChoice.binary`` when the choice needs no override.
_DEFAULT_BINARY = ""


@dataclass(frozen=True)
class CodecChoice:
    """The video encoder an export will use, and the binary that runs it.

    ``binary`` is empty when the caller's own ffmpeg is fine, and a path when
    the encoder only starts on a *different* build (see :class:`FfmpegBuild`).
    """

    encoder: str
    hardware: bool
    args: tuple[str, ...]
    binary: str = _DEFAULT_BINARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder": self.encoder,
            "hardware": self.hardware,
            "binary": self.binary or None,
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
