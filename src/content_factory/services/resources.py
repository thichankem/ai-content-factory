"""Compute-resource surface of the service.

One thin mixin so an operator or an agent can ask the machine questions before
starting heavy work: what hardware is here, which encoder an export will use,
whether the GPU is free right now, and how many jobs have been serialized or
degraded since the process started.
"""

from __future__ import annotations

from typing import Any

from ..resources import JobKind
from .context import ServiceContext

__all__ = ["ResourcesMixin"]


class ResourcesMixin(ServiceContext):
    """Hardware and scheduling introspection."""

    def resource_snapshot(self, *, refresh: bool = False) -> dict[str, Any]:
        """Hardware profile, governor limits, live admission and counters.

        The profile is cached; ``refresh=True`` re-probes the machine.
        """
        return self._governor.snapshot(refresh=refresh)

    def resource_explain(self, kind: str) -> dict[str, Any]:
        """What would happen to one job kind right now, without starting it."""
        try:
            resolved = JobKind((kind or "").strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Unknown job kind {kind!r}; use one of "
                f"{[str(item) for item in JobKind]}."
            ) from exc
        return self._governor.explain(resolved)
