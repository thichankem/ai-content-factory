"""Tests for the dedup and search modules."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from content_factory.dedup import (
    find_near_duplicates,
    hamming_distance,
    image_hash,
    perceptual_hash,
    video_sample_hashes,
)
from content_factory.search import MediaSearchIndex, cosine_similarity


def test_perceptual_hash_is_stable_and_distinguishes_images() -> None:
    img_a = np.zeros((24, 24, 3), dtype=np.uint8)
    img_a[:, 12:, :] = 255
    img_b = np.zeros((24, 24, 3), dtype=np.uint8)
    img_b[:, :12, :] = 255

    hash_a = perceptual_hash(img_a)
    assert hash_a == perceptual_hash(img_a)
    assert len(hash_a) == 64
    assert hash_a != perceptual_hash(img_b)


def test_perceptual_hash_empty_image() -> None:
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    assert perceptual_hash(empty) == ""


def test_hamming_distance_basic_cases() -> None:
    assert hamming_distance("0000", "0000") == 0
    assert hamming_distance("0000", "0001") == 1
    assert hamming_distance("1111", "0000") == 4
    # Missing trailing positions count as differing.
    assert hamming_distance("0000", "00") == 2
    assert hamming_distance("", "") == 0


def test_find_near_duplicates_groups_and_ignores_distinct() -> None:
    hashes = {
        "a": "000000",
        "b": "000001",
        "c": "000010",
        "d": "111111",
    }
    groups = find_near_duplicates(hashes, max_distance=2)
    assert groups == [["a", "b", "c"]]
    grouped = [member for group in groups for member in group]
    assert "d" not in grouped


def test_video_sample_hashes_returns_at_least_one(tmp_path) -> None:
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (160, 90))
    for i in range(30):
        frame = np.full((90, 160, 3), i * 8, dtype=np.uint8)
        writer.write(frame)
    writer.release()

    samples = video_sample_hashes(str(path), sample_every=1)
    assert len(samples) >= 1
    assert all(isinstance(ts, float) and isinstance(h, str) for ts, h in samples)


def test_image_hash_raises_on_missing_file(tmp_path) -> None:
    with pytest.raises(ValueError):
        image_hash(str(tmp_path / "missing.png"))


def test_search_ranks_relevant_item_first() -> None:
    index = MediaSearchIndex()
    index.add("1", "cats.mp4", "video", "A documentary about cats and kittens.")
    index.add("2", "dogs.mp4", "video", "A documentary about dogs and puppies.")

    hits = index.search("kittens", top_k=2)
    assert hits[0].media_id == "1"
    assert hits[0].kind == "video"
    assert hits[0].snippet
    assert index.size() == 2


def test_search_with_embedder_fuses_scores(tmp_path) -> None:
    class FixedEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    index = MediaSearchIndex(embedder=FixedEmbedder())
    index.add("1", "cats.mp4", "video", "A documentary about cats.")
    index.add("2", "dogs.mp4", "video", "A documentary about dogs.")

    hits = index.search("cats", top_k=1)
    assert len(hits) == 1
    assert hits[0].media_id == "1"
    assert hits[0].score >= 0.0


def test_cosine_similarity_identical_and_orthogonal() -> None:
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(0.0)
    assert cosine_similarity([], [1.0]) == 0.0
