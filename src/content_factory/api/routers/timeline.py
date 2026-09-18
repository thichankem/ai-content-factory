"""Video studio: timeline NLE, render plan, video and voiceover."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from ...models import (
    AiAssistRequest,
    MarkerCreate,
    Project,
    RenderPlan,
    RenderRequest,
    SceneAudioRequest,
    SceneBulkRequest,
    SceneClipResponse,
    SceneMoveRequest,
    ScenePasteRequest,
    SceneReverseRequest,
    SceneSpeedRequest,
    SceneSplitRequest,
    SceneTrimRequest,
    StructuredTimeline,
    TimelineReport,
    VideoEditUpdate,
    VideoProject,
)
from ...render import RenderError
from ...service import ContentFactoryService, NotFoundError
from ..deps import get_or_404, guard, guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/projects/{project_id}/video-project", response_model=VideoProject)
    async def get_video_project(project_id: str) -> VideoProject:
        project = get_or_404(service, project_id)
        if project.video_project is None:
            raise HTTPException(
                status_code=404, detail="No video project has been built yet"
            )
        return project.video_project

    @router.put("/projects/{project_id}/video-project", response_model=Project)
    async def update_video_project(project_id: str, data: VideoEditUpdate) -> Project:
        return guard(lambda: service.update_video_project(project_id, data.project))

    @router.get("/projects/{project_id}/timeline/report", response_model=TimelineReport)
    async def timeline_report(project_id: str) -> TimelineReport:
        return guard_value(lambda: service.timeline_report(project_id))

    @router.get("/projects/{project_id}/render-plan", response_model=RenderPlan)
    async def render_plan(project_id: str) -> RenderPlan:
        return guard_value(lambda: service.render_plan(project_id))

    @router.post("/projects/{project_id}/timeline/normalize", response_model=Project)
    async def normalize_timeline(project_id: str) -> Project:
        return guard_value(lambda: service.normalize_video_project(project_id))

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/split",
        response_model=Project,
    )
    async def split_scene(
        project_id: str, scene_id: str, data: SceneSplitRequest
    ) -> Project:
        return guard_value(
            lambda: service.split_video_scene(project_id, scene_id, at=data.at)
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/merge",
        response_model=Project,
    )
    async def merge_scene(project_id: str, scene_id: str) -> Project:
        return guard_value(lambda: service.merge_video_scene(project_id, scene_id))

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/duplicate",
        response_model=Project,
    )
    async def duplicate_scene(project_id: str, scene_id: str) -> Project:
        return guard_value(lambda: service.duplicate_video_scene(project_id, scene_id))

    @router.delete(
        "/projects/{project_id}/timeline/scenes/{scene_id}", response_model=Project
    )
    async def delete_scene(project_id: str, scene_id: str) -> Project:
        return guard_value(lambda: service.delete_video_scene(project_id, scene_id))

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/move",
        response_model=Project,
    )
    async def move_scene(
        project_id: str, scene_id: str, data: SceneMoveRequest
    ) -> Project:
        return guard_value(
            lambda: service.move_video_scene(project_id, scene_id, data.to_index)
        )

    @router.post("/projects/{project_id}/timeline/scenes/bulk", response_model=Project)
    async def bulk_update_scenes(project_id: str, data: SceneBulkRequest) -> Project:
        return guard_value(
            lambda: service.bulk_update_video_scenes(
                project_id, data.scene_ids, dict(data.patch)
            )
        )

    @router.post("/projects/{project_id}/timeline/markers", response_model=Project)
    async def add_marker(project_id: str, data: MarkerCreate) -> Project:
        return guard_value(
            lambda: service.add_timeline_marker(
                project_id, data.time_seconds, data.label, data.color
            )
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/speed",
        response_model=Project,
    )
    async def set_scene_speed(
        project_id: str, scene_id: str, data: SceneSpeedRequest
    ) -> Project:
        """Retime a scene (0.5x slow-mo .. 2x fast-forward)."""
        return guard_value(
            lambda: service.set_scene_speed(project_id, scene_id, data.speed)
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/reverse",
        response_model=Project,
    )
    async def reverse_scene(
        project_id: str, scene_id: str, data: SceneReverseRequest
    ) -> Project:
        """Play a scene's source media backwards (boomerang)."""
        return guard_value(
            lambda: service.reverse_scene(project_id, scene_id, data.reverse)
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/trim",
        response_model=Project,
    )
    async def trim_scene(
        project_id: str, scene_id: str, data: SceneTrimRequest
    ) -> Project:
        """Set a scene's source in/out handles without moving the timeline."""
        return guard_value(
            lambda: service.trim_scene(
                project_id, scene_id, data.trim_start, data.trim_end
            )
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/audio",
        response_model=Project,
    )
    async def set_scene_audio(
        project_id: str, scene_id: str, data: SceneAudioRequest
    ) -> Project:
        """Adjust a scene's gain and audio fades."""
        return guard_value(
            lambda: service.set_scene_audio(
                project_id, scene_id, data.volume, data.fade_in, data.fade_out
            )
        )

    @router.post(
        "/projects/{project_id}/timeline/scenes/{scene_id}/copy",
        response_model=SceneClipResponse,
    )
    async def copy_scene(project_id: str, scene_id: str) -> SceneClipResponse:
        """Copy a scene to a JSON clipboard the client can paste later."""
        return guard_value(
            lambda: SceneClipResponse(clip=service.copy_scene(project_id, scene_id))
        )

    @router.post("/projects/{project_id}/timeline/scenes/paste", response_model=Project)
    async def paste_scene(project_id: str, data: ScenePasteRequest) -> Project:
        """Paste a scene previously returned by the copy endpoint."""
        return guard_value(
            lambda: service.paste_scene(project_id, data.clip, data.after_scene_id)
        )

    @router.delete(
        "/projects/{project_id}/timeline/markers/{marker_id}", response_model=Project
    )
    async def remove_marker(project_id: str, marker_id: str) -> Project:
        return guard_value(
            lambda: service.remove_timeline_marker(project_id, marker_id)
        )

    @router.post(
        "/projects/{project_id}/video-project/ai-assist", response_model=Project
    )
    async def ai_assist(project_id: str, data: AiAssistRequest) -> Project:
        return guard(
            lambda: service.apply_ai_assist(
                project_id, fit=data.fit, beat=data.beat, bpm=data.bpm
            )
        )

    @router.get("/projects/{project_id}/video-project/scenes/{scene_id}/suggest")
    async def ai_suggest_scene(project_id: str, scene_id: str) -> dict[str, str]:
        try:
            return service.ai_suggest_scene(project_id, scene_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post(
        "/projects/{project_id}/video-project/scenes/{scene_id}/polish",
        response_model=Project,
    )
    async def polish_scene(project_id: str, scene_id: str) -> Project:
        return guard_value(lambda: service.polish_scene_text(project_id, scene_id))

    @router.post("/projects/{project_id}/video/upload", response_model=Project)
    async def upload_video(project_id: str, file: UploadFile = File(...)) -> Project:  # noqa: B008
        get_or_404(service, project_id)
        content = await file.read()
        try:
            return service.upload_video(
                project_id, file.filename or "video.webm", content
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Upload failed: {exc}"
            ) from exc

    @router.get("/projects/{project_id}/video")
    async def get_video(project_id: str, download: bool = False) -> FileResponse:
        get_or_404(service, project_id)
        path = service.video_path(project_id)
        if path is None:
            raise HTTPException(status_code=404, detail="No exported video yet")
        return FileResponse(
            path,
            media_type="video/mp4" if path.suffix == ".mp4" else "video/webm",
            filename=path.name if download else None,
        )

    @router.post("/projects/{project_id}/render", response_model=Project)
    def render_video(project_id: str, data: RenderRequest | None = None) -> Project:
        """Render the current timeline with the local ffmpeg adapter."""
        try:
            request = data or RenderRequest()
            return guard_value(
                lambda: service.render_video(
                    project_id, request.export_format, request.audio_ref
                )
            )
        except RenderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/projects/{project_id}/voiceover/generate", response_model=Project)
    async def generate_voiceover(project_id: str) -> Project:
        return guard(lambda: service.generate_voiceover(project_id))

    @router.get("/projects/{project_id}/voiceover/{scene_id}")
    async def get_voiceover(project_id: str, scene_id: str) -> FileResponse:
        get_or_404(service, project_id)
        path = service.voiceover_path(project_id, scene_id)
        if path is None:
            raise HTTPException(status_code=404, detail="Voiceover clip not found")
        return FileResponse(path, media_type="audio/mpeg")

    @router.post(
        "/projects/{project_id}/timeline/extract",
        response_model=StructuredTimeline,
    )
    def extract_project_timeline(project_id: str) -> StructuredTimeline:
        """Extract a structured event timeline with turning points & casualties."""
        return guard_value(lambda: service.extract_timeline(project_id))

    return router
