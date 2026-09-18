"""Historical events, maps and infographics."""

from __future__ import annotations

from fastapi import APIRouter

from ...models import OnThisDayEvent
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/history/on-this-day", response_model=list[OnThisDayEvent])
    def get_on_this_day(
        month: int | None = None, day: int | None = None
    ) -> list[OnThisDayEvent]:
        """Get notable historical disasters/events for today or a specific date."""
        return service.get_on_this_day(month=month, day=day)

    @router.get("/history/search", response_model=list[OnThisDayEvent])
    def search_history(q: str) -> list[OnThisDayEvent]:
        """Search historical catastrophe database by keyword or location."""
        return service.search_history_events(q)

    return router
