"""Exercise every media tool against real, ffmpeg-generated media."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from content_factory import media_tools as mt  # noqa: E402

WORK = Path(tempfile.mkdtemp(prefix="media-tools-"))
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{f' — {detail}' if detail else ''}")


def make_video(path: Path, seconds: float = 6.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=25:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
        ],
        check=True, capture_output=True,
    )


def make_audio(path: Path, seconds: float, freq: int = 220) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}",
            "-c:a", "pcm_s16le", str(path),
        ],
        check=True, capture_output=True,
    )


def make_image(path: Path, color: str, size: str = "400x300") -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:size={size}:duration=1",
            "-frames:v", "1", str(path),
        ],
        check=True, capture_output=True,
    )


print("generating fixtures ...")
video = WORK / "clip.mp4"
make_video(video)
music = WORK / "music.wav"
make_audio(music, 8.0, 330)
voice = WORK / "voice.wav"
make_audio(voice, 5.0, 180)
photo_a = WORK / "a.png"
photo_b = WORK / "b.png"
make_image(photo_a, "navy")
make_image(photo_b, "orange", "200x200")

print("\nreading")
info = mt.probe(video)
check("probe duration", abs((info["duration_seconds"] or 0) - 6.0) < 0.6, f"{info['duration_seconds']}s")
check("probe streams", info["has_video"] and info["has_audio"], f"{info['width']}x{info['height']}@{info['fps']}")

loud = mt.loudness(video)
check("loudness lufs", loud["integrated_lufs"] is not None, f"{loud['integrated_lufs']} LUFS peak {loud['true_peak_db']} dB")

silence = mt.silence_ranges(video, threshold_db=-40)
check("silence detection runs", isinstance(silence, list), f"{len(silence)} gap(s)")

cuts = mt.scene_cuts(video)
check("scene cuts runs", isinstance(cuts, list), f"{len(cuts)} scene(s)")

colors = mt.palette(photo_a, count=3)
check("palette", len(colors) > 0 and all(c.startswith("#") for c in colors), str(colors))

grid = mt.beat_grid(music)
check("beat grid", grid["bpm"] > 0 and len(grid["beats"]) > 3, f"{grid['bpm']}bpm, {len(grid['beats'])} beats, downbeats={len(grid['downbeats'])}")

report = mt.describe(video)
sections = [k for k in ("probe", "loudness", "silence", "scene_cuts", "palette", "music", "text") if k in report]
check("describe sections", len(sections) >= 5, ",".join(sections))
check("describe is json-safe", isinstance(json.dumps(report), str), f"{len(json.dumps(report))} bytes")

sheet = mt.contact_sheet(video, WORK / "sheet.png", count=4, columns=2)
check("contact sheet", sheet["destination"] and Path(sheet["destination"]).is_file(), f"{sheet['timestamps']}")

print("\ncutting")
clip = mt.cut(video, 1.0, 3.0, WORK / "cut.mp4")
check("cut", abs((clip["duration_seconds"] or 0) - 2.0) < 0.5, f"{clip['duration_seconds']}s via copy")

clips = mt.split_at(video, [1.5, 3.5], WORK / "parts", prefix="p")
check("split_at", len(clips) == 3, f"{[round(c['duration_seconds'] or 0, 2) for c in clips]}")

joined = mt.concat([clip["destination"], clips[0]["destination"]], WORK / "joined.mp4", copy=True)
check("concat", (joined["duration_seconds"] or 0) > 2.0, f"{joined['duration_seconds']}s from {joined['count']} clips")

extracted = mt.extract_audio(video, WORK / "extracted.mp3")
check("extract_audio", (extracted["duration_seconds"] or 0) > 5.0, f"{extracted['duration_seconds']}s")

frame = mt.extract_frame(video, 2.5, WORK / "frame.png")
check("extract_frame", Path(frame["destination"]).is_file(), f"{frame['size_bytes']}B")

print("\nmusic")
trimmed = mt.trim_audio(music, 1.0, 4.0, WORK / "trim.wav")
check("trim_audio", abs((trimmed["duration_seconds"] or 0) - 3.0) < 0.4, f"{trimmed['duration_seconds']}s")

faded = mt.fade_audio(music, WORK / "faded.mp3", fade_in_seconds=1.0, fade_out_seconds=2.0)
check("fade_audio", (faded["duration_seconds"] or 0) > 7.0, f"{faded['duration_seconds']}s")

looped = mt.loop_audio(music, WORK / "loop.mp3", 12.0)
check("loop_audio", abs((looped["duration_seconds"] or 0) - 12.0) < 0.5, f"{looped['duration_seconds']}s")

normal = mt.normalize_loudness(music, WORK / "normal.mp3", target_lufs=-14.0)
check("normalize_loudness", normal["after_lufs"] is not None, f"{normal['before_lufs']} -> {normal['after_lufs']} LUFS")

sped = mt.tempo_shift(music, WORK / "fast.mp3", 1.5)
check("tempo_shift", (sped["duration_seconds"] or 9) < 7.0, f"{sped['duration_seconds']}s at {sped['factor']}x")

mixed = mt.mix_tracks(
    [
        {"path": str(voice), "role": "voice", "gain_db": 0},
        {"path": str(music), "role": "music", "gain_db": -6, "loop": True},
    ],
    WORK / "mix.mp3",
    duration_seconds=6.0,
)
check("mix_tracks ducked", mixed["ducked"] and (mixed["duration_seconds"] or 0) > 5.0, f"{mixed['duration_seconds']}s, {mixed['track_count']} tracks, {mixed['loudness']} LUFS")

mixed_plain = mt.mix_tracks(
    [{"path": str(voice)}, {"path": str(music), "offset_seconds": 1.0, "gain_db": -12}],
    WORK / "mix2.wav",
)
check("mix_tracks plain", mixed_plain["ducked"] is False, f"{mixed_plain['duration_seconds']}s")

print("\nimage composition")
composed = mt.compose_layers(
    photo_a,
    [
        {"path": str(photo_b), "x": "center", "y": "bottom-right", "scale": 0.4, "opacity": 0.8},
        {"path": str(photo_b), "x": 20, "y": 20, "scale": 0.25, "blend": "screen"},
    ],
    WORK / "composed.png",
)
check("compose_layers", composed["layer_count"] == 2 and Path(composed["destination"]).is_file(), f"{composed['width']}x{composed['height']}")

sheet2 = mt.collage([photo_a, photo_b, photo_a], WORK / "grid.png", columns=2, captions=["one", "two", "three"])
check("collage", sheet2["rows"] == 2 and len(sheet2["cells"]) == 3, f"{sheet2['width']}x{sheet2['height']}")

failed = [name for name, ok, _ in CHECKS if not ok]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
if failed:
    print("failed:", failed)
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if failed else 0)
