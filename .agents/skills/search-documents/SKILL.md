---
name: search-documents
description: >-
  Search public document sources (arXiv, Crossref, Gutenberg, Open Library,
  Wikipedia, Internet Archive) for a topic, download results into the local
  library, and search within downloaded documents. Use when the user asks to
  find/collect/download documents, papers, or references for a project.
---

# Search and collect documents

The backend federates six public sources concurrently, deduplicates, and
reranks by relevance. Results carry rich metadata (authors, year, DOI, PDF
URL, citations, open-access) and can be exported as BibTeX or Markdown.

1. Search across all sources:

```bash
curl -s "http://127.0.0.1:8080/documents/search?q=<QUERY>&limit=10"
```

   Expect HTTP 200 with a JSON array of results. Each result has `id`,
   `title`, `authors`, `year`, `abstract`, `source`, `doi`, `pdf_url`,
   `landing_url`, `venue`, `citations`, `is_open_access`, and `score`.

2. Pick a result and download it into the library, attaching it to a project:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/documents \
  -H 'Content-Type: application/json' \
  -d '<the full result JSON from step 1>'
```

   The backend streams the PDF into `library/`, indexes it page-by-page, and
   returns the project with the new entry in `documents`. HTTP 502 means the
   download failed (bad URL, network error).

3. Search within everything downloaded:

```bash
curl -s "http://127.0.0.1:8080/library/search?q=<QUERY>&limit=20"
```

   Returns ranked BM25 hits with highlighted snippets (`path`, `title`,
   `page`, `snippet`, `score`).

4. Inspect the library:

```bash
curl -s http://127.0.0.1:8080/library
```

Notes:
- Sources are queried concurrently and degrade gracefully — a dead source
  never breaks the search.
- Disable web sources entirely with `CONTENT_FACTORY_DOCUMENTS_WEB_ENABLED=false`.
- On Windows PowerShell use `curl.exe` instead of `curl`.