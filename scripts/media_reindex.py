"""Re-probe the media library and repair what the index got wrong.

The library's ``kind`` used to be decided by the file extension alone, so a
``.mp4``/``.webm`` container holding only an audio stream was registered as
``video`` and an ``.png`` that was really 108 bytes of HTML was registered as an
``image``. Everything built on that classification then misbehaved: re-encoding
a "video" with no video stream failed, and the palette/collage tools choked on
the fake image. A full library scan found 5 of 45 items wrong that way.

``MediaLibrary.upload_stream`` now takes the kind from the real streams
(``media.resolve_kind``), but an index written *before* that stays wrong until it
is recomputed. This script does that, and reports the entries whose file is
missing or unreadable so they can be removed instead of breaking a later call.

Read-only by default; pass ``--apply`` to write the changes back.

Usage::

    python scripts/media_reindex.py                  # report only
    python scripts/media_reindex.py --apply          # fix kinds
    python scripts/media_reindex.py --apply --prune  # also drop broken entries
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from content_factory.config import get_settings  # noqa: E402
from content_factory.media import MediaLibrary, probe_media, resolve_kind  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="write the corrections to the index"
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="with --apply, also delete entries whose file is gone",
    )
    parser.add_argument(
        "--media-dir",
        default=None,
        help="override the media directory (defaults to the configured one)",
    )
    args = parser.parse_args()

    settings = get_settings()
    library = MediaLibrary(args.media_dir or settings.media_dir)
    items = library.list_items()
    print(f"Re-probing {len(items)} item(s) in {args.media_dir or settings.media_dir}")

    corrected = 0
    broken: list[str] = []
    for item in items:
        path = library.path_for(item)
        if path is None or not path.is_file():
            broken.append(item.id)
            print(f"  [missing] {item.id} {item.filename} ({item.kind.value})")
            continue
        probe = probe_media(path)
        resolved = resolve_kind(item.filename, probe)
        if probe and not (probe.get("has_video") or probe.get("has_audio")):
            streams = "no audio or video stream"
        else:
            streams = "ok"
        if resolved is not item.kind:
            corrected += 1
            print(
                f"  [kind]    {item.id} {item.filename}: "
                f"{item.kind.value} -> {resolved.value} ({streams})"
            )
            if args.apply:
                item.kind = resolved
                item.mime = _mime_for(resolved, item.filename, item.mime)
            continue
        if streams != "ok":
            print(f"  [warning] {item.id} {item.filename}: {streams}")

    if args.apply:
        _write_back(library, items, prune=args.prune, broken=broken)
        print(f"Applied: {corrected} kind correction(s)")
    else:
        print(f"Would correct: {corrected} kind(s). Re-run with --apply to write it.")
    if broken:
        print(
            f"{len(broken)} entr(ies) have no file on disk"
            + (" (removed with --prune)." if (args.apply and args.prune) else ".")
        )
    return 0


def _mime_for(kind, filename: str, current: str) -> str:
    """The content type that matches the corrected kind."""
    import mimetypes

    if str(kind.value) == "audio":
        return mimetypes.guess_type(filename)[0] or "audio/mpeg"
    if str(kind.value) == "video":
        return mimetypes.guess_type(filename)[0] or "video/mp4"
    return current


def _write_back(
    library: MediaLibrary, items, *, prune: bool, broken: list[str]
) -> None:
    """Persist the corrected index through the library's own writer."""
    if prune:
        for item_id in broken:
            library.delete(item_id)
    with library._lock:
        for item in items:
            if item.id in library._items:
                library._items[item.id] = item
        library._save()


if __name__ == "__main__":
    raise SystemExit(main())
