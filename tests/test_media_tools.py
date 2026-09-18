"""Tests for the media tool engine and its agent-facing tools.

Fixtures are generated with ffmpeg's synthetic sources, so the suite needs no
network and no sample files. Everything here is the contract a text-only agent
relies on: read the file as text, then cut, mix and compose from that text.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from content_factory import media_tools
from content_factory.agent_tools import (
    TOOL_MANIFEST,
    TOOL_REGISTRY,
    Args,
    ToolError,
    build_tool_manifest,
    dispatch_tool,
)
from content_factory.config import Settings

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

pytestmark = pytest.mark.skipif(
    FFMPEG is None or FFPROBE is None, reason="ffmpeg/ffprobe required"
)


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory) -> dict[str, object]:
    """A short synthetic video, a music bed and two stills."""
    work = tmp_path_factory.mktemp("media")
    video = work / "clip.mp4"
    _run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=15:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(video),
        ]
    )
    music = work / "music.wav"
    _run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:duration=4",
            "-c:a",
            "pcm_s16le",
            str(music),
        ]
    )
    voice = work / "voice.wav"
    _run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=180:duration=3",
            "-c:a",
            "pcm_s16le",
            str(voice),
        ]
    )
    first = work / "first.png"
    second = work / "second.png"
    for path, colour, size in (
        (first, "navy", "240x160"),
        (second, "orange", "120x120"),
    ):
        _run(
            [
                FFMPEG,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c={colour}:size={size}:duration=1",
                "-frames:v",
                "1",
                str(path),
            ]
        )
    return {
        "video": video,
        "music": music,
        "voice": voice,
        "first": first,
        "second": second,
        "dir": work,
    }


@pytest.fixture
def service(tmp_path, monkeypatch):
    """A service whose media library and edited assets live in tmp_path."""
    library = tmp_path / "library"
    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
        media_dir=str(library / "media"),
        library_dir=str(library),
        cache_dir=str(tmp_path / "cache"),
    )
    from content_factory.service import ContentFactoryService

    return ContentFactoryService(settings)


@pytest.fixture
def refs(service, media) -> dict[str, str]:
    """Media-library ids for each fixture file."""
    ids = {}
    for key in ("video", "music", "voice", "first", "second"):
        path = media[key]
        ids[key] = service.media_upload(path.name, path.read_bytes()).id  # type: ignore[union-attr]
    return ids


# --- Engine ------------------------------------------------------------------


def test_probe_reports_streams_and_duration(media) -> None:
    info = media_tools.probe(media["video"])
    assert info["has_video"] and info["has_audio"]
    assert info["duration_seconds"] == pytest.approx(2.0, abs=0.4)
    assert (info["width"], info["height"]) == (320, 180)


def test_loudness_reports_integrated_level(media) -> None:
    report = media_tools.loudness(media["music"])
    assert report["integrated_lufs"] is not None
    assert report["gain_to_target_db"] is not None


def test_palette_reads_a_still(media) -> None:
    colours = media_tools.palette(media["first"], count=3)
    assert colours and all(colour.startswith("#") for colour in colours)


def test_beat_grid_returns_beats_and_downbeats(media) -> None:
    grid = media_tools.beat_grid(media["music"])
    assert grid["bpm"] > 0
    assert len(grid["beats"]) > 2
    assert len(grid["downbeats"]) >= 1


def test_describe_is_json_safe_and_covers_the_essentials(media) -> None:
    report = media_tools.describe(media["video"])
    assert {"probe", "loudness", "silence", "scene_cuts", "music"} <= set(report)
    assert isinstance(json.dumps(report), str)


def test_cut_split_and_concat(media) -> None:
    clip = media_tools.cut(media["video"], 0.2, 1.2, media["dir"] / "cut.mp4")
    assert clip["duration_seconds"] == pytest.approx(1.0, abs=0.4)

    parts = media_tools.split_at(
        media["video"], [0.5, 1.5], media["dir"] / "parts", prefix="p"
    )
    assert [p["index"] for p in parts] == [1, 2, 3]

    joined = media_tools.concat(
        [clip["destination"], parts[0]["destination"]], media["dir"] / "join.mp4"
    )
    assert joined["count"] == 2
    assert joined["duration_seconds"] > clip["duration_seconds"]


def test_extract_audio_and_frame(media) -> None:
    audio = media_tools.extract_audio(media["video"], media["dir"] / "audio.mp3")
    assert audio["duration_seconds"] == pytest.approx(2.0, abs=0.4)
    frame = media_tools.extract_frame(media["video"], 1.0, media["dir"] / "frame.png")
    assert frame["size_bytes"] > 0


def test_audio_fade_loop_and_normalise(media) -> None:
    faded = media_tools.fade_audio(
        media["music"],
        media["dir"] / "fade.mp3",
        fade_in_seconds=0.5,
        fade_out_seconds=1.0,
    )
    assert faded["duration_seconds"] == pytest.approx(4.0, abs=0.4)

    looped = media_tools.loop_audio(media["music"], media["dir"] / "loop.mp3", 7.0)
    assert looped["duration_seconds"] == pytest.approx(7.0, abs=0.4)

    normalised = media_tools.normalize_loudness(
        media["music"], media["dir"] / "normal.mp3", target_lufs=-14.0
    )
    assert normalised["after_lufs"] is not None
    assert normalised["after_lufs"] > normalised["before_lufs"]


def test_mix_tracks_ducks_music_under_voice(media) -> None:
    report = media_tools.mix_tracks(
        [
            {"path": str(media["voice"]), "role": "voice"},
            {"path": str(media["music"]), "role": "music", "loop": True},
        ],
        media["dir"] / "mix.mp3",
        duration_seconds=5.0,
    )
    assert report["ducked"] is True
    assert report["duration_seconds"] == pytest.approx(5.0, abs=0.4)
    assert report["loudness"] is not None


def test_compose_layers_and_collage(media) -> None:
    composed = media_tools.compose_layers(
        media["first"],
        [
            {
                "path": str(media["second"]),
                "x": "bottom-right",
                "y": "bottom-right",
                "scale": 0.5,
            },
            {"path": str(media["second"]), "x": 10, "y": 10, "blend": "screen"},
        ],
        media["dir"] / "composed.png",
    )
    assert composed["layer_count"] == 2
    assert (composed["width"], composed["height"]) == (240, 160)

    sheet = media_tools.collage(
        [media["first"], media["second"], media["first"]],
        media["dir"] / "collage.png",
        columns=2,
        captions=["one", "two", "three"],
    )
    assert sheet["rows"] == 2
    assert len(sheet["cells"]) == 3
    assert sheet["cells"][0]["caption"] == "one"


def test_unknown_blend_mode_is_rejected(media) -> None:
    with pytest.raises(media_tools.MediaToolError):
        media_tools.compose_layers(
            media["first"],
            [{"path": str(media["second"]), "blend": "nonsense"}],
            media["dir"] / "bad.png",
        )


# --- Service + tool surface --------------------------------------------------


def test_describe_media_tool_returns_a_reading(service, refs) -> None:
    report = dispatch_tool(service, "describe_media", {"ref": refs["video"]})
    assert report["probe"]["has_audio"] is True
    assert "music" in report


def test_cut_media_tool_chains_by_asset_id(service, refs) -> None:
    clip = dispatch_tool(
        service,
        "cut_media",
        {"ref": refs["video"], "start_seconds": 0.2, "end_seconds": 1.2},
    )
    assert clip["asset_id"]
    assert clip["duration_seconds"] == pytest.approx(1.0, abs=0.4)

    followed = dispatch_tool(service, "inspect_media", {"ref": clip["asset_id"]})
    assert followed["has_video"] is True


def test_split_and_join_media_tools(service, refs) -> None:
    clips = dispatch_tool(
        service,
        "split_media",
        {"ref": refs["video"], "timestamps": [0.6, 1.2]},
    )
    assert len(clips) == 3
    joined = dispatch_tool(
        service, "join_media", {"refs": [clips[0]["asset_id"], clips[1]["asset_id"]]}
    )
    assert joined["clipped"] == 2
    assert joined["duration_seconds"] > 0


def test_audio_mix_tool_ducks_the_bed(service, refs) -> None:
    mixed = dispatch_tool(
        service,
        "audio_mix",
        {
            "tracks": [
                {"ref": refs["voice"], "role": "voice"},
                {"ref": refs["music"], "role": "music", "loop": True, "gain_db": -6},
            ],
            "duration_seconds": 4.0,
        },
    )
    assert mixed["ducked"] is True
    assert mixed["asset_id"]


def test_compose_and_collage_tools(service, refs) -> None:
    composed = dispatch_tool(
        service,
        "compose_images",
        {
            "base": refs["first"],
            "layers": [
                {"ref": refs["second"], "x": "center", "y": "center", "scale": 0.5}
            ],
        },
    )
    assert composed["layer_count"] == 1
    assert composed["width"] == 240

    sheet = dispatch_tool(
        service,
        "collage_images",
        {"refs": [refs["first"], refs["second"]], "columns": 2, "captions": ["a", "b"]},
    )
    assert sheet["rows"] == 1


def test_contact_sheet_and_beat_grid_tools(service, refs) -> None:
    sheet = dispatch_tool(
        service, "media_contact_sheet", {"ref": refs["video"], "count": 4, "columns": 2}
    )
    assert len(sheet["timestamps"]) == 4
    grid = dispatch_tool(service, "music_beat_grid", {"ref": refs["music"]})
    assert grid["bpm"] > 0 and grid["beats"]


def test_resolving_a_missing_reference_names_the_reference(service) -> None:
    with pytest.raises(Exception) as excinfo:
        dispatch_tool(service, "inspect_media", {"ref": "nope-not-here"})
    assert "nope-not-here" in str(excinfo.value)


# --- Manifest -----------------------------------------------------------------


def test_every_tool_publishes_a_valid_input_schema() -> None:
    for spec in TOOL_REGISTRY.values():
        schema = spec.input_schema
        assert schema["type"] == "object"
        assert set(schema.get("required", [])) <= set(schema["properties"])
        for name, prop in schema["properties"].items():
            assert prop["type"], f"{spec.name}.{name} has no type"
            assert prop["description"], f"{spec.name}.{name} has no description"
    assert len(TOOL_REGISTRY) >= 55


def test_manifest_entries_expose_schema_and_args() -> None:
    manifest = build_tool_manifest()
    assert manifest["count"] == len(TOOL_MANIFEST)
    assert {"media", "audio"} <= set(manifest["categories"])
    entry = next(t for t in manifest["tools"] if t["name"] == "describe_media")
    assert entry["input_schema"]["required"] == ["ref"]
    assert "ref" in entry["args"]


def test_required_arguments_are_enforced_per_tool() -> None:
    for spec in TOOL_REGISTRY.values():
        for name in spec.required:
            assert name in spec.properties, (
                f"{spec.name} requires undocumented '{name}'"
            )


def test_dispatch_reports_unknown_tools() -> None:
    class Dummy:
        pass

    with pytest.raises(ToolError, match="Unknown tool"):
        dispatch_tool(Dummy(), "not_a_tool", {})


def test_argument_validation_names_the_offending_field() -> None:
    with pytest.raises(ToolError, match="start_seconds"):
        Args({"start_seconds": "soon"}).number("start_seconds")
    with pytest.raises(ToolError, match="Missing required argument 'ref'"):
        Args({}).requires("ref")
    with pytest.raises(ToolError, match="tracks"):
        Args({"tracks": "nope"}).objects("tracks")
    with pytest.raises(ToolError, match="stage"):
        Args({"stage": "nonsense"}).choice("stage", ("script", "video"), "script")
    with pytest.raises(ToolError, match="scene_id"):
        Args({"scene_id": "with spaces!"}).ident("scene_id")
