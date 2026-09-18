"""Route builders, one module per API surface."""

from .agents import build_router as build_agents_router
from .campaign import build_router as build_campaign_router
from .external import build_router as build_external_router
from .graphics import build_router as build_graphics_router
from .health import build_router as build_health_router
from .history import build_router as build_history_router
from .index import build_router as build_index_router
from .knowledge import build_router as build_knowledge_router
from .library import build_router as build_library_router
from .media import build_router as build_media_router
from .projects import build_router as build_projects_router
from .qa import build_router as build_qa_router
from .resources import build_router as build_resources_router
from .seo import build_router as build_seo_router
from .studio_media import build_router as build_studio_media_router
from .styles import build_router as build_styles_router
from .timeline import build_router as build_timeline_router
from .tools import build_router as build_tools_router
from .workflow import build_router as build_workflow_router

__all__ = [
    "build_health_router",
    "build_projects_router",
    "build_styles_router",
    "build_agents_router",
    "build_library_router",
    "build_timeline_router",
    "build_workflow_router",
    "build_campaign_router",
    "build_knowledge_router",
    "build_studio_media_router",
    "build_media_router",
    "build_tools_router",
    "build_external_router",
    "build_history_router",
    "build_graphics_router",
    "build_index_router",
    "build_qa_router",
    "build_resources_router",
    "build_seo_router",
]
