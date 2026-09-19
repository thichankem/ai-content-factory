"""Compute-governor agent tools, split out of ``agent_tools.py``.

The two "ask the machine before committing to a long job" tools live here so
``agent_tools.py`` stays under its line budget while the registry still exposes
them through the same manifest at the same position. ``compute_tool_specs()``
builds the specs lazily to avoid a circular import with ``agent_tools``.
"""

from __future__ import annotations

from typing import Any


def _h_resource_status(service: Any, args: Any) -> Any:
    """Hardware, limits, live admission per job kind, and governor counters.

    The profile is read from cache unless the caller asks to re-probe: a status
    question used to cost 1.5-2 s of subprocess work every time it was asked.
    """
    return service.resource_snapshot(refresh=args.boolean("refresh", False))


def _h_resource_explain(service: Any, args: Any) -> Any:
    """Whether a job would use the GPU, the CPU, or wait — before starting it."""
    return service.resource_explain(args.string("kind", "render"))


def compute_tool_specs() -> list[Any]:
    """Build the compute tool specs (lazy import to avoid a cycle)."""
    from .agent_tools import ToolSpec, _p

    return [
        ToolSpec(
            "resource_status",
            "What this machine has (CPU, RAM, GPU, VRAM, temperature, hardware "
            "encoders, CUDA) and how the governor is behaving: live admission per "
            "job kind, jobs serialized, jobs degraded to CPU, encoder fallbacks.",
            "discovery",
            "resource_snapshot",
            _h_resource_status,
            {
                "refresh": _p(
                    "boolean", "Re-probe the hardware instead of using the cache."
                ),
            },
        ),
        ToolSpec(
            "resource_explain",
            "Ask before committing to a long job: would this run on the GPU or the "
            "CPU, and what is blocking it (busy, hot, VRAM, policy)?",
            "discovery",
            "resource_explain",
            _h_resource_explain,
            {
                "kind": _p(
                    "string",
                    "Job kind to test.",
                    enum=["render", "transcribe", "ocr", "vision"],
                    default="render",
                )
            },
        ),
    ]
