"""Tests for the local document library (index + download)."""

from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from content_factory.library import DocumentLibrary
from content_factory.models import DocumentResult


@pytest.fixture
def library(tmp_path: Path) -> DocumentLibrary:
    return DocumentLibrary(str(tmp_path / "lib"), str(tmp_path / "lib" / ".index.db"))


def test_index_and_search_txt(library: DocumentLibrary, tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Morning light resets the circadian clock and boosts alertness.",
        encoding="utf-8",
    )
    pages = library.index_file(doc)
    assert pages == 1

    hits = library.search("circadian")
    assert len(hits) == 1
    assert hits[0].title == "notes"
    assert "circadian" in hits[0].snippet.lower()
    assert hits[0].score > 0


def test_reindex_skips_unchanged(library: DocumentLibrary, tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text("Some content here.", encoding="utf-8")
    assert library.index_file(doc) == 1
    assert library.index_file(doc) is None  # unchanged → skipped


def test_search_empty_query(library: DocumentLibrary) -> None:
    assert library.search("") == []
    assert library.search("   ") == []


def test_stats(library: DocumentLibrary, tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text("Hello world content.", encoding="utf-8")
    library.index_file(doc)
    stats = library.stats()
    assert stats.documents == 1
    assert stats.pages >= 1
    assert stats.size_bytes > 0


def test_list_documents(library: DocumentLibrary, tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text("Hello world content.", encoding="utf-8")
    library.index_file(doc)
    listing = library.list_documents()
    assert len(listing) == 1
    assert "notes.txt" in listing[0]["path"]


def test_remove_file(library: DocumentLibrary, tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text("Hello world content.", encoding="utf-8")
    library.index_file(doc)
    assert library.remove_file(str(doc)) is True
    assert library.stats().documents == 0


def test_download_streams_and_indexes(library: DocumentLibrary, tmp_path: Path) -> None:
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Morning light resets the circadian clock.")
    payload = pdf.tobytes()
    pdf.close()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        result = DocumentResult(
            id="test:1",
            title="Downloaded Paper",
            source="test",
            pdf_url=f"http://127.0.0.1:{port}/paper.pdf",
            landing_url=f"http://127.0.0.1:{port}/paper",
            is_open_access=True,
        )
        path = asyncio.run(library.download(result, timeout_seconds=10))
        assert path.exists()
        assert path.read_bytes() == payload
        assert library.stats().documents == 1
    finally:
        server.shutdown()
        server.server_close()


def test_download_requires_url(library: DocumentLibrary) -> None:
    result = DocumentResult(id="x", title="No URL", source="test")
    with pytest.raises(ValueError):
        asyncio.run(library.download(result))
