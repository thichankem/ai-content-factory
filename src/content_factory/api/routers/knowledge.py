"""Knowledge base, chunking and grounded retrieval endpoints."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    File,
    UploadFile,
)

from ... import rag
from ...models import (
    Chunk,
    ChunkEdit,
    ChunkTemplate,
    KBAskRequest,
    KBAskResponse,
    KBCreate,
    KBDocument,
    KBIngestText,
    KBIngestUrl,
    KBUpdate,
    KnowledgeBase,
    RetrievalRequest,
    RetrievalResponse,
)
from ...service import ContentFactoryService
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post("/kb", response_model=KnowledgeBase)
    def create_kb(payload: KBCreate) -> KnowledgeBase:
        """Create a knowledge base with its chunking template."""
        return guard_value(lambda: service.create_kb(payload))

    @router.get("/kb", response_model=list[KnowledgeBase])
    def list_kbs() -> list[KnowledgeBase]:
        return service.list_kbs()

    @router.get("/kb/{kb_id}", response_model=KnowledgeBase)
    def get_kb(kb_id: str) -> KnowledgeBase:
        return guard_value(lambda: service.get_kb(kb_id))

    @router.patch("/kb/{kb_id}", response_model=KnowledgeBase)
    def update_kb(kb_id: str, payload: KBUpdate) -> KnowledgeBase:
        """Update settings; changing template/budget re-chunks every document."""
        return guard_value(lambda: service.update_kb(kb_id, payload))

    @router.delete("/kb/{kb_id}")
    def delete_kb(kb_id: str) -> dict[str, bool]:
        guard_value(lambda: service.delete_kb(kb_id))
        return {"deleted": True}

    @router.get("/kb/templates")
    def list_kb_templates() -> dict[str, str]:
        """Explain every chunk template (RAGFlow template picker)."""
        return {
            template.value: rag.describe_template(template)
            for template in ChunkTemplate
        }

    @router.post("/kb/{kb_id}/documents", response_model=KBDocument)
    def ingest_kb_text(kb_id: str, payload: KBIngestText) -> KBDocument:
        """Ingest raw text and cut it with the KB's template."""
        return guard_value(lambda: service.ingest_text(kb_id, payload))

    @router.post("/kb/{kb_id}/upload", response_model=KBDocument)
    async def ingest_kb_file(kb_id: str, file: UploadFile = File(...)) -> KBDocument:  # noqa: B008
        content = await file.read()
        return guard_value(
            lambda: service.ingest_file(kb_id, file.filename or "upload", content)
        )

    @router.get("/kb/{kb_id}/documents", response_model=list[KBDocument])
    def list_kb_documents(kb_id: str) -> list[KBDocument]:
        return guard_value(lambda: service.list_kb_documents(kb_id))

    @router.get("/kb/{kb_id}/chunks", response_model=list[Chunk])
    def list_kb_chunks(kb_id: str, document_id: str | None = None) -> list[Chunk]:
        """Chunk visualization for human review (RAGFlow's chunk view)."""
        return guard_value(lambda: service.list_chunks(kb_id, document_id))

    @router.patch("/kb/{kb_id}/chunks/{chunk_id}", response_model=Chunk)
    def edit_kb_chunk(kb_id: str, chunk_id: str, payload: ChunkEdit) -> Chunk:
        """Human intervention: edit text/heading, or split at char offsets."""
        return guard_value(lambda: service.edit_chunk(kb_id, chunk_id, payload))

    @router.post("/kb/{kb_id}/chunks/merge", response_model=Chunk)
    def merge_kb_chunks(kb_id: str, payload: list[str]) -> Chunk:
        """Merge consecutive chunks of the same document into one."""
        return guard_value(lambda: service.merge_chunks(kb_id, payload))

    @router.delete("/kb/{kb_id}/chunks/{chunk_id}")
    def delete_kb_chunk(kb_id: str, chunk_id: str) -> dict[str, bool]:
        guard_value(lambda: service.delete_chunk(kb_id, chunk_id))
        return {"deleted": True}

    @router.post("/kb/retrieve", response_model=RetrievalResponse)
    def retrieve_kb(
        payload: RetrievalRequest, kb_id: str | None = None
    ) -> RetrievalResponse:
        """Hybrid retrieval test (vector + BM25 + optional rerank)."""
        return guard_value(lambda: service.retrieve_kb(payload, kb_id))

    @router.post("/kb/{kb_id}/retrieve", response_model=RetrievalResponse)
    def retrieve_kb_scoped(kb_id: str, payload: RetrievalRequest) -> RetrievalResponse:
        """Hybrid retrieval scoped to one knowledge base."""
        return guard_value(lambda: service.retrieve_kb(payload, kb_id))

    @router.post("/kb/{kb_id}/ask", response_model=KBAskResponse)
    async def ask_kb(kb_id: str, payload: KBAskRequest) -> KBAskResponse:
        """NotebookLM-style grounded Q&A: answer with citations from the KB."""
        return await service.ask_kb(kb_id, payload)

    @router.post("/kb/{kb_id}/ingest-url", response_model=KBDocument)
    def ingest_kb_url(kb_id: str, payload: KBIngestUrl) -> KBDocument:
        """Ingest a web page as a source (NotebookLM web-source addition)."""
        return guard_value(lambda: service.ingest_url(kb_id, payload))

    return router
