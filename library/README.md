# Knowledge & Asset Library: `library/`

This directory serves as the local media asset repository and document knowledge base for research, RAG retrieval, and video synthesis in the **AI Content Factory**.

---

## Directory Organization

```text
library/
├── .index.db           # SQLite database with FTS5 BM25 full-text search index
├── media/              # Curated uploaded media assets (images, b-roll, overlays)
├── audio/              # Voiceover recordings, sound effects, ambient stems
├── music/              # Background music tracks with BPM and mood tags
├── videos/             # Source footage clips and rendered intermediates
└── edited/             # Exported video cuts and completed reels
```

---

## Knowledge & Search Subsystem

1. **SQLite FTS5 Full-Text Search**:
   - Managed via [`src/content_factory/documents.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/src/content_factory/documents.py).
   - Ingests text documents, PDFs, and metadata into `.index.db` using BM25 ranking for ultra-fast local keyword queries (`GET /library/search?q=...`).
2. **Media Deduplication**:
   - Uses perceptual difference hashing (dHash) implemented in [`src/content_factory/media.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/src/content_factory/media.py) to identify visually redundant b-roll and prevent repetitive shot selection.
3. **Federated Ingest**:
   - Extensible adapters allow importing public domain papers and books from arXiv, Project Gutenberg, and Wikimedia Commons.
