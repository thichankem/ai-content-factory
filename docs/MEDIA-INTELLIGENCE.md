# Media Intelligence — understand & search the footage library

Beyond transforming media, the factory now *understands* its library: find the
right clip, spot near-duplicates, and (later) match footage to a script
semantically. Implemented in `src/content_factory/dedup.py` and `search.py`.

## Asset dedup — `dedup.py`

Cleans the library by detecting clips/images that are identical or near-identical,
so the operator never reuses a stale duplicate.

- `perceptual_hash(image)` — dHash (difference hash) → a compact binary string.
- `image_hash(path)` — hash one image file (Windows-Unicode safe via `np.fromfile`).
- `video_sample_hashes(video_path, sample_every)` — hash sampled frames of a video.
- `hamming_distance(a, b)` — bit distance between two hashes.
- `find_near_duplicates(hashes, max_distance)` — group keys whose hashes are within
  a Hamming distance → near-duplicate clusters.

```python
from content_factory.dedup import image_hash, find_near_duplicates
hashes = {"clip-a": image_hash("a.mp4"), "clip-b": image_hash("b.mp4")}
for group in find_near_duplicates(hashes, max_distance=4):
    print("duplicates:", group)
```

## Semantic search seam — `search.py`

Search the whole library by transcript/filename. Lexical BM25 ranking works out
of the box (free, offline); a pluggable `Embedder` upgrades it to true semantic
vectors when a model is wired in — without changing the call site.

```python
from content_factory.search import MediaSearchIndex

idx = MediaSearchIndex()                      # or MediaSearchIndex(my_embedder)
idx.add("m1", "interview.mp4", "video", "person in red coat laughing")
idx.add("m2", "city.mp4", "video", "traffic and city streets")
hits = idx.search("person laughing in red")
```

`SearchHit` carries `media_id`, `filename`, `kind`, `score`, `snippet`. When an
embedder is present, the final score fuses `0.6 * cosine + 0.4 * lexical`.

## Configuration

```ini
CONTENT_FACTORY_DEDUP_MAX_DISTANCE=4
CONTENT_FACTORY_SEARCH_EMBEDDER=lexical   # lexical | embedding
```

## Planned (needs a model)

- **Auto B-roll matching** — agent reads the script and proposes footage that
  matches each line semantically (built on `search.py` + captions).
- **Continuity checker** — face embeddings to catch jump-cut / outfit errors
  between scenes (needs a face model).

## Guardrail

Dedup and search only *organize* the library — they never auto-confirm source
rights or auto-select footage for publish. The two human gates still stand.