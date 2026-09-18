"""RAGFlow-style knowledge base: chunks, retrieval and grounding."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import utcnow

# --- RAGFlow-style knowledge engine -------------------------------------------


class ChunkTemplate(enum.StrEnum):
    """Explainable chunking templates, ported from RAGFlow's parser catalogue.

    Each template knows how to cut a raw document into semantic chunks and can
    explain its decision — RAGFlow's core promise of *intelligent and
    explainable* chunking.
    """

    NAIVE = "naive"  # fixed-token windows with overlap; works on anything
    QA = "qa"  # Q&A pairs, one chunk per pair
    RESUME = "resume"  # contact / experience / education blocks
    PAPER = "paper"  # abstract, sections, figure captions
    BOOK = "book"  # chapters and hierarchical headings
    LAWS = "laws"  # articles, clauses, and sub-clauses
    PRESENTATION = "presentation"  # slide-per-chunk with title + bullets
    ONE = "one"  # whole document as a single chunk


# Historical alias for external callers.
ChunkingMethod = ChunkTemplate


class KnowledgeBase(BaseModel):
    """A named collection of documents chunked with a shared template."""

    id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    template: ChunkTemplate = ChunkTemplate.NAIVE
    # Chunking budget: target tokens per chunk and the overlap between
    # consecutive windows (naive-family templates only).
    chunk_tokens: int = Field(default=256, ge=64, le=2048)
    chunk_overlap: int = Field(default=48, ge=0, le=512)
    language: str = ""
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class KBDocumentStatus(enum.StrEnum):
    """Lifecycle of one document inside a knowledge base."""

    QUEUED = "queued"
    PARSED = "parsed"
    FAILED = "failed"


class KBDocument(BaseModel):
    """One ingested document and how it was cut into chunks."""

    id: str
    kb_id: str
    name: str
    source_type: str = "text"
    status: KBDocumentStatus = KBDocumentStatus.PARSED
    template: ChunkTemplate = ChunkTemplate.NAIVE
    tokens: int = 0
    chunk_count: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Chunk(BaseModel):
    """One retrievable piece of knowledge with visual, editable metadata."""

    id: str
    kb_id: str
    document_id: str
    document_name: str
    index: int
    text: str
    token_count: int = 0
    # Template-specific structural labels ("Question", "Article 5", "Slide 3",
    # "Abstract", ...) so the UI can *visualize* the chunking for review.
    kind: str = "text"
    heading: str = ""
    page: int | None = None
    # Human intervention bookkeeping.
    edited: bool = False
    available_interventions: list[str] = Field(
        default_factory=lambda: ["edit", "split", "merge", "delete"]
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RetrievalHit(BaseModel):
    """One retrieved chunk with traceable retrieval scores."""

    chunk_id: str
    kb_id: str
    document_id: str
    document_name: str
    index: int
    text: str
    heading: str = ""
    kind: str = "text"
    # RAGFlow-style dual scores: semantic similarity and keyword (BM25) match,
    # plus the fused rank the reranker produced.
    vector_score: float = 0.0
    keyword_score: float = 0.0
    fused_score: float = 0.0
    rank: int = 0


class GroundingBundle(BaseModel):
    """The retrieved context handed to a model, with citations.

    Every claim the script makes can be traced back to one of these chunks —
    RAGFlow's grounded-citations promise applied to video scripts.
    """

    query: str
    kb_id: str | None = None
    hits: list[RetrievalHit] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    context_text: str = ""
    generated_at: datetime = Field(default_factory=utcnow)


class KBCreate(BaseModel):
    """Payload for creating a knowledge base."""

    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    template: ChunkTemplate = ChunkTemplate.NAIVE
    chunk_tokens: int = Field(default=256, ge=64, le=2048)
    chunk_overlap: int = Field(default=48, ge=0, le=512)
    language: str = ""


class KBUpdate(BaseModel):
    """Payload for updating a knowledge base's settings."""

    name: str | None = None
    description: str | None = None
    template: ChunkTemplate | None = None
    chunk_tokens: int | None = Field(default=None, ge=64, le=2048)
    chunk_overlap: int | None = Field(default=None, ge=0, le=512)
    language: str | None = None


class KBIngestText(BaseModel):
    """Payload for ingesting raw text into a knowledge base."""

    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    source_type: str = "text"


class KBIngestUrl(BaseModel):
    """Ingest a web page as a source (NotebookLM lets you add web sources)."""

    url: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=200)


class KBTurn(BaseModel):
    """One prior exchange in a NotebookLM-style grounded conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class KBAskRequest(BaseModel):
    """Ask a grounded question against one knowledge base.

    ``history`` carries the prior turns of the same conversation so follow-up
    questions keep their context, exactly like NotebookLM's chat.
    """

    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)
    use_vector: bool = True
    use_keywords: bool = True
    rerank: bool = True
    history: list[KBTurn] = Field(default_factory=list)


class KBAskResponse(BaseModel):
    """A grounded answer with traceable citations (NotebookLM-style).

    ``grounded`` is True when the answer was synthesized by a real LLM from the
    retrieved context, and False when the offline extractive fallback was used
    (no provider available). Either way every claim maps to ``citations``.
    """

    query: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    hits: list[RetrievalHit] = Field(default_factory=list)
    provider: str = "template"
    grounded: bool = True
    generated_at: datetime = Field(default_factory=utcnow)


class ChunkEdit(BaseModel):
    """Human interventions on a chunk (RAGFlow's "visualization + intervention")."""

    text: str | None = None
    heading: str | None = None
    split_at_chars: list[int] | None = None


class RetrievalRequest(BaseModel):
    """Payload for testing retrieval against one or all knowledge bases."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)
    use_vector: bool = True
    use_keywords: bool = True
    rerank: bool = True
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class GroundRequest(BaseModel):
    """Payload for a project grounding pass (retrieve + attach context)."""

    query: str | None = None
    top_k: int = Field(default=6, ge=1, le=50)


class RetrievalResponse(BaseModel):
    """Result of a retrieval test call."""

    query: str
    top_k: int
    hits: list[RetrievalHit] = Field(default_factory=list)
    kb_scanned: int = 0
    generated_at: datetime = Field(default_factory=utcnow)
