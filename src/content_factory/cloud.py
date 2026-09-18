"""Pluggable media storage backends for the universal media library.

``MediaLibrary`` stores the *authoritative* copy of every media file through a
:class:`MediaStorage` backend while keeping a local cache for in-place
processing (ffmpeg, transcription, trimming all need a real local path). The
default backend is local disk; an S3-compatible backend is activated when the
``S3_*`` settings are present and ``boto3`` is installed, so the same library
can be cloud-backed without changing any caller.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol

__all__ = [
    "MediaStorage",
    "LocalMediaStorage",
    "MemoryMediaStorage",
    "S3MediaStorage",
    "build_media_storage",
]


class MediaStorage(Protocol):
    """Where a media file's authoritative copy lives."""

    def save(self, key: str, source: Path) -> int:
        """Persist the file at ``source`` under ``key``; return bytes written."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open the object at ``key`` for reading."""
        ...

    def exists(self, key: str) -> bool:
        """True if an object exists at ``key``."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at ``key`` (idempotent)."""
        ...

    def stat(self, key: str) -> int:
        """Size in bytes of the object at ``key`` (0 if missing)."""
        ...


class LocalMediaStorage:
    """Files under a root directory, mirroring the legacy on-disk layout."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def save(self, key: str, source: Path) -> int:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        return dest.stat().st_size

    def open(self, key: str) -> BinaryIO:
        return self._path(key).open("rb")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def stat(self, key: str) -> int:
        path = self._path(key)
        return path.stat().st_size if path.is_file() else 0


class MemoryMediaStorage:
    """In-memory backend for tests (never touches disk or the network)."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def save(self, key: str, source: Path) -> int:
        data = source.read_bytes()
        self._objects[key] = data
        return len(data)

    def open(self, key: str) -> BinaryIO:
        if key not in self._objects:
            raise FileNotFoundError(key)
        return io.BytesIO(self._objects[key])

    def exists(self, key: str) -> bool:
        return key in self._objects

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    def stat(self, key: str) -> int:
        return len(self._objects.get(key, b""))


class S3MediaStorage:
    """S3-compatible object storage (boto3), activated only when configured.

    ``boto3`` is imported lazily so the rest of the library works without it.
    Keys map to ``<prefix>/media/<id>/<filename>`` in the bucket.
    """

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        prefix: str = "content-factory",
    ) -> None:
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on optional tool
            raise RuntimeError(
                "S3 media storage requires boto3; run `pip install boto3`."
            ) from exc
        kwargs: dict[str, object] = {}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if region:
            kwargs["region_name"] = region
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client("s3", **kwargs)
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def _key(self, key: str) -> str:
        return f"{self._prefix}/{key}" if self._prefix else key

    def save(self, key: str, source: Path) -> int:
        size = source.stat().st_size
        self._client.upload_file(str(source), self._bucket, self._key(key))
        return size

    def open(self, key: str) -> BinaryIO:
        import io as _io

        body = self._client.get_object(Bucket=self._bucket, Key=self._key(key))["Body"]
        return _io.BytesIO(body.read())

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._key(key))
            return True
        except Exception:  # noqa: BLE001 - 404 / access errors mean "absent"
            return False

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self._key(key))

    def stat(self, key: str) -> int:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=self._key(key))
            return int(head.get("ContentLength", 0))
        except Exception:  # noqa: BLE001
            return 0


def build_media_storage(
    *,
    local_root: Path,
    s3_bucket: str | None = None,
    s3_endpoint: str | None = None,
    s3_region: str | None = None,
    s3_access_key: str | None = None,
    s3_secret_key: str | None = None,
    s3_prefix: str = "content-factory",
) -> MediaStorage:
    """Pick the storage backend: S3 when configured, otherwise local disk."""
    if s3_bucket:
        return S3MediaStorage(
            s3_bucket,
            endpoint_url=s3_endpoint,
            region=s3_region,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            prefix=s3_prefix,
        )
    return LocalMediaStorage(local_root)
