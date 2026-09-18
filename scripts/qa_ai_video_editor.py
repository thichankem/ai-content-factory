"""AI Video Editor QA: prove the AI can really edit a video.

Synthesises a short clip with a moving subject, inserts an image, and runs the
full AI edit (analyse -> plan -> track -> composite -> cut -> export) in both
modes:

  * no-vision  — heuristic placement (gradient saliency)
  * with-vision — a vision planner picks the spot

Then verifies the exported ``final.mp4`` has real video + audio streams and
reports where/when the image was inserted and how much was cut.

Exits 0 only when both modes produced a probeable MP4.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from content_factory.ai_video_editor import (
    AiVideoEditor,
    _demo_vision_planner,
    _imwrite,
    extract_audio,
)

ROOT = Path(__file__).resolve().parents[1]


def make_source_video(out: Path, seconds: float = 6.0, fps: int = 15) -> None:
    """A 360x640 clip with a moving red square over a static blue bar + audio."""
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_name(out.stem + "_raw.mp4")
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, (360, 640))
    n = int(seconds * fps)
    for i in range(n):
        frame = np.full((640, 360, 3), 20, dtype=np.uint8)
        cv2.rectangle(frame, (0, 520), (360, 630), (60, 60, 90), -1)
        x = 40 + i * 3
        cv2.rectangle(frame, (x, 300), (x + 40, 340), (0, 0, 200), -1)
        writer.write(frame)
    writer.release()
    # Add a tone so the edited output can be checked for preserved audio.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=330:duration={seconds}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    raw.unlink(missing_ok=True)


def make_logo(out: Path) -> None:
    img = np.full((80, 120, 3), 30, dtype=np.uint8)
    cv2.circle(img, (60, 40), 30, (0, 200, 255), -1)
    _imwrite(out, img)


def main(argv=None) -> int:
    default_out = str(ROOT / "scratch" / "ai_editor")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=str, default=default_out)
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    video = outdir / "source.mp4"
    logo = outdir / "logo.png"
    make_source_video(video)
    make_logo(logo)
    audio = extract_audio(video, outdir / "audio.m4a")

    results = []
    for mode, vision in (("no-vision", None), ("with-vision", _demo_vision_planner)):
        out = outdir / f"final_{mode}.mp4"
        try:
            report = AiVideoEditor(vision=vision, working_width=360).edit(
                video, logo, out, audio_path=audio
            )
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type,codec_name",
                    "-of",
                    "csv",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            types = [line.split(",")[-1] for line in probe.stdout.strip().splitlines()]
            ok = "video" in types and "audio" in types
            p = report.placement
            print(
                f"[{'PASS' if ok else 'FAIL'}] {mode:<12} planner={report.planner} "
                f"placement=({p.x},{p.y},{p.w},{p.h}) cuts={len(report.cuts)} "
                f"frames={report.source_frames}->{report.output_frames} "
                f"streams={','.join(types)} size={out.stat().st_size}B"
            )
            results.append(ok)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {mode:<12} {exc}")
            results.append(False)

    passed = sum(1 for r in results if r)
    line = (
        f"\nSUMMARY total={len(results)} passed={passed} failed={len(results) - passed}"
    )
    print(line)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
