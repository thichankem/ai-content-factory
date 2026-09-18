"""Research sources, documents and local library search results."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

from .common import utcnow


class ResearchSource(BaseModel):
    """A single reference source gathered during research."""

    id: str
    title: str
    url: str
    source_type: str
    summary: str
    highlights: list[str] = Field(default_factory=list)
    relevance: float = 0.0


class ResearchBundle(BaseModel):
    """The result of a research pass: sources plus distilled key facts.

    ``topic`` echoes the subject the pass was run for. The sources already imply
    it, but a client labelling a bundle should not need a second lookup.
    """

    topic: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    notes: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)


class DocumentResult(BaseModel):
    """A search hit from a document provider (arXiv, Crossref, ...)."""

    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    source: str = ""
    doi: str | None = None
    pdf_url: str | None = None
    landing_url: str | None = None
    venue: str | None = None
    citations: int | None = None
    is_open_access: bool = False
    score: float = 1.0

    def to_bibtex(self) -> str:
        """Render a BibTeX entry for reference managers."""
        first_author = "Unknown"
        if self.authors:
            parts = self.authors[0].strip().split()
            first_author = re.sub(r"[^A-Za-z0-9]", "", parts[-1]) if parts else "Author"
        words = [w for w in re.findall(r"[A-Za-z0-9]+", self.title) if len(w) > 3]
        first_word = words[0].lower() if words else "document"
        cite_key = f"{first_author.lower()}{self.year or 'nodate'}{first_word}"
        author_str = " and ".join(self.authors) if self.authors else "Anonymous"
        lines = [
            f"@article{{{cite_key},",
            f"  title = {{{{{self.title}}}}},",
            f"  author = {{{author_str}}},",
        ]
        if self.year:
            lines.append(f"  year = {{{self.year}}},")
        if self.venue:
            lines.append(f"  journal = {{{self.venue}}},")
        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")
        if self.pdf_url or self.landing_url:
            lines.append(f"  url = {{{self.pdf_url or self.landing_url}}},")
        lines.append("}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render a rich Markdown summary card."""
        authors = ", ".join(self.authors[:5])
        if len(self.authors) > 5:
            authors += f" et al. ({len(self.authors)} total)"
        year = f" ({self.year})" if self.year else ""
        citations = (
            f" | {self.citations} citations" if self.citations is not None else ""
        )
        oa = " [Open Access]" if self.is_open_access else ""
        lines = [f"### [{self.title}]({self.landing_url or self.pdf_url or '#'})"]
        lines.append(f"**Authors:** {authors}{year}{citations}{oa}")
        if self.venue:
            lines.append(f"**Venue:** *{self.venue}* | **Source:** `{self.source}`")
        if self.pdf_url:
            lines.append(f"**PDF:** {self.pdf_url}")
        if self.abstract:
            abstract = self.abstract.strip()
            if len(abstract) > 350:
                abstract = abstract[:347] + "..."
            lines.append(f"> {abstract}")
        return "\n".join(lines)


class DocumentRef(BaseModel):
    """A document attached to a project and stored in the local library."""

    id: str
    title: str
    source: str
    doi: str | None = None
    url: str | None = None
    pdf_path: str | None = None
    added_at: datetime = Field(default_factory=utcnow)


class LibraryHit(BaseModel):
    """A ranked full-text match inside the local document library."""

    path: str
    title: str
    page: int
    snippet: str
    score: float


class LibraryStats(BaseModel):
    """Coverage statistics for the local document library."""

    database: str
    fts5: bool
    documents: int
    pages: int
    size_bytes: int
