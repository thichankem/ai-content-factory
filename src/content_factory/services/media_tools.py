"""Media tools: read, cut, compose and mix any asset an agent can name.

These are the operations that let a *text-only* agent work like an editor: it
reads a file as structured text (``describe_media``), decides what to do, and
hands the decision back as a cut, a mix or a composite. Every method resolves
its input by media-library id, edited-asset id, or a sandboxed path, and every
output is persisted under ``library/edited/`` so the next call can reference it
by ``asset_id`` alone.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from .. import media_tools as engine
from ..sandbox import Sandbox, SandboxError
from .errors import NotFoundError
from .media import MediaMixin

__all__ = ["MediaToolsMixin"]


class MediaToolsMixin(MediaMixin):
    """Agent-facing media operations on top of the universal media library."""

    # --- resolution and persistence -------------------------------------------

    @property
    def _edited_dir(self) -> Path:
        """Where edited assets are written (shared with the image/voice studio)."""
        directory = Path(self._settings.library_dir) / "edited"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def _asset_sandbox(self) -> Sandbox:
        """Roots an agent-named path is allowed to live in."""
        settings = self._settings
        return Sandbox(
            [
                settings.media_dir,
                settings.uploads_dir,
                settings.cache_dir,
                settings.library_dir,
            ]
        )

    def resolve_media_ref(self, ref: str) -> Path:
        """Resolve a media id, an edited asset id, or a sandboxed file path.

        Accepts the bare ``asset_id`` this module returns, the ``/edited/name``
        URL it reports, a media-library id, or a path inside the media roots —
        so an agent can chain calls with whichever identifier it still holds.
        """
        item = self._media.get(ref)
        if item is not None:
            path = self._media.path_for(item)
            if path is None:
                raise NotFoundError(f"Media '{ref}' has no file on disk.")
            return path
        name = ref.rsplit("/", 1)[-1]
        edited_dir = self._edited_dir
        if name != ref or "." in name:
            candidate = edited_dir / name
            if candidate.is_file():
                return candidate
        matches = sorted(edited_dir.glob(f"{name}.*"))
        if matches:
            return matches[0]
        try:
            resolved = self._asset_sandbox.resolve(ref)
        except (SandboxError, ValueError) as exc:
            raise NotFoundError(
                f"Nothing named '{ref}' in the media library or edited assets."
            ) from exc
        del edited_dir
        if not resolved.is_file():
            raise NotFoundError(f"Nothing named '{ref}' in the allowed media roots.")
        return resolved

    def _new_asset(self, suffix: str) -> tuple[str, Path]:
        """Reserve a name in the edited-assets directory."""
        asset_id = uuid.uuid4().hex[:12]
        return asset_id, self._edited_dir / f"{asset_id}.{suffix.lstrip('.')}"

    def _asset_report(self, asset_id: str, path: Path, **extra: Any) -> dict[str, Any]:
        """JSON-safe description of a persisted asset, referenceable by id."""
        return {
            "asset_id": asset_id,
            "url": f"/edited/{path.name}",
            "path": str(path),
            "duration_seconds": engine.probe(path)["duration_seconds"],
            "size_bytes": path.stat().st_size,
            **extra,
        }

    # --- reading --------------------------------------------------------------

    def inspect_media(self, ref: str) -> dict[str, Any]:
        """Technical fingerprint: duration, streams, codecs, fps, size."""
        return engine.probe(self.resolve_media_ref(ref))

    def describe_media(
        self, ref: str, include: list[str] | None = None
    ) -> dict[str, Any]:
        """The 'read without eyes' call: one text report per media file.

        Includes loudness, silence, shot changes, colour palette, tempo and any
        on-screen text when the optional OCR tool is installed.
        """
        return engine.describe(self.resolve_media_ref(ref), include=include)

    def media_loudness(self, ref: str, target_lufs: float = -14.0) -> dict[str, Any]:
        """EBU R128 integrated loudness, true peak and gain to a target."""
        return engine.loudness(self.resolve_media_ref(ref), target_lufs=target_lufs)

    def media_silence(
        self, ref: str, threshold_db: float = -32.0, min_seconds: float = 0.35
    ) -> list[dict[str, float]]:
        """Silent gaps, so an agent can tighten a take without listening."""
        return engine.silence_ranges(
            self.resolve_media_ref(ref),
            threshold_db=threshold_db,
            min_seconds=min_seconds,
        )

    def media_scene_cuts(
        self, ref: str, threshold: float = 30.0
    ) -> list[dict[str, Any]]:
        """Shot boundaries with timestamps (histogram method, no model)."""
        return engine.scene_cuts(self.resolve_media_ref(ref), threshold=threshold)

    def media_palette(self, ref: str, count: int = 5) -> list[str]:
        """Dominant colours as hex, so 'the look' is something an agent can cite."""
        return engine.palette(self.resolve_media_ref(ref), count=count)

    def music_beat_grid(self, ref: str, bpm: float | None = None) -> dict[str, Any]:
        """Tempo and beat timestamps, the input to cutting on the music."""
        return engine.beat_grid(self.resolve_media_ref(ref), bpm=bpm)

    # --- cutting --------------------------------------------------------------

    def cut_media(
        self,
        ref: str,
        start_seconds: float,
        end_seconds: float,
        *,
        reencode: bool = False,
    ) -> dict[str, Any]:
        """Cut one range out of a media file into a new, referenceable asset."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(source.suffix or ".mp4")
        report = engine.cut(
            source, start_seconds, end_seconds, target, copy=not reencode
        )
        return self._asset_report(
            asset_id,
            target,
            source=ref,
            start_seconds=report["start_seconds"],
            end_seconds=report["end_seconds"],
            duration_seconds=report["duration_seconds"],
        )

    def split_media(
        self, ref: str, timestamps: list[float], prefix: str = "clip"
    ) -> list[dict[str, Any]]:
        """Cut one file at every timestamp into numbered clips."""
        source = self.resolve_media_ref(ref)
        stamp = uuid.uuid4().hex[:8]
        workdir = self._edited_dir / f"split-{stamp}"
        clips = engine.split_at(source, timestamps, workdir, prefix=prefix)
        reports: list[dict[str, Any]] = []
        for clip in clips:
            asset_id, target = self._new_asset(source.suffix or ".mp4")
            shutil.move(clip["destination"], target)
            reports.append(
                self._asset_report(
                    asset_id,
                    target,
                    index=clip["index"],
                    start_seconds=clip["start_seconds"],
                    end_seconds=clip["end_seconds"],
                )
            )
        shutil.rmtree(workdir, ignore_errors=True)
        return reports

    def join_media(self, refs: list[str], *, reencode: bool = False) -> dict[str, Any]:
        """Join clips in order into one asset."""
        sources = [self.resolve_media_ref(ref) for ref in refs]
        asset_id, target = self._new_asset(sources[0].suffix if sources else ".mp4")
        report = engine.concat(sources, target, copy=not reencode)
        return self._asset_report(
            asset_id,
            target,
            clipped=report["count"],
            sources=list(refs),
        )

    def extract_audio_track(self, ref: str, format: str = "mp3") -> dict[str, Any]:
        """Pull the soundtrack out of a video into an audio asset."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        report = engine.extract_audio(source, target)
        return self._asset_report(
            asset_id,
            target,
            source=ref,
            sample_rate=report["sample_rate"],
            channels=report["channels"],
        )

    def extract_frame_image(
        self, ref: str, at_seconds: float = 0.0, format: str = "png"
    ) -> dict[str, Any]:
        """Save a single frame as an image asset."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        engine.extract_frame(source, at_seconds, target)
        return self._asset_report(asset_id, target, source=ref, at_seconds=at_seconds)

    def media_contact_sheet(
        self, ref: str, count: int = 9, columns: int = 3
    ) -> dict[str, Any]:
        """One image with ``count`` evenly spaced frames, plus their timestamps."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset("png")
        report = engine.contact_sheet(source, target, count=count, columns=columns)
        return self._asset_report(
            asset_id,
            target,
            source=ref,
            timestamps=report["timestamps"],
            columns=report["columns"],
        )

    # --- music and audio -------------------------------------------------------

    def audio_trim(
        self, ref: str, start_seconds: float, end_seconds: float, format: str = "mp3"
    ) -> dict[str, Any]:
        """Trim an audio asset to a range."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        engine.trim_audio(source, start_seconds, end_seconds, target)
        return self._asset_report(asset_id, target, source=ref, operation="trim")

    def audio_fade(
        self,
        ref: str,
        fade_in_seconds: float = 0.0,
        fade_out_seconds: float = 0.0,
        format: str = "mp3",
    ) -> dict[str, Any]:
        """Fade an audio asset in, out, or both."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        engine.fade_audio(
            source,
            target,
            fade_in_seconds=fade_in_seconds,
            fade_out_seconds=fade_out_seconds,
        )
        return self._asset_report(
            asset_id,
            target,
            source=ref,
            fade_in_seconds=fade_in_seconds,
            fade_out_seconds=fade_out_seconds,
        )

    def audio_loop(
        self, ref: str, duration_seconds: float, format: str = "mp3"
    ) -> dict[str, Any]:
        """Loop a music bed until it reaches the requested length."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        engine.loop_audio(source, target, duration_seconds)
        return self._asset_report(asset_id, target, source=ref, operation="loop")

    def audio_normalize(
        self, ref: str, target_lufs: float = -14.0, format: str = "mp3"
    ) -> dict[str, Any]:
        """Loudness-normalise to a streaming target, reporting before/after."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        report = engine.normalize_loudness(source, target, target_lufs=target_lufs)
        return self._asset_report(
            asset_id,
            target,
            source=ref,
            before_lufs=report["before_lufs"],
            after_lufs=report["after_lufs"],
        )

    def audio_retime(
        self, ref: str, factor: float, format: str = "mp3"
    ) -> dict[str, Any]:
        """Speed a track up or down without changing its pitch."""
        source = self.resolve_media_ref(ref)
        asset_id, target = self._new_asset(format)
        report = engine.tempo_shift(source, target, factor)
        return self._asset_report(asset_id, target, source=ref, factor=report["factor"])

    def audio_mix(
        self,
        tracks: list[dict[str, Any]],
        *,
        duration_seconds: float | None = None,
        duck: bool = True,
        duck_db: float = -12.0,
        format: str = "mp3",
    ) -> dict[str, Any]:
        """Mix any number of audio tracks (voice + music bed) into one asset.

        Each track is ``{ref, gain_db, offset_seconds, loop, role}`` where
        ``role`` may be ``voice`` — that track then drives a sidechain
        compressor that ducks the music under it.
        """
        resolved: list[dict[str, Any]] = []
        for track in tracks:
            entry = dict(track)
            entry["path"] = str(self.resolve_media_ref(str(track["ref"])))
            entry.pop("ref", None)
            resolved.append(entry)
        asset_id, target = self._new_asset(format)
        report = engine.mix_tracks(
            resolved,
            target,
            duration_seconds=duration_seconds,
            duck=duck,
            duck_db=duck_db,
        )
        return self._asset_report(
            asset_id,
            target,
            tracks=report["tracks"],
            ducked=report["ducked"],
            loudness_lufs=report["loudness"],
        )

    # --- image composition -----------------------------------------------------

    def compose_images(
        self,
        base: str,
        layers: list[dict[str, Any]],
        format: str = "png",
    ) -> dict[str, Any]:
        """Stack images: the "ghép ảnh" operator (position, scale, blend)."""
        base_path = self.resolve_media_ref(base)
        resolved: list[dict[str, Any]] = []
        for layer in layers:
            entry = dict(layer)
            entry["path"] = str(self.resolve_media_ref(str(layer["ref"])))
            entry.pop("ref", None)
            resolved.append(entry)
        asset_id, target = self._new_asset(format)
        report = engine.compose_layers(base_path, resolved, target)
        return self._asset_report(
            asset_id,
            target,
            base=base,
            width=report["width"],
            height=report["height"],
            layer_count=report["layer_count"],
            layers=report["layers"],
        )

    def collage_images(
        self,
        refs: list[str],
        columns: int = 2,
        captions: list[str] | None = None,
        format: str = "png",
    ) -> dict[str, Any]:
        """Grid several images into one sheet with optional captions."""
        paths = [str(self.resolve_media_ref(ref)) for ref in refs]
        asset_id, target = self._new_asset(format)
        report = engine.collage(paths, target, columns=columns, captions=captions)
        return self._asset_report(
            asset_id,
            target,
            collage_count=report["count"],
            columns=report["columns"],
            rows=report["rows"],
            width=report["width"],
            height=report["height"],
        )
