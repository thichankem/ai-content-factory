"""The shared shape of the accessibility catalogues.

``photo_assist``, ``video_assist`` and ``audio_assist`` each publish what a
non-vision operator or a text-only agent can do, and each had grown its own
copy of the same assembly: group the operation documents by category, emit the
declared categories first, append any that arrived later, and return
``{"categories": [...], "ops": {...}}``. Three copies meant three places to
change whenever the shape of a catalogue entry moved.

The vocabulary here is deliberately small: an *entry* is what an agent calls,
a *detail* adds the category, and :func:`grouped_catalog` is the envelope the
three endpoints return. Descriptions stay in the modules that own them —
this module only knows how to arrange them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

__all__ = ["detail", "entry", "grouped_catalog"]


def entry(name: str, doc: Mapping[str, Any]) -> dict[str, Any]:
    """One catalogue row: what to call, what it does, how to tune it.

    A missing description falls back to the operation's own name so a newly
    registered op is still discoverable before anyone documents it.
    """
    return {
        "name": name,
        "description": doc.get("description", name),
        "params": doc.get("params", {}),
    }


def detail(name: str, doc: Mapping[str, Any]) -> dict[str, Any]:
    """One described operation: an :func:`entry` plus the category it sits in."""
    return {"name": name, "category": doc.get("category", "other"), **entry(name, doc)}


def grouped_catalog(
    docs: Mapping[str, Mapping[str, Any]],
    order: Iterable[str],
    **extra: Any,
) -> dict[str, Any]:
    """Group ``docs`` by category, ``order`` first and anything else after.

    Every category named in ``order`` appears even when it is empty, so a client
    can render a stable menu instead of having entries appear and disappear as
    operations are registered. ``extra`` is merged into the envelope, which is
    how a catalogue adds its presets or its counts.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for name, doc in docs.items():
        category = str(doc.get("category", "other"))
        groups.setdefault(category, []).append(entry(name, doc))
    declared = list(order)
    ordered = {cat: groups.get(cat, []) for cat in declared}
    for cat in sorted(set(groups) - set(declared)):
        ordered[cat] = groups[cat]
    return {"categories": list(ordered), "ops": ordered, **extra}
