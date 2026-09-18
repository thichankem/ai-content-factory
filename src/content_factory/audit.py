"""Append-only provenance / audit trail for the AI Content Factory.

Every meaningful pipeline action (script drafted, gate approved, video
published, cost guarded, ...) can be recorded as one JSON line in an append-only
``audit.jsonl`` file. The log never rewrites history — it only ever appends —
so a tamper-evident, chronological record of "who did what, when" is kept.

  * :class:`AuditLog` — thread-safe append-only log backed by ``audit.jsonl``.
  * :class:`AuditEntry` — one immutable record.

Reading is tolerant: missing files yield an empty log and corrupt JSON lines
are skipped rather than raising.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class AuditEntry:
    """One immutable audit record."""

    ts: str
    actor: str
    action: str
    project_id: str | None
    media_id: str | None
    prompt: str | None
    detail: str | None


class AuditLog:
    """An append-only, thread-safe audit trail stored as JSON lines.

    Entries are appended to ``<audit_dir>/audit.jsonl``, creating the directory
    on construction. Reading tolerates missing files and corrupt lines.
    """

    def __init__(self, audit_dir: str) -> None:
        self._dir = Path(audit_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "audit.jsonl"
        self._lock = threading.RLock()

    def record(
        self,
        actor: str,
        action: str,
        *,
        project_id: str | None = None,
        media_id: str | None = None,
        prompt: str | None = None,
        detail: str | None = None,
    ) -> AuditEntry:
        """Append one entry and return it."""
        entry = AuditEntry(
            ts=datetime.now(UTC).isoformat(),
            actor=actor,
            action=action,
            project_id=project_id,
            media_id=media_id,
            prompt=prompt,
            detail=detail,
        )
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def entries(self, limit: int = 200) -> list[AuditEntry]:
        """Return the most recent ``limit`` entries, newest first."""
        all_entries = self._read_valid()
        return all_entries[::-1][:limit]

    def count(self) -> int:
        """Return the number of valid entries in the log."""
        return len(self._read_valid())

    def _read_valid(self) -> list[AuditEntry]:
        """Parse every valid entry in file order, skipping corrupt lines."""
        with self._lock:
            if not self._path.exists():
                return []
            lines = self._path.read_text(encoding="utf-8").splitlines()

        parsed: list[AuditEntry] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                parsed.append(AuditEntry(**data))
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                continue
        return parsed
