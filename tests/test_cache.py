"""Content-addressed cache: hashing, atomic put/get, JSON, and memoization."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from content_factory.cache import ContentCache, content_hash


def test_content_hash_is_stable_and_distinct(tmp_path) -> None:
    assert content_hash(b"a", b"b") == content_hash(b"a", b"b")
    assert content_hash(b"a", b"b") != content_hash(b"ab")
    assert len(content_hash(b"x")) == 32


def test_put_get_roundtrip(tmp_path) -> None:
    cache = ContentCache(tmp_path / "cache")
    assert cache.get("k1") is None
    cache.put("k1", b"hello")
    assert cache.get("k1") == b"hello"
    assert (cache.root / "k1.bin").is_file()


def test_json_helpers(tmp_path) -> None:
    cache = ContentCache(tmp_path / "cache")
    assert cache.get_json("k") is None
    cache.put_json("k", {"a": 1, "b": [True, "x"]})
    assert cache.get_json("k") == {"a": 1, "b": [True, "x"]}


def test_cached_computes_once_and_reuses(tmp_path) -> None:
    cache = ContentCache(tmp_path / "cache")
    calls: list[int] = []

    def compute() -> bytes:
        calls.append(1)
        return b"result"

    first = cache.cached("ns", b"payload", {"p": 1}, compute)
    second = cache.cached("ns", b"payload", {"p": 1}, compute)
    assert first == second == b"result"
    assert len(calls) == 1  # second call reused the cache


def test_cached_distinguishes_payload_and_params(tmp_path) -> None:
    cache = ContentCache(tmp_path / "cache")
    calls: list[bytes] = []

    def make(value: bytes):
        def compute() -> bytes:
            calls.append(value)
            return value

        return compute

    cache.cached("ns", b"a", {}, make(b"a"))
    cache.cached("ns", b"b", {}, make(b"b"))
    cache.cached("ns", b"a", {"x": 1}, make(b"c"))
    assert len(calls) == 3  # different payload/params => recompute


@pytest.mark.parametrize("payload", [b"", b"a", bytes(range(256)) * 17])
@pytest.mark.parametrize("params", [{}, {"language": "vi", "z": [1, "âm"]}])
def test_file_keys_preserve_exact_framing(tmp_path, monkeypatch, payload, params):
    path = tmp_path / "input.bin"
    path.write_bytes(payload)
    cache = ContentCache(tmp_path / "cache")
    parts = (
        b"transcribe",
        payload,
        json.dumps(params, sort_keys=True, ensure_ascii=False).encode(),
    )
    expected = hashlib.sha256(
        b"".join(len(p).to_bytes(8, "big") + p for p in parts)
    ).hexdigest()[:32]
    original_open = Path.open
    reads = []

    @contextmanager
    def bounded_open(self, *args, **kwargs):
        with original_open(self, *args, **kwargs) as source:

            def read(size=-1):
                assert 0 < size <= 7
                reads.append(size)
                return source.read(size)

            yield SimpleNamespace(read=read, fileno=source.fileno)

    monkeypatch.setattr(Path, "open", bounded_open)
    assert cache.key_for_file("transcribe", path, params, chunk_bytes=7) == expected
    assert cache.key_for("transcribe", payload, params) == expected
    assert content_hash(path, chunk_bytes=7) == content_hash(payload)
    if payload:
        assert reads


@pytest.mark.parametrize("chunk_bytes", [0, -1, 16 * 1024 * 1024 + 1, True])
def test_hash_rejects_invalid_chunk_size(chunk_bytes):
    with pytest.raises(ValueError, match="stream_chunk_bytes"):
        content_hash(b"payload", chunk_bytes=chunk_bytes)
