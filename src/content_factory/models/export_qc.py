"""Export pre-flight QC models.

Mirrors ``docs/NLE-STUDIO-FULL-ARCHITECTURE.md`` §5 (``GET /export/preflight-qc``).
The report is what an operator reads at **Gate 2**: every check is one row, and
the verdict is explicit rather than implied by an empty list.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class QCCheckStatus(enum.StrEnum):
    """Outcome of one automated pre-flight check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"


class QCCheck(BaseModel):
    """One automated quality-control finding."""

    code: str
    status: QCCheckStatus = QCCheckStatus.INFO
    message: str
    detail: str | None = None
    hint: str | None = None


class QCReport(BaseModel):
    """The pre-flight verdict an operator reviews before Gate 2 clearance."""

    project_id: str
    ready: bool
    checks: list[QCCheck] = Field(default_factory=list)
    loudness_report: dict[str, object] | None = None
    safe_zone_report: dict[str, object] | None = None
    score: int = Field(default=100, ge=0, le=100)


class ExportPackageRequest(BaseModel):
    """Bundle a project for delivery to one or more platforms."""

    platforms: list[str] = Field(default_factory=lambda: ["youtube"])
    include_subtitles: bool = True
    include_thumbnail: bool = True
    include_lut: bool = False


__all__ = ["ExportPackageRequest", "QCCheck", "QCCheckStatus", "QCReport"]
