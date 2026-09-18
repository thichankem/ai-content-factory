"""Path sandbox: confine MCP tool file access to allowed asset directories.

Agents should never roam the host filesystem through a tool. Every file the
MCP server reads or writes must resolve inside one of the configured roots
(the media library, uploads, cache, library, and storage trees). This module
provides the single resolver that enforces that rule.
"""

from __future__ import annotations

from pathlib import Path


class SandboxError(ValueError):
    """Raised when a path escapes the allowed asset directories."""


class Sandbox:
    """Resolves user-supplied paths, rejecting anything outside the roots."""

    def __init__(self, allowed: list[str | Path]) -> None:
        self._roots = [Path(p).expanduser().resolve() for p in allowed]

    @property
    def roots(self) -> list[Path]:
        """The resolved allowed directories."""
        return list(self._roots)

    def resolve(self, path: str | Path) -> Path:
        """Resolve ``path`` absolutely and require it inside an allowed root."""
        candidate = Path(path).expanduser().resolve()
        if not any(
            candidate == root or root in candidate.parents for root in self._roots
        ):
            raise SandboxError(f"path outside allowed directories: {path}")
        return candidate

    def contains(self, path: str | Path) -> bool:
        """Whether ``path`` resolves inside an allowed root (no raise)."""
        try:
            self.resolve(path)
            return True
        except SandboxError:
            return False
