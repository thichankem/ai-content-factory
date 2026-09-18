"""Voiceover synthesis: per-scene TTS clips for a project."""

from __future__ import annotations

import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import timeline
from ..models import Project, VoiceoverBundle, VoiceoverTrack, utcnow
from ..tts import resolve_voice
from .errors import (
    StateConflictError,
)
from .timeline import TimelineMixin


class VoiceMixin(TimelineMixin):
    """Voiceover synthesis: per-scene TTS clips for a project."""

    def generate_voiceover(self, project_id: str) -> Project:
        """Kick off narration synthesis for every scene in the background."""
        project = self._assert_tts_available(project_id)
        self._spawn_voiceover(project_id)
        return project

    def _spawn_voiceover(self, project_id: str) -> None:
        self._register_worker(
            threading.Thread(
                target=self._synthesize_voiceover,
                args=(project_id,),
                name=f"voiceover-{project_id}",
                daemon=True,
            )
        )

    def _synthesize_voiceover(self, project_id: str) -> None:
        """Synthesize narration per scene and sync scene durations to the audio."""
        import asyncio

        async def run() -> None:
            try:
                snapshot = self._assert_tts_available(project_id).model_copy(deep=True)
                video_project = self._editable_video_project(snapshot).model_copy(
                    deep=True
                )
                timeline.normalize(video_project)
                audio_dir = Path(self._settings.library_dir) / "audio" / project_id
                audio_dir.mkdir(parents=True, exist_ok=True)
                tracks: list[VoiceoverTrack] = []
                engine_name = self._settings.tts_engine
                with TemporaryDirectory(dir=audio_dir) as staging:
                    for scene in video_project.scenes:
                        text = scene.narration or scene.text or ""
                        if not text.strip():
                            continue
                        data, duration, engine_name = await self._tts.synthesize(
                            text, snapshot.target_language, pitch=scene.pitch
                        )
                        (Path(staging) / f"{scene.id}.mp3").write_bytes(data)
                        scene.duration_seconds = round(max(1.0, duration + 0.35), 1)
                        tracks.append(
                            VoiceoverTrack(
                                scene_id=scene.id,
                                audio_url=f"/projects/{project_id}/voiceover/{scene.id}",
                                duration_seconds=round(duration, 2),
                                text=text,
                            )
                        )
                    project = self._assert_tts_available(project_id).model_copy(
                        deep=True
                    )
                    if (
                        project.video_project != snapshot.video_project
                        or project.target_language != snapshot.target_language
                        or project.voiceover != snapshot.voiceover
                    ):
                        raise StateConflictError(
                            "Timeline or narration changed during synthesis; "
                            "retry voiceover."
                        )
                    self._store_video_project(project, video_project)
                    project.voiceover = VoiceoverBundle(
                        tracks=tracks,
                        engine=engine_name,
                        voice=resolve_voice(project.target_language),
                        generated_at=utcnow(),
                    )
                    destination = audio_dir / project.voiceover.generated_at.strftime(
                        "%Y%m%dT%H%M%S%fZ"
                    )
                    Path(staging).rename(destination)
                    project.error = None
                    self._store.save(project)
            except Exception as exc:
                project = self.get_project(project_id).model_copy(deep=True)
                project.error = f"Voiceover failed: {exc}"
                self._store.save(project)

        asyncio.run(run())

    def _assert_tts_available(self, project_id: str) -> Project:
        """Guard the narration path: enabled engine, and a timeline to voice."""
        project = self.get_project(project_id)
        if not self._settings.tts_enabled or self._settings.tts_engine == "off":
            raise StateConflictError("Text-to-speech is disabled in the configuration.")
        if project.video_project is None:
            raise StateConflictError("No video project to narrate yet.")
        self._assert_video_editable(project)
        return project

    def voiceover_path(self, project_id: str, scene_id: str) -> Path | None:
        """Absolute path of a synthesized narration clip, if it exists."""
        project = self.get_project(project_id)
        bundle = project.voiceover
        if bundle is None or not any(
            track.scene_id == scene_id for track in bundle.tracks
        ):
            return None
        audio_dir = Path(self._settings.library_dir) / "audio" / project_id
        generation = audio_dir / bundle.generated_at.strftime("%Y%m%dT%H%M%S%fZ")
        candidate = (
            generation if generation.is_dir() else audio_dir
        ) / f"{scene_id}.mp3"
        return candidate if candidate.is_file() else None
