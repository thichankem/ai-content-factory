"""Domain errors raised by the service layers and mapped to HTTP."""

from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a project id does not exist."""


class StateConflictError(Exception):
    """Raised when an operation is invalid for the current project state."""


class RightsNotConfirmedError(Exception):
    """Raised when script approval is attempted without confirmed rights."""
