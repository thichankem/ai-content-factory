"""Shared parameter coercion for the media engines.

The image, video and audio engines all read their parameters out of an untyped
mapping — an HTTP form field, a tool call, or an ``ImageOp`` object wrapping
one. Each engine had grown its own private copy of the same three coercions
(``_num``, ``_seed``, ``_clamp01``) with the same bodies and the same error
messages, differing only in which exception class they raised. They now share
the implementations here and pass their own error type in, so a coercion fix
lands in exactly one place and no caller's contract changes.

A *source* is either a plain mapping or any object exposing one on ``.params``,
which is what lets ``photo_ops`` (handed :class:`ImageOp` objects) and
``audio_effects`` (handed dicts) use the same helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = [
    "ParamError",
    "clamp01",
    "flag",
    "number",
    "params_of",
    "seed",
]


class ParamError(ValueError):
    """Raised when an operation's parameters cannot be coerced to their types."""


def params_of(source: Any) -> Mapping[str, Any]:
    """The parameter mapping behind ``source``.

    Accepts a mapping directly, or any object carrying one on ``.params`` — how
    an :class:`~content_factory.image_engine.ImageOp` exposes its fields.
    """
    if isinstance(source, Mapping):
        return source
    params = getattr(source, "params", None)
    if isinstance(params, Mapping):
        return params
    raise ParamError(
        "Expected a parameter mapping or an object with .params, got "
        f"{type(source).__name__}."
    )


def number(
    source: Any, key: str, default: float, *, error: type[Exception] = ParamError
) -> float:
    """Coerce ``source[key]`` to a float, falling back to ``default`` when absent.

    ``error`` is the exception type the calling layer already speaks, so the
    failure a caller observes is the same one it observed before this helper
    existed.
    """
    params = params_of(source)
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise error(f"'{key}' must be a number.") from exc


def flag(source: Any, key: str, default: bool) -> bool:
    """Read ``source[key]`` as a boolean, falling back to ``default``."""
    return bool(params_of(source).get(key, default))


def seed(source: Any, key: str = "seed", default: int = 0) -> int:
    """Read a deterministic RNG seed, tolerating anything unparseable.

    A malformed seed is not worth failing an operation over: every effect that
    uses one is decorative, so an unusable value falls back to the default and
    the result stays reproducible.
    """
    try:
        return int(params_of(source).get(key, default))
    except (TypeError, ValueError):
        return default


def clamp01(value: Any) -> float:
    """Clamp a scalar to the 0..1 range."""
    return max(0.0, min(1.0, float(value)))
