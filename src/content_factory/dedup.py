"""Perceptual-hash near-duplicate detection for the asset library.

Cleaning up a media library means spotting files that are effectively the same
shot — a re-export, a re-compressed copy, a slightly cropped variant. Pixel
comparison is too brittle for that, so this module fingerprints media with a
difference hash (dHash): a tiny, deterministic bit-string that is stable under
minor compression and resolution changes.

Everything here is pure OpenCV + numpy and runs fully offline, so it can be
exercised in tests and called from the MCP server without any model or network.
"""

from __future__ import annotations

import cv2
import numpy as np


def perceptual_hash(image: np.ndarray, hash_size: int = 8) -> str:
    """Return a dHash bit-string for a BGR image.

    The image is resized to ``(hash_size + 1, hash_size)`` grayscale and each
    pixel is compared with its right neighbour; a brighter right neighbour
    yields a ``1`` bit. The result is a binary string of length
    ``hash_size * hash_size``. Degenerate (empty) input yields an empty string.
    """
    if image.size == 0:
        return ""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    return "".join("1" if bit else "0" for bit in diff.flatten())


def image_hash(path: str) -> str:
    """Read an image file and return its perceptual hash.

    The file is read via ``np.fromfile`` + ``cv2.imdecode`` so paths with
    non-ASCII characters (common on Windows) work correctly. Raises
    :class:`ValueError` if the file cannot be read or decoded.
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError as exc:
        raise ValueError(f"cannot read image '{path}'") from exc
    if data.size == 0:
        raise ValueError(f"cannot read image '{path}'")
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode image '{path}'")
    return perceptual_hash(image)


def video_sample_hashes(
    video_path: str, *, sample_every: int = 30
) -> list[tuple[float, str]]:
    """Sample a video and return ``(timestamp_seconds, hash)`` tuples.

    Every ``sample_every``-th frame is fingerprinted. Returns an empty list if
    the video cannot be opened. The capture is always released.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    samples: list[tuple[float, str]] = []
    try:
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % sample_every == 0:
                timestamp = round(index / max(1.0, fps), 3)
                fingerprint = perceptual_hash(frame)
                if fingerprint:
                    samples.append((timestamp, fingerprint))
            index += 1
    finally:
        cap.release()
    return samples


def hamming_distance(a: str, b: str) -> int:
    """Number of differing bits between two hash strings.

    If the strings differ in length, the missing trailing positions of the
    shorter string are counted as differing.
    """
    length = max(len(a), len(b))
    distance = 0
    for i in range(length):
        bit_a = a[i] if i < len(a) else None
        bit_b = b[i] if i < len(b) else None
        if bit_a != bit_b:
            distance += 1
    return distance


def find_near_duplicates(
    hashes: dict[str, str], *, max_distance: int = 4
) -> list[list[str]]:
    """Group keys whose hashes lie within ``max_distance`` Hamming distance.

    Keys are joined into a cluster when any two of them are within the Hamming
    threshold (connected components of the near-duplicate graph). Only clusters
    of two or more keys are returned. Ordering is deterministic: keys are
    processed in sorted order and clusters are returned sorted by first member.
    """
    keys = sorted(hashes)
    parent = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a: str, b: str) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            key_a = keys[i]
            key_b = keys[j]
            if hamming_distance(hashes[key_a], hashes[key_b]) <= max_distance:
                union(key_a, key_b)

    components: dict[str, list[str]] = {}
    for key in keys:
        components.setdefault(find(key), []).append(key)

    groups = [members for members in components.values() if len(members) >= 2]
    groups.sort(key=lambda members: members[0])
    return groups
