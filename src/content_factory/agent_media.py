"""Media, music, image and voice agent tools.

The text-first media surface (read a file, then cut it), the music/audio
editing tools, the image composition tools and the voice chain.  Split out of
``agent_tools.py`` so the registry module holds only the assembly of the
manifest.
"""

from __future__ import annotations

from typing import Any

from .agent_schema import AUDIO_TRACKS, IMAGE_LAYERS, REF, Args, ToolSpec, _p

# ---------------------------------------------------------------------------
# Handlers — reading media without eyes
# ---------------------------------------------------------------------------


def _h_inspect_media(service: Any, args: Args) -> Any:
    return service.inspect_media(args.string("ref"))


def _h_describe_media(service: Any, args: Args) -> Any:
    include = args.strings("include") or None
    return service.describe_media(args.string("ref"), include=include)


def _h_media_loudness(service: Any, args: Args) -> Any:
    return service.media_loudness(
        args.string("ref"), args.number_or("target_lufs", -14.0)
    )


def _h_media_silence(service: Any, args: Args) -> Any:
    return service.media_silence(
        args.string("ref"),
        args.number_or("threshold_db", -32.0),
        args.number_or("min_seconds", 0.35),
    )


def _h_media_scene_cuts(service: Any, args: Args) -> Any:
    return service.media_scene_cuts(
        args.string("ref"), args.number_or("threshold", 30.0)
    )


def _h_media_palette(service: Any, args: Args) -> Any:
    return service.media_palette(args.string("ref"), args.integer("count", 5))


def _h_media_contact_sheet(service: Any, args: Args) -> Any:
    return service.media_contact_sheet(
        args.string("ref"), args.integer("count", 9), args.integer("columns", 3)
    )


def _h_music_beat_grid(service: Any, args: Args) -> Any:
    return service.music_beat_grid(args.string("ref"), args.number("bpm"))


# ---------------------------------------------------------------------------
# Handlers — cutting
# ---------------------------------------------------------------------------


def _h_cut_media(service: Any, args: Args) -> Any:
    return service.cut_media(
        args.string("ref"),
        args.number_or("start_seconds", 0.0),
        args.number_or("end_seconds", 0.0),
        reencode=args.boolean("reencode", False),
    )


def _h_split_media(service: Any, args: Args) -> Any:
    return service.split_media(
        args.string("ref"),
        args.numbers("timestamps"),
        prefix=args.string("prefix", "clip"),
    )


def _h_join_media(service: Any, args: Args) -> Any:
    return service.join_media(
        args.strings("refs"), reencode=args.boolean("reencode", False)
    )


def _h_extract_audio_track(service: Any, args: Args) -> Any:
    return service.extract_audio_track(args.string("ref"), args.string("format", "mp3"))


def _h_extract_frame_image(service: Any, args: Args) -> Any:
    return service.extract_frame_image(
        args.string("ref"),
        args.number_or("at_seconds", 0.0),
        args.string("format", "png"),
    )


# ---------------------------------------------------------------------------
# Handlers — music and audio
# ---------------------------------------------------------------------------


def _h_audio_trim(service: Any, args: Args) -> Any:
    return service.audio_trim(
        args.string("ref"),
        args.number_or("start_seconds", 0.0),
        args.number_or("end_seconds", 0.0),
        args.string("format", "mp3"),
    )


def _h_audio_fade(service: Any, args: Args) -> Any:
    return service.audio_fade(
        args.string("ref"),
        args.number_or("fade_in_seconds", 0.0),
        args.number_or("fade_out_seconds", 0.0),
        args.string("format", "mp3"),
    )


def _h_audio_loop(service: Any, args: Args) -> Any:
    return service.audio_loop(
        args.string("ref"),
        args.number_or("duration_seconds", 15.0),
        args.string("format", "mp3"),
    )


def _h_audio_normalize(service: Any, args: Args) -> Any:
    return service.audio_normalize(
        args.string("ref"),
        args.number_or("target_lufs", -14.0),
        args.string("format", "mp3"),
    )


def _h_audio_retime(service: Any, args: Args) -> Any:
    return service.audio_retime(
        args.string("ref"), args.number_or("factor", 1.0), args.string("format", "mp3")
    )


def _h_audio_mix(service: Any, args: Args) -> Any:
    duration = args.number("duration_seconds")
    return service.audio_mix(
        args.objects("tracks"),
        duration_seconds=duration,
        duck=args.boolean("duck", True),
        duck_db=args.number_or("duck_db", -12.0),
        format=args.string("format", "mp3"),
    )


# ---------------------------------------------------------------------------
# Handlers — image composition and voice
# ---------------------------------------------------------------------------


def _h_image_presets(service: Any, args: Args) -> Any:
    return service.image_presets()


def _h_edit_image(service: Any, args: Args) -> Any:
    return service.edit_image(
        args.base64("image_b64"),
        ops=args.objects("ops"),
        preset=args.optional_string("preset"),
        export_format=args.string("format", "png"),
    )


