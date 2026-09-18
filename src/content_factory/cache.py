"""Content-addressed cache for expensive, retryable pipeline steps.

Long media pipelines (transcription, vision scoring, scene analysis) are
expensive and often retried. Every entry is keyed by a SHA-256 over
``(namespace, input bytes, params)`` so the same input plus the same options
always resolves to the same entry — a retried run reuses the previous result
instead of recomputing it (idempotent checkpoints). Entries live under a
single ``storage/cache/`` directory and are plain files, so a crashed run
leaves nothing half-written and a restart can resume.

Nothing here touches the network or the model; it is a pure on-disk memo.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import DEFAULT_STREAM_CHUNK_BYTES, validate_stream_chunk_bytes


def content_hash(
    *parts: bytes | Path, chunk_bytes: int = DEFAULT_STREAM_CHUNK_BYTES
) -> str:
    """Return a short SHA-256 over the byte parts.

    Each part is length-framed so concatenation is unambiguous: ``(b"a", b"b")``
    and ``(b"ab",)`` hash differently.
    """
    validate_stream_chunk_bytes(chunk_bytes)
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, Path):
            with part.open("rb") as stream:
                size = os.fstat(stream.fileno()).st_size
                digest.update(size.to_bytes(8, "big"))
                remaining = size
                while remaining:
                    chunk = stream.read(min(chunk_bytes, remaining))
                    if not chunk:
                        raise OSError("File changed while hashing.")
                    digest.update(chunk)
                    remaining -= len(chunk)
                if stream.read(1):
                    raise OSError("File changed while hashing.")
        else:
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()[:32]


class ContentCache:
    """Thread-safe, content-addressed key/value store on disk.

    Keys are caller-supplied (usually a :func:`content_hash`). Values are
    opaque bytes; JSON helpers wrap them. Missing entries return ``None`` so
    callers can fall through to computing.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @property
    def root(self) -> Path:
        """The on-disk cache directory."""
        return self._root

    def path_for(self, key: str) -> Path:
        """Resolve a key to its cache file path (no IO)."""
        return self._root / f"{key}.bin"

    def get(self, key: str) -> bytes | None:
        """Read a cached value, or ``None`` when absent/corrupt."""
        path = self.path_for(key)
        try:
            return path.read_bytes()
        except OSError:
            return None

    def put(self, key: str, value: bytes) -> Path:
        """Write a value atomically (temp file + rename) and return its path."""
        path = self.path_for(key)
        tmp = path.with_suffix(".tmp")
        with self._lock:
            tmp.write_bytes(value)
            tmp.replace(path)
        return path

    # --- JSON helpers ----------------------------------------------------------

    def get_json(self, key: str) -> Any | None:
        """Read a cached JSON value, or ``None`` when absent/unparseable."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def put_json(self, key: str, value: Any) -> Path:
        """Serialize a JSON value into the cache."""
        return self.put(key, json.dumps(value, ensure_ascii=False).encode("utf-8"))

    # --- Memoized compute ------------------------------------------------------

    def cached(
        self,
        namespace: str,
        payload: bytes,
        params: dict[str, Any],
        compute: Callable[[], bytes],
    ) -> bytes:
        """Return the cached bytes for ``(namespace, payload, params)`` or compute.

        The key folds the namespace, the input bytes, and the serialized
        params, so different options never collide. ``compute`` runs only on a
        miss and its result is stored for the next call.
        """
        key = self.key_for(namespace, payload, params)
        hit = self.get(key)
        if hit is not None:
            return hit
        value = compute()
        self.put(key, value)
        return value

    def key_for_file(
        self,
        namespace: str,
        path: Path,
        params: dict[str, Any],
        *,
        chunk_bytes: int = DEFAULT_STREAM_CHUNK_BYTES,
    ) -> str:
        param_bytes = json.dumps(params, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        return content_hash(
            namespace.encode("utf-8"), path, param_bytes, chunk_bytes=chunk_bytes
        )

    def key_for(self, namespace: str, payload: bytes, params: dict[str, Any]) -> str:
        """Derive the content-addressed key for a memoized call."""
        param_bytes = json.dumps(params, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        return content_hash(namespace.encode("utf-8"), payload, param_bytes)
