"""Compatibility facade over :mod:`content_factory.services`.

The service used to live in this module; it is now split into cohesive
mixins behind :class:`ContentFactoryService`.  Importing from here keeps
working, and new code is encouraged to import the service package.
"""

from __future__ import annotations

from .services import (
    ContentFactoryService,
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)

__all__ = [
    "ContentFactoryService",
    "NotFoundError",
    "RightsNotConfirmedError",
    "StateConflictError",
]
