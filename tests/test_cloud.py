"""Media storage backend tests (local, in-memory, and S3 delegation)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_factory.cloud import (
    LocalMediaStorage,
    MemoryMediaStorage,
    S3MediaStorage,
    build_media_storage,
)
from content_factory.media import MediaLibrary


@pytest.fixture
def mem() -> MemoryMediaStorage:
    return MemoryMediaStorage()


def test_memory_storage_crud(tmp_path: Path, mem: MemoryMediaStorage) -> None:
    src = tmp_path / "a.bin"
    src.write_bytes(b"hello")
    assert mem.save("k", src) == 5
    assert mem.exists("k")
    assert mem.stat("k") == 5
    with mem.open("k") as f:
        assert f.read() == b"hello"
    mem.delete("k")
    assert not mem.exists("k")
    assert mem.stat("k") == 0


def test_local_storage_crud(tmp_path: Path) -> None:
    store = LocalMediaStorage(tmp_path / "files")
    src = tmp_path / "a.bin"
    src.write_bytes(b"xyz")
    assert store.save("media/x/a.bin", src) == 3
    assert store.exists("media/x/a.bin")
    assert store.stat("media/x/a.bin") == 3
    store.delete("media/x/a.bin")
    assert not store.exists("media/x/a.bin")


def test_media_library_uses_memory_storage(tmp_path: Path) -> None:
    mem = MemoryMediaStorage()
    lib = MediaLibrary(tmp_path / "media", storage=mem)
    item = lib.upload("clip.mp4", b"\x00" * 64)
    key = f"media/{item.id}/clip.mp4"
    assert mem.exists(key)
    # path_for pulls the authoritative copy back into the local cache.
    path = lib.path_for(item)
    assert path is not None and path.is_file()
    assert path.stat().st_size == 64
    # delete removes it from storage too.
    lib.delete(item.id)
    assert not mem.exists(key)


def test_build_media_storage_defaults_to_local(tmp_path: Path) -> None:
    store = build_media_storage(local_root=tmp_path / "files")
    assert isinstance(store, LocalMediaStorage)


def test_build_media_storage_uses_s3_when_bucket_set(tmp_path: Path) -> None:
    with patch("content_factory.cloud.S3MediaStorage") as cls:
        cls.return_value = MagicMock()
        store = build_media_storage(
            local_root=tmp_path / "files",
            s3_bucket="my-bucket",
            s3_endpoint="https://minio.local",
            s3_access_key="k",
            s3_secret_key="s",
        )
    assert store is cls.return_value
    cls.assert_called_once_with(
        "my-bucket",
        endpoint_url="https://minio.local",
        region=None,
        access_key="k",
        secret_key="s",
        prefix="content-factory",
    )


def test_s3_storage_delegates_to_boto3(tmp_path: Path) -> None:
    import sys

    client = MagicMock()
    client.head_object.side_effect = Exception("not found")
    fake_boto = MagicMock()
    fake_boto.client.return_value = client
    with patch.dict(sys.modules, {"boto3": fake_boto}):
        store = S3MediaStorage(
            "bucket",
            endpoint_url="http://localhost:9000",
            access_key="k",
            secret_key="s",
        )
    src = tmp_path / "a.bin"
    src.write_bytes(b"data")
    assert store.save("media/x/a.bin", src) == 4
    client.upload_file.assert_called_once()
    assert store.exists("media/x/a.bin") is False  # head_object raised -> absent
    assert store.stat("media/x/a.bin") == 0
    store.delete("media/x/a.bin")
    client.delete_object.assert_called_once()


def test_s3_storage_requires_boto3(tmp_path: Path) -> None:
    import sys

    with patch.dict(sys.modules, {"boto3": None}):
        with pytest.raises(RuntimeError):
            S3MediaStorage("bucket")
