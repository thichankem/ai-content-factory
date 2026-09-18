"""External AI asset and dossier ingestion endpoints."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    File,
    Form,
    UploadFile,
)

from ...models import (
    BatchExternalImportRequest,
    ExternalAssetRecord,
    ExternalAssetType,
    ExternalImportRequest,
)
from ...service import ContentFactoryService
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post(
        "/projects/{project_id}/external/import",
        response_model=ExternalAssetRecord,
    )
    def import_external_asset(
        project_id: str, payload: ExternalImportRequest
    ) -> ExternalAssetRecord:
        """Link an external media asset or research dossier into the project."""
        return guard_value(lambda: service.import_external_asset(project_id, payload))

    @router.post(
        "/projects/{project_id}/external/upload",
        response_model=ExternalAssetRecord,
    )
    async def upload_external_asset(
        project_id: str,
        asset_type: ExternalAssetType = Form(...),  # noqa: B008
        scene_id: str | None = Form(None),  # noqa: B008
        attribution: str | None = Form(None),  # noqa: B008
        file: UploadFile = File(...),  # noqa: B008
    ) -> ExternalAssetRecord:
        """Upload a local media file (video/image/audio) and bind to scene."""
        content = await file.read()
        return guard_value(
            lambda: service.upload_external_file(
                project_id=project_id,
                filename=file.filename or "uploaded_media",
                content=content,
                asset_type=asset_type,
                scene_id=scene_id,
                attribution=attribution,
            )
        )

    @router.post(
        "/projects/{project_id}/external/batch-import",
        response_model=list[ExternalAssetRecord],
    )
    def batch_import_external_assets(
        project_id: str, payload: BatchExternalImportRequest
    ) -> list[ExternalAssetRecord]:
        """Batch import multiple external assets into a project."""
        return guard_value(
            lambda: service.batch_import_external_assets(project_id, payload.items)
        )

    @router.get(
        "/projects/{project_id}/external/assets",
        response_model=list[ExternalAssetRecord],
    )
    def list_external_assets(project_id: str) -> list[ExternalAssetRecord]:
        """List all external assets linked or uploaded to the project."""
        return guard_value(lambda: service.list_external_assets(project_id))

    return router
