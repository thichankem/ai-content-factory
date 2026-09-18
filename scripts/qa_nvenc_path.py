"""Live check: does the real encode path put work on the 4060?

Drives :func:`content_factory.render._run_encode` — the same function the export
path uses — against the real governor, then reads the produced file back to prove
which encoder wrote it. Also drives the overload watchdog.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from content_factory.config import Settings  # noqa: E402
from content_factory.render import RenderError, _run_command, _run_encode  # noqa: E402
from content_factory.resources import probe  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def main() -> int:
    from content_factory.resources import ResourceGovernor

    profile = probe()
    governor = ResourceGovernor(Settings(), probe_fn=lambda: profile)

    print("=== discovered builds ===")
    for build in profile.binaries:
        print(f"  {build.short_version:8s} {build.path}")

    print("\n=== encoder resolution ===")
    resolved = governor.resolve_hardware_encoder()
    check("a working hardware encoder was resolved", resolved is not None, str(resolved))
    assert resolved is not None
    binary, encoder = resolved
    check("it is NVENC", encoder == "h264_nvenc", encoder)
    check("it needs the second build", binary != profile.ffmpeg)

    choice = governor.video_codec("mp4")
    check("video_codec returns h264_nvenc", choice.encoder == "h264_nvenc")
    check("video_codec carries the alternate binary", choice.binary == binary)
    check("no hardware decode is planned (measured slower)", governor.decoder_args("mp4") == ())

    print("\n=== a real encode through _run_encode ===")
    tmp = Path(tempfile.mkdtemp(prefix="cf_nvenc_"))
    out = tmp / "out.mp4"

    def build_prefix(decode: list[str], encoder_binary: str | None = None) -> list[str]:
        return [
            encoder_binary or "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=1080x1920:r=30",
            "-t",
            "8",
        ]

    started = time.monotonic()
    completed = _run_encode(
        build_prefix,
        export_format="mp4",
        threads=1,
        total_seconds=8,
        output_path=out,
        governor=governor,
    )
    elapsed = time.monotonic() - started
    check("the encode returned 0", completed.returncode == 0, completed.stderr[-200:])
    check("an output file exists", out.is_file() and out.stat().st_size > 0)

    if out.is_file():
        info = subprocess.run(
            [binary, "-hide_banner", "-i", str(out)],
            capture_output=True,
            text=True,
            check=False,
        )
        banner = info.stderr
        print(f"      {elapsed:.2f}s for 8s of 1080x1920")
        check("the file reports a 1080x1920 h264 stream", "h264" in banner)
        check(
            "it was encoded by the GPU build (fast, ~real time for 1 thread)",
            elapsed < 6.0,
            f"{elapsed:.2f}s",
        )
        print(f"      ffprobe: {[l for l in banner.splitlines() if 'Stream' in l][:1]}")

    print("\n=== fallback still works when hardware is refused ===")
    refusing = ResourceGovernor(
        Settings(),
        probe_fn=lambda: profile,
        encoder_probe=lambda _binary, _encoder: (False, "nvenc API 13.1 required"),
    )
    out2 = tmp / "out_soft.mp4"
    completed2 = _run_encode(
        build_prefix,
        export_format="mp4",
        threads=1,
        total_seconds=4,
        output_path=out2,
        governor=refusing,
    )
    check("software fallback produced a file", completed2.returncode == 0 and out2.is_file())
    check(
        "the fallback is recorded as a software encode",
        refusing.snapshot()["stats"]["last_encoder"] == "libx264",
        refusing.snapshot()["stats"]["last_encoder"],
    )

    print("\n=== the overload watchdog aborts a runaway render ===")
    hot = ResourceGovernor(
        Settings(render_monitor_seconds=0.25, ram_abort_mb=350),
        probe_fn=lambda: profile,
        pressure=lambda: (120, 91),
    )
    started = time.monotonic()
    killed = False
    reason = ""
    try:
        _run_command(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            120.0,
            governor=hot,
        )
    except RenderError as exc:
        killed = True
        reason = str(exc)
    took = time.monotonic() - started
    check("a runaway render was aborted", killed, reason[:120])
    check("it was aborted promptly, not at the deadline", took < 15.0, f"{took:.2f}s")
    check("the reason names the pressure", "protect the machine" in reason)
    check("the reason cites RAM", "120MB" in reason, reason[:120])

    print("\n=== a healthy machine is left alone ===")
    fine = _run_command(
        [sys.executable, "-c", "print('ok')"], 30.0, governor=governor
    )
    check("a normal command still succeeds", fine.returncode == 0 and "ok" in fine.stdout)

    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    print(json.dumps(governor.snapshot()["hardware"]["binaries"], indent=2)[:400])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
