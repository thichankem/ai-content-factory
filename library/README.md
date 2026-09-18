# Knowledge & Asset Library: `library/`

The local document corpus and media asset repository for research, RAG retrieval and video synthesis. It is backed by **`documents.py` and `library.py`**, and it is **created on demand** — a fresh checkout contains only this file.

---

## Layout

```text
library/
├── .index.db       # SQLite FTS5 BM25 index (created on first ingest)
├── media/          # Curated media assets: images, b-roll, overlays
├── audio/          # Voiceover recordings, SFX, ambient stems
├── music/          # Background music with BPM and mood tags
├── videos/         # Source footage and rendered intermediates
└── edited/         # Exported cuts and completed reels
```

Configured in `config.py`:

| Setting | Default |
| :--- | :--- |
| `library_dir` | `./library` |
| `library_db_path` | `./library/.index.db` |
| `media_dir` | `./library/media` |

Only `library_dir` and `library_db_path` are referenced by the code today; `media/`, `audio/`, `music/`, `videos/` and `edited/` are the intended organisation and appear as the corresponding features write to them. Nothing is lost by treating this directory as generated output — as with `storage/`, it is gitignored and fully reproducible.

---

## Knowledge & search subsystem

### 1. SQLite FTS5 full-text search

Implemented in [`src/content_factory/library.py`](../src/content_factory/library.py). Ingested text, PDFs and metadata go into `.index.db` and are queried through BM25 ranking for fast local keyword search — no embedding model, no network, no external index server.

### 2. Federated document ingestion

[`src/content_factory/documents.py`](../src/content_factory/documents.py) fans a query out across public scholarly sources (arXiv, Crossref, Project Gutenberg, Open Library, Wikipedia, Internet Archive) and runs a zero-dependency lexical reranker over the merged results. Web access is controlled by `CONTENT_FACTORY_DOCUMENTS_WEB_ENABLED`; with it off, everything still runs, just from whatever is already local.

### 3. Retrieval and grounding

[`src/content_factory/rag.py`](../src/content_factory/rag.py) does template-driven chunking and hybrid retrieval (vector + BM25) with reciprocal-rank fusion, then attaches citations so a claim can be traced back to its source.

### 4. Media deduplication

[`src/content_factory/media.py`](../src/content_factory/media.py) computes perceptual difference hashes (dHash) so visually redundant b-roll is detected before it produces a repetitive cut. `POST /media/dedup` returns the duplicate pairs, the groups they form, and the distance threshold used.

---

## Quality note on this corpus

Nothing in this directory is auto-approved. A document landing here is a *candidate* source, and the source-rights confirmation that Gate 1 requires is always a human decision — see `docs/QA-LAYER.md` and the root `README.md`.