def _h_compose_images(service: Any, args: Args) -> Any:
    return service.compose_images(
        args.string("base"), args.objects("layers"), args.string("format", "png")
    )


def _h_collage_images(service: Any, args: Args) -> Any:
    captions = args.strings("captions") or None
    return service.collage_images(
        args.strings("refs"),
        columns=args.integer("columns", 2),
        captions=captions,
        format=args.string("format", "png"),
    )


def _h_voice_presets(service: Any, args: Args) -> Any:
    return service.voice_presets()


def _h_enhance_voice(service: Any, args: Args) -> Any:
    return service.process_voice_audio(
        args.base64("audio_b64"),
        params=args.mapping("params") or None,
        preset=args.optional_string("preset"),
        export_format=args.string("format", "mp3"),
    )


def _h_duck_music(service: Any, args: Args) -> Any:
    return service.duck_music_under_voice(
        args.base64("voice_b64"),
        args.base64("music_b64"),
        args.number_or("duck_db", -12.0),
    )


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

MEDIA_SPECS: list[ToolSpec] = [
    ToolSpec(
        "inspect_media",
        "Technical fingerprint of a file: duration, streams, codecs, fps, size.",
        "media",
        "inspect_media",
        _h_inspect_media,
        {"ref": REF},
        ("ref",),
    ),
    ToolSpec(
        "describe_media",
        "Read a file without eyes: loudness, silence, shot changes, palette, "
        "tempo, on-screen text. The starting point for any media decision.",
        "media",
        "describe_media",
        _h_describe_media,
        {
            "ref": REF,
            "include": _p(
                "array",
                "Subset of loudness|silence|cuts|palette|beats|text (default: all).",
                items=_p("string", "Section name."),
            ),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_loudness",
        "EBU R128 integrated loudness, true peak, and gain needed to hit target.",
        "media",
        "media_loudness",
        _h_media_loudness,
        {
            "ref": REF,
            "target_lufs": _p("number", "Delivery target, -14 LUFS by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_silence",
        "Silent gaps with timestamps, so a take can be tightened without listening.",
        "media",
        "media_silence",
        _h_media_silence,
        {
            "ref": REF,
            "threshold_db": _p("number", "Level below which audio counts as silent."),
            "min_seconds": _p("number", "Shortest gap to report."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_scene_cuts",
        "Shot boundaries with timestamps (histogram method, no vision model).",
        "media",
        "media_scene_cuts",
        _h_media_scene_cuts,
        {
            "ref": REF,
            "threshold": _p("number", "Higher means fewer, stronger cuts."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_palette",
        "Dominant colours as hex, so a look can be described and reused.",
        "media",
        "media_palette",
        _h_media_palette,
        {"ref": REF, "count": _p("integer", "How many colours to return.")},
        ("ref",),
    ),
    ToolSpec(
        "media_contact_sheet",
        "One image with evenly spaced frames plus their timestamps.",
        "media",
        "media_contact_sheet",
        _h_media_contact_sheet,
        {
            "ref": REF,
            "count": _p("integer", "How many frames to sample."),
            "columns": _p("integer", "Grid columns."),
        },
        ("ref",),
    ),
    ToolSpec(
        "cut_media",
        "Cut one time range out of any media file into a new asset.",
        "media",
        "cut_media",
        _h_cut_media,
        {
            "ref": REF,
            "start_seconds": _p(
                "number", "Range start; omit to cut from the beginning."
            ),
            "end_seconds": _p("number", "Range end."),
            "reencode": _p("boolean", "Force a frame-accurate re-encode."),
        },
        ("ref", "end_seconds"),
    ),
    ToolSpec(
        "split_media",
        "Cut one file at every timestamp into numbered clips.",
        "media",
        "split_media",
        _h_split_media,
        {
            "ref": REF,
            "timestamps": _p(
                "array", "Cut points in seconds.", items=_p("number", "Seconds.")
            ),
            "prefix": _p("string", "Filename prefix for the clips."),
        },
        ("ref", "timestamps"),
    ),
    ToolSpec(
        "join_media",
        "Join clips in order into one asset.",
        "media",
        "join_media",
        _h_join_media,
        {
            "refs": _p("array", "Assets to join, in order.", items=REF),
            "reencode": _p("boolean", "Re-encode instead of stream copy."),
        },
        ("refs",),
    ),
    ToolSpec(
        "extract_audio_track",
        "Pull the soundtrack out of a video into an audio asset.",
        "media",
        "extract_audio_track",
        _h_extract_audio_track,
        {"ref": REF, "format": _p("string", "mp3 (default) or wav.")},
        ("ref",),
    ),
    ToolSpec(
        "extract_frame_image",
        "Save a single frame as an image asset.",
        "media",
        "extract_frame_image",
        _h_extract_frame_image,
        {
            "ref": REF,
            "at_seconds": _p("number", "Timestamp to grab."),
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("ref",),
    ),
]

AUDIO_SPECS: list[ToolSpec] = [
    ToolSpec(
        "music_beat_grid",
        "Tempo plus beat and downbeat timestamps — the input to cutting on music.",
        "audio",
        "music_beat_grid",
        _h_music_beat_grid,
        {
            "ref": REF,
            "bpm": _p("number", "Override tempo detection."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_trim",
        "Trim an audio asset to a range.",
        "audio",
        "audio_trim",
        _h_audio_trim,
        {
            "ref": REF,
            "start_seconds": _p(
                "number", "Range start; omit to trim from the beginning."
            ),
            "end_seconds": _p("number", "Range end."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "end_seconds"),
    ),
    ToolSpec(
        "audio_fade",
        "Fade an audio asset in, out, or both.",
        "audio",
        "audio_fade",
        _h_audio_fade,
        {
            "ref": REF,
            "fade_in_seconds": _p("number", "Fade-in length."),
            "fade_out_seconds": _p("number", "Fade-out length."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_loop",
        "Loop a music bed until it reaches the requested length.",
        "audio",
        "audio_loop",
        _h_audio_loop,
        {
            "ref": REF,
            "duration_seconds": _p("number", "Target length."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "duration_seconds"),
    ),
    ToolSpec(
        "audio_normalize",
        "Loudness-normalise to a streaming target, reporting before and after.",
        "audio",
        "audio_normalize",
        _h_audio_normalize,
        {
            "ref": REF,
            "target_lufs": _p("number", "Delivery target, -14 LUFS by default."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_retime",
        "Speed a track up or down without changing its pitch.",
        "audio",
        "audio_retime",
        _h_audio_retime,
        {
            "ref": REF,
            "factor": _p("number", "1.0 keeps the tempo; 1.25 is 25% faster."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "factor"),
    ),
    ToolSpec(
        "audio_mix",
        "Mix several tracks (voice plus music bed) with per-track gain, offset, "
        "loop, and automatic ducking of the music under the voice.",
        "audio",
        "audio_mix",
        _h_audio_mix,
        {
            "tracks": AUDIO_TRACKS,
            "duration_seconds": _p("number", "Pad/limit the mix to this length."),
            "duck": _p("boolean", "Duck non-voice tracks under the voice track."),
            "duck_db": _p("number", "Ducking depth in dB."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("tracks",),
    ),
]

IMAGE_SPECS: list[ToolSpec] = [
    ToolSpec(
        "image_presets",
        "List named photo looks (thumbnail, cinematic, noir) and available ops.",
        "image",
        "image_presets",
        _h_image_presets,
    ),
    ToolSpec(
        "edit_image",
        "Edit an image (base64) with an ops pipeline and/or a named preset.",
        "image",
        "edit_image",
        _h_edit_image,
        {
            "image_b64": _p("string", "Base64 of a png/jpeg/webp image."),
            "ops": _p(
                "array",
                "Ops: resize crop rotate flip tone curves color_balance filter "
                "vignette blur sharpen text padding auto_enhance remove_background.",
                items=_p("object", "{name, params}"),
            ),
            "preset": _p("string", "Named look, e.g. thumbnail."),
            "format": _p("string", "png, jpeg or webp."),
        },
        ("image_b64",),
    ),
    ToolSpec(
        "compose_images",
        "Composite images: place layers on a base with position, scale, opacity "
        "and blend mode — the 'ghép ảnh' operator.",
        "image",
        "compose_images",
        _h_compose_images,
        {
            "base": REF,
            "layers": IMAGE_LAYERS,
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("base", "layers"),
    ),
    ToolSpec(
        "collage_images",
        "Grid several images into one sheet, with optional captions per cell.",
        "image",
        "collage_images",
        _h_collage_images,
        {
            "refs": _p("array", "Images to place, in order.", items=REF),
            "columns": _p("integer", "Grid columns."),
            "captions": _p(
                "array", "Caption per cell, same order as refs.", items=_p("string", "")
            ),
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("refs",),
    ),
]

VOICE_SPECS: list[ToolSpec] = [
    ToolSpec(
        "voice_presets",
        "List named voice chains (podcast, voiceover, soft) and their params.",
        "voice",
        "voice_presets",
        _h_voice_presets,
    ),
    ToolSpec(
        "enhance_voice",
        "Enhance raw voice audio (base64) with the Audition-style chain: "
        "highpass, gate, de-ess, 3-band EQ, compressor, loudness, reverb.",
        "voice",
        "process_voice_audio",
        _h_enhance_voice,
        {
            "audio_b64": _p("string", "Base64 of wav/mp3 audio."),
            "params": _p("object", "Chain overrides, e.g. {target_lufs: -16}."),
            "preset": _p("string", "Named chain, e.g. podcast."),
            "format": _p("string", "mp3 or wav."),
        },
        ("audio_b64",),
    ),
    ToolSpec(
        "duck_music",
        "Mix a music bed (base64) under a voice track (base64) with automatic "
        "sidechain ducking.",
        "voice",
        "duck_music_under_voice",
        _h_duck_music,
        {
            "voice_b64": _p("string", "Base64 voice track."),
            "music_b64": _p("string", "Base64 music bed."),
            "duck_db": _p("number", "Ducking depth in dB."),
        },
        ("voice_b64", "music_b64"),
    ),
]
