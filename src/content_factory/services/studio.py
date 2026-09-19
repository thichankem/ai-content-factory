"""The image, voice and audio studio facade.

The HTTP layer and the agent tools speak one method per studio operation
("edit_image", "apply_audio_effect", "separate_audio_stems" ...). Those
methods are deliberately thin: they decide nothing and resolve nothing, they
translate between the wire format and the engine facade in
:mod:`content_factory.image_voice_service`, which is where persistence and
preset handling actually live.

They used to share a module with the ffmpeg renderer, which made a file
called "production" the place to look for a photo operation. The two halves
are now separate: this module is the studio surface, and
:mod:`content_factory.services.production` is the video pipeline that ends in
a rendered file.
"""

from __future__ import annotations

from pathlib import Path

from ..image_voice_service import IMAGE_PRESETS, VOICE_PRESETS_DOC
from .errors import NotFoundError, StateConflictError
from .media_tools import MediaToolsMixin


class StudioMixin(MediaToolsMixin):
    """Image, voice and audio studio operations."""

    # --- Image & voice studio (Photoshop / Audition style) ---------------------

    def edit_image(
        self,
        data: bytes,
        *,
        ops: list[dict] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict:
        """Edit an image with an op pipeline or a named look; persist the result."""
        return self._studio.edit_image_bytes(
            data, ops=ops, preset=preset, export_format=export_format
        )

    # --- image analysis & accessibility --------------------------------------

    def analyze_image(self, data: bytes) -> dict:
        """Describe an image from its pixel statistics (vision-free)."""
        return self._studio.analyze_image_bytes(data)

    def image_op_catalog(self) -> dict:
        """Full op catalogue grouped by category, with plain-language docs."""
        return self._studio.image_op_catalog()

    def describe_image_op(self, name: str, params: dict | None = None) -> dict:
        """Explain a single op in plain language."""
        return self._studio.describe_image_op(name, params)

    def suggest_image_edits(self, data: bytes) -> dict:
        """Histogram-based auto-suggestions for an image."""
        return self._studio.suggest_image_edits(data)

    def batch_edit_image(
        self,
        images: list[bytes],
        *,
        ops: list[dict] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict:
        """Apply the same pipeline to several images (batch / sync settings)."""
        return self._studio.batch_edit_images(
            images, ops=ops, preset=preset, export_format=export_format
        )

    # --- non-destructive edit sessions (undo / redo / history) ---------------

    def begin_image_session(self, data: bytes) -> dict:
        """Start a non-destructive edit session around an image."""
        return self._studio.begin_image_session(data)

    def edit_image_session(
        self, session_id: str, ops: list[dict], *, export_format: str = "png"
    ) -> dict:
        """Apply a step to a session and record it in the undo stack."""
        return self._studio.edit_image_session(
            session_id, ops, export_format=export_format
        )

    def undo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict:
        """Undo the last edit step."""
        return self._studio.undo_image_session(session_id, export_format=export_format)

    def redo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict:
        """Redo the last undone edit step."""
        return self._studio.redo_image_session(session_id, export_format=export_format)

    def image_session_state(self, session_id: str) -> dict:
        """Current state of a session (version, undo/redo availability)."""
        return self._studio.image_session_state(session_id)

    # --- video & audio effects + accessibility -------------------------------

    def video_effect_catalog(self) -> dict:
        """Every video frame effect with a plain-language description."""
        from .. import video_effects

        return video_effects.effect_catalog()

    def apply_video_effect(
        self,
        data: bytes,
        name: str,
        params: dict | None = None,
        *,
        export_format: str = "png",
    ) -> dict:
        """Apply a frame effect to an image (or a video frame) and persist it."""
        import numpy as np
        from PIL import Image as PILImage

        from .. import image_engine, video_effects

        img = image_engine.load_image(data)
        frame = np.asarray(img.convert("RGB"))
        result = video_effects.apply_frame_effect(frame, name, params)
        out = PILImage.fromarray(result)
        blob = image_engine.export_bytes(out, export_format)
        report = self._studio.persist_image_bytes(blob, export_format)
        return {**report, "effect": name, "params": params or {}}

    def audio_effect_catalog(self) -> dict:
        """Every audio effect with a plain-language description."""
        from .. import audio_effects

        return audio_effects.audio_effect_catalog()

    def apply_audio_effect(
        self,
        data: bytes,
        name: str,
        params: dict | None = None,
        *,
        export_format: str = "mp3",
    ) -> dict:
        """Apply a DSP effect to audio bytes and persist the result."""
        from .. import audio_effects, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        processed = audio_effects.apply_audio_effect(samples, sr, name, params)
        blob = voice_engine.encode_pcm(processed, sr, export_format)
        return self._studio.persist_audio_bytes(blob, export_format)

    # --- audio analysis, SFX & accessibility ---------------------------------

    def analyze_audio(self, data: bytes) -> dict:
        """Measure an audio clip: waveform, spectrogram, frequency, meters."""
        import numpy as np

        from .. import audio_analysis, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        return audio_analysis.analyze_samples(np.asarray(samples, dtype=np.float32), sr)

    def sfx_catalog(self) -> dict:
        """Every synthesised sound effect with a plain-language description."""
        from .. import sfx

        return sfx.sfx_catalog()

    def synthesize_sfx(
        self, name: str, params: dict | None = None, *, export_format: str = "wav"
    ) -> dict:
        """Generate a sound effect from scratch and persist it."""
        from .. import sfx, voice_engine

        samples = sfx.synthesize_sfx(name, 44100, params)
        blob = voice_engine.encode_pcm(samples, 44100, export_format)
        return self._studio.persist_audio_bytes(blob, export_format)

    def audio_operation_catalog(self) -> dict:
        """Every audio operation grouped by category, with descriptions."""
        from .. import audio_assist

        return audio_assist.catalog()

    def describe_audio_operation(self, name: str) -> dict:
        """Explain one audio operation in plain language."""
        from .. import audio_assist

        return audio_assist.describe_operation(name)

    def describe_audio(self, data: bytes) -> dict:
        """Describe an audio clip in plain language from its measurements."""
        import numpy as np

        from .. import audio_assist, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        return audio_assist.describe_audio(np.asarray(samples, dtype=np.float32), sr)

    def suggest_audio_mastering(self, data: bytes) -> dict:
        """Auto-suggest a mastering chain from the audio measurements."""
        import numpy as np

        from .. import audio_assist, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        return audio_assist.suggest_mastering_chain(
            np.asarray(samples, dtype=np.float32), sr
        )

    def apply_audio_mastering(self, data: bytes, *, export_format: str = "wav") -> dict:
        """Run the auto-suggested mastering chain and persist the mastered audio."""
        import numpy as np

        from .. import audio_assist, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        mastered, report = audio_assist.execute_mastering_chain(
            np.asarray(samples, dtype=np.float32), sr
        )
        blob = voice_engine.encode_pcm(mastered, sr, export_format)
        asset = self._studio.persist_audio_bytes(blob, export_format)
        return {"asset": asset, "report": report}

    def ai_audio_catalog(self) -> dict:
        """Every AI audio capability with a plain-language description."""
        from .. import ai_audio

        return ai_audio.ai_audio_catalog()

    def dub_audio(self, data: bytes, target_text: str, lang: str = "en") -> dict:
        """Dub a clip via a registered ML adapter (raises if none configured)."""
        from .. import ai_audio

        return ai_audio.dub_audio(data, target_text, lang)

    def voice_clone(self, data: bytes, ref_voice: bytes) -> dict:
        """Clone a voice via a registered ML adapter (raises if none configured)."""
        from .. import ai_audio

        return ai_audio.voice_clone(data, ref_voice)

    def stem_catalog(self) -> dict:
        """Every available audio stem with a plain-language description."""
        from .. import audio_separation

        return audio_separation.stem_catalog()

    def separate_audio_stems(
        self,
        data: bytes,
        num: int = 2,
        *,
        export_format: str = "wav",
    ) -> dict:
        """Separate a mono clip into stems (voice/instrumental or low/mid/high)."""
        import numpy as np

        from .. import audio_separation, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        stems = audio_separation.separate_stems(
            np.asarray(samples, dtype=np.float32), sr, num=int(num)
        )
        out = {}
        for name, stem in stems.items():
            blob = voice_engine.encode_pcm(stem, sr, export_format)
            out[name] = self._studio.persist_audio_bytes(blob, export_format)
        return {"stems": out, "count": len(out)}

    def video_operation_catalog(self) -> dict:
        """Every video/audio operation grouped by category, with descriptions."""
        from .. import video_assist

        return video_assist.catalog()

    def describe_video_operation(self, name: str) -> dict:
        """Explain one video/audio operation in plain language."""
        from .. import video_assist

        return video_assist.describe_operation(name)

    def describe_video_timeline(self, project_id: str) -> dict:
        """Summarise a project's timeline in natural language."""
        from .. import video_assist

        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        return video_assist.describe_timeline(project.video_project)

    def suggest_video_edits(self, project_id: str) -> dict:
        """Turn the timeline report into concrete edit suggestions."""
        from .. import video_assist

        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        return video_assist.suggest_edits(project.video_project)

    def image_presets(self) -> list[str]:
        """Named one-click photo looks."""
        return sorted(IMAGE_PRESETS)

    def voice_presets(self) -> list[str]:
        """Named Audition-style voice chains."""
        return list(VOICE_PRESETS_DOC)

    def process_voice_audio(
        self,
        data: bytes,
        *,
        params: dict | None = None,
        preset: str | None = None,
        export_format: str = "mp3",
    ) -> dict:
        """Enhance raw voice audio through the Audition-style chain."""
        return self._studio.process_voice_bytes(
            data, params=params, preset=preset, export_format=export_format
        )

    def duck_music_under_voice(
        self, voice: bytes, music: bytes, duck_db: float = -12.0
    ) -> dict:
        """Mix a music bed that automatically ducks under the voice."""
        return self._studio.duck_music_bytes(voice, music, duck_db=duck_db)

    def edited_asset_path(self, name: str) -> Path:
        """Absolute path of a persisted edited asset (image or audio)."""
        try:
            return self._studio.asset_path(name)
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
