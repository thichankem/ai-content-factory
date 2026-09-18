"""Service layer, split into cohesive mixins over a shared context."""

from __future__ import annotations

from .agents import AgentsMixin
from .context import ServiceContext
from .errors import (
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)
from .growth import GrowthMixin
from .history import HistoryMixin
from .knowledge import KnowledgeMixin
from .media import MediaMixin
from .media_tools import MediaToolsMixin
from .production import ProductionMixin
from .projects import ProjectsMixin
from .qa import QaMixin
from .research import ResearchMixin
from .resources import ResourcesMixin
from .scripting import ScriptingMixin
from .seo import SeoMixin
from .styles import StylesMixin
from .timeline import TimelineMixin
from .voice import VoiceMixin
from .workflow import WorkflowMixin


class ContentFactoryService(
    ResourcesMixin,
    QaMixin,
    SeoMixin,
    WorkflowMixin,
    ProductionMixin,
    StylesMixin,
    KnowledgeMixin,
    HistoryMixin,
):
    """Coordinates projects, the provider chain, and the state machine.

    Composed from one mixin per domain; see the individual modules for
    the operations they contribute.
    """


__all__ = [
    "AgentsMixin",
    "ContentFactoryService",
    "GrowthMixin",
    "HistoryMixin",
    "KnowledgeMixin",
    "MediaMixin",
    "MediaToolsMixin",
    "NotFoundError",
    "ProductionMixin",
    "ProjectsMixin",
    "QaMixin",
    "ResearchMixin",
    "ResourcesMixin",
    "RightsNotConfirmedError",
    "ScriptingMixin",
    "SeoMixin",
    "ServiceContext",
    "StateConflictError",
    "StylesMixin",
    "TimelineMixin",
    "VoiceMixin",
    "WorkflowMixin",
]
