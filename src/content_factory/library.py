"""Local document library: streaming downloads plus a BM25 full-text index.

Ported from the Scribd-Doc-Downloader-ToolKit's search index: SQLite FTS5
ships inside CPython, stores an inverted index on disk, and ranks with a real
BM25 implementation — instant ranked search over downloaded documents with
highlighted snippets and no extra dependency. PDFs are indexed page-by-page
via PyMuPDF (falling back to pypdf); files are re-indexed only when their
SHA-256 changes.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .models import DocumentResult, LibraryHit, LibraryStats

_SUPPORTED_EXTENSIONS = frozenset(
    {".pdf", ".txt", ".md", ".markdown", ".rst", ".html", ".htm", ".csv"}
)
_SNIPPET_OPEN = "[["
_SNIPPET_CLOSE = "]]"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", str(name or "document"))
    name = re.sub(r"\s+", " ", name).strip()
    return name[:max_len] if name else "document"


def _pdf_units(path: Path) -> list[tuple[int, str]]:
    try:
        import pymupdf

        with pymupdf.open(str(path)) as doc:
            return [
                (index + 1, page.get_text("text") or "")
                for index, page in enumerate(doc)
            ]
    except Exception:  # noqa: BLE001 - optional PDF backend: fall through to pypdf
        pass
    try:
        import pypdf

        reader = pypdf.PdfReader(str(path))
        return [
            (index + 1, page.extract_text() or "")
            for index, page in enumerate(reader.pages)
        ]
    except Exception:  # noqa: BLE001 - optional PDF backend: no extractor available at all
        return []


def _plain_units(path: Path) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if path.suffix.lower() in (".html", ".htm"):
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
    return [(1, text)]


def _build_match_query(query: str) -> str:
    terms: list[str] = []
    for quoted, bare in re.findall(r'"([^"]+)"|(\S+)', str(query)):
        term = (quoted or bare or "").strip()
        if not term:
            continue
        prefix = term.endswith("*") and not quoted
        if prefix:
            term = term[:-1]
        term = term.replace('"', '""')
        if not term:
            continue
        terms.append(f'"{term}"*' if prefix else f'"{term}"')
    return " AND ".join(terms)


@dataclass
class IndexStats:
    """Outcome of an indexing run."""

    files_indexed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    pages_indexed: int = 0
    errors: list[str] = field(default_factory=list)


class DocumentLibrary:
    """Persistent BM25 full-text index over a folder of downloaded documents."""

    def __init__(self, root_dir: str, db_path: str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._fts5 = self._probe_fts5()
        self._init_schema()

    def close(self) -> None:
        with contextlib.suppress(sqlite3.Error):
            self._conn.close()

    def _probe_fts5(self) -> bool:
        try:
            probe = sqlite3.connect(":memory:")
            try:
                probe.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
                return True
            finally:
                probe.close()
        except sqlite3.Error:
            return False

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                sha256 TEXT,
                pages INTEGER DEFAULT 0,
                indexed_at TEXT
            )
            """
        )
        if self._fts5:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5("
                "path UNINDEXED, title UNINDEXED, page UNINDEXED, text)"
            )
        else:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS pages_plain "
                "(path TEXT, title TEXT, page INTEGER, text TEXT)"
            )
        self._conn.commit()

    # --- downloads ----------------------------------------------------------

    async def download(
        self, result: DocumentResult, timeout_seconds: float = 60.0
    ) -> Path:
        """Stream a document into the library and index it. Returns the path."""
        url = result.pdf_url or result.landing_url
        if not url:
            raise ValueError(f"No downloadable URL for '{result.title}'")
        dest = self.root / f"{_sanitize_filename(result.title)}.pdf"
        if dest.exists():
            return dest
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with dest.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        handle.write(chunk)
        self.index_file(dest)
        return dest

    # --- indexing -----------------------------------------------------------

    def index_directory(self, path: str | None = None) -> IndexStats:
        stats = IndexStats()
        root = Path(path) if path else self.root
        for candidate in sorted(root.rglob("*")):
            if (
                candidate.is_file()
                and candidate.suffix.lower() in _SUPPORTED_EXTENSIONS
            ):
                try:
                    pages = self.index_file(candidate)
                except Exception as err:  # noqa: BLE001 - one unreadable file must not abort a whole index run
                    stats.files_failed += 1
                    stats.errors.append(f"{candidate.name}: {err}")
                    continue
                if pages is None:
                    stats.files_skipped += 1
                else:
                    stats.files_indexed += 1
                    stats.pages_indexed += pages
        return stats

    def index_file(self, path: Path) -> int | None:
        """Index one file; returns unit count, or None if unchanged."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        digest = _sha256(path)
        absolute = str(path.resolve())
        existing = self._conn.execute(
            "SELECT sha256 FROM documents WHERE path = ?", (absolute,)
        ).fetchone()
        if existing and existing["sha256"] == digest:
            return None
        units = (
            _pdf_units(path) if path.suffix.lower() == ".pdf" else _plain_units(path)
        )
        if not units:
            raise ValueError(f"No extractable text found in {path.name}")
        with self._conn:
            self._conn.execute("DELETE FROM documents WHERE path = ?", (absolute,))
            self._delete_pages(absolute)
            self._conn.execute(
                "INSERT INTO documents (path, title, sha256, pages, indexed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (absolute, path.stem, digest, len(units), _now()),
            )
            if self._fts5:
                self._conn.executemany(
                    "INSERT INTO pages_fts (path, title, page, text) "
                    "VALUES (?, ?, ?, ?)",
                    [(absolute, path.stem, page, text) for page, text in units],
                )
            else:
                self._conn.executemany(
                    "INSERT INTO pages_plain (path, title, page, text) "
                    "VALUES (?, ?, ?, ?)",
                    [(absolute, path.stem, page, text) for page, text in units],
                )
        return len(units)

    def _delete_pages(self, absolute: str) -> None:
        table = "pages_fts" if self._fts5 else "pages_plain"
        self._conn.execute(f"DELETE FROM {table} WHERE path = ?", (absolute,))

    def remove_file(self, path: str) -> bool:
        absolute = str(Path(path).resolve())
        with self._conn:
            deleted = self._conn.execute(
                "DELETE FROM documents WHERE path = ?", (absolute,)
            ).rowcount
            if deleted:
                self._delete_pages(absolute)
        return bool(deleted)

    # --- searching ----------------------------------------------------------

    def search(self, query: str, *, limit: int = 20) -> list[LibraryHit]:
        query = str(query or "").strip()
        if not query:
            return []
        limit = max(1, min(int(limit), 500))
        if self._fts5:
            expression = _build_match_query(query)
            if not expression:
                return []
            try:
                rows = self._conn.execute(
                    "SELECT path, title, page, "
                    f"snippet(pages_fts, 3, '{_SNIPPET_OPEN}', '{_SNIPPET_CLOSE}', "
                    "' … ', 24) AS snippet, "
                    "bm25(pages_fts, 0.0, 0.0, 0.0, 1.0) AS score "
                    "FROM pages_fts WHERE pages_fts MATCH ? ORDER BY score LIMIT ?",
                    (expression, limit),
                ).fetchall()
                return [
                    LibraryHit(
                        path=row["path"],
                        title=row["title"],
                        page=int(row["page"] or 1),
                        snippet=(row["snippet"] or "").strip(),
                        score=-float(row["score"] or 0.0),
                    )
                    for row in rows
                ]
            except sqlite3.Error:
                return self._like_search(query, limit=limit)
        return self._like_search(query, limit=limit)

    def _like_search(self, query: str, *, limit: int) -> list[LibraryHit]:
        lowered = query.lower()
        rows = self._conn.execute(
            "SELECT path, title, page, text FROM pages_plain "
            "WHERE lower(text) LIKE ? LIMIT ?",
            (f"%{lowered}%", limit),
        ).fetchall()
        hits: list[LibraryHit] = []
        for row in rows:
            text = row["text"] or ""
            position = text.lower().find(lowered)
            start = max(0, position - 120)
            hits.append(
                LibraryHit(
                    path=row["path"],
                    title=row["title"],
                    page=int(row["page"] or 1),
                    snippet=text[start : position + 240].strip(),
                    score=float(len(re.findall(re.escape(lowered), text.lower()))),
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits

    # --- reporting ----------------------------------------------------------

    def list_documents(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT path, title, pages, indexed_at FROM documents "
            "ORDER BY indexed_at DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> LibraryStats:
        documents = self._conn.execute(
            "SELECT COUNT(*) AS c, COALESCE(SUM(pages), 0) AS p FROM documents"
        ).fetchone()
        size_bytes = (
            Path(self._db_path).stat().st_size if Path(self._db_path).exists() else 0
        )
        return LibraryStats(
            database=self._db_path,
            fts5=self._fts5,
            documents=int(documents["c"]),
            pages=int(documents["p"]),
            size_bytes=size_bytes,
        )
