"""Script style preset library endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ...models import ScriptStyle
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/script/styles", response_model=list[ScriptStyle])
    async def list_script_styles() -> list[ScriptStyle]:
        return service.list_script_styles()

    @router.get("/script/styles/{name}", response_model=ScriptStyle)
    async def get_script_style(name: str) -> ScriptStyle:
        style = service.get_script_style(name)
        if style is None:
            raise HTTPException(status_code=404, detail="Script style not found")
        return style

    @router.get("/script/styles/{name}/md", response_class=PlainTextResponse)
    async def get_script_style_markdown(name: str) -> PlainTextResponse:
        markdown = service.export_script_style_markdown(name)
        if markdown is None:
            raise HTTPException(status_code=404, detail="Script style not found")
        return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")

    @router.put("/script/styles/{name}", response_model=ScriptStyle)
    async def save_script_style(name: str, data: ScriptStyle) -> ScriptStyle:
        try:
            return service.save_script_style(data.model_copy(update={"name": name}))
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.delete("/script/styles/{name}")
    async def delete_script_style(name: str) -> dict[str, bool]:
        return {"deleted": service.delete_script_style(name)}

    return router
