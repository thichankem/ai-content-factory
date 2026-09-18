"""RAGFlow-style knowledge bases: chunking, retrieval and grounding."""

from __future__ import annotations

import itertools
import re
import uuid
from pathlib import Path

from .. import rag
from ..models import (
    Chunk,
    ChunkEdit,
    GroundRequest,
    KBCreate,
    KBDocument,
    KBDocumentStatus,
    KBIngestText,
    KBUpdate,
    KnowledgeBase,
    Project,
    RetrievalRequest,
    RetrievalResponse,
    utcnow,
)
from ..rag import KnowledgeRetriever
from .context import ServiceContext
from .errors import (
    NotFoundError,
    StateConflictError,
)


class KnowledgeMixin(ServiceContext):
    """RAGFlow-style knowledge bases: chunking, retrieval and grounding."""

    # --- Knowledge engine (RAGFlow-style) -------------------------------------

    def create_kb(self, data: KBCreate) -> KnowledgeBase:
        """Create a knowledge base with a chunking template."""
        kb = KnowledgeBase(
            id=uuid.uuid4().hex[:12],
            name=data.name,
            description=data.description,
            template=data.template,
            chunk_tokens=data.chunk_tokens,
            chunk_overlap=data.chunk_overlap,
            language=data.language,
        )
        self._kbs[kb.id] = kb
        return kb

    def list_kbs(self) -> list[KnowledgeBase]:
        return sorted(self._kbs.values(), key=lambda kb: kb.created_at)

    def get_kb(self, kb_id: str) -> KnowledgeBase:
        kb = self._kbs.get(kb_id)
        if kb is None:
            raise NotFoundError(f"No knowledge base '{kb_id}'.")
        return kb

    def update_kb(self, kb_id: str, data: KBUpdate) -> KnowledgeBase:
        """Update KB settings; changing the template re-chunks everything."""
        kb = self.get_kb(kb_id)
        changed_template = data.template is not None and data.template != kb.template
        changed_budget = (
            data.chunk_tokens is not None and data.chunk_tokens != kb.chunk_tokens
        ) or (data.chunk_overlap is not None and data.chunk_overlap != kb.chunk_overlap)
        if data.name is not None:
            kb.name = data.name
        if data.description is not None:
            kb.description = data.description
        if data.template is not None:
            kb.template = data.template
        if data.chunk_tokens is not None:
            kb.chunk_tokens = data.chunk_tokens
        if data.chunk_overlap is not None:
            kb.chunk_overlap = data.chunk_overlap
        if data.language is not None:
            kb.language = data.language
        kb.updated_at = utcnow()
        if changed_template or changed_budget:
            self._rechunk_kb(kb)
        return kb

    def delete_kb(self, kb_id: str) -> None:
        self.get_kb(kb_id)
        doc_ids = [d.id for d in self._kb_documents.values() if d.kb_id == kb_id]
        for doc_id in doc_ids:
            self._kb_documents.pop(doc_id, None)
        for chunk_id in [
            c for c, chunk in self._chunks.items() if chunk.kb_id == kb_id
        ]:
            self._chunks.pop(chunk_id, None)
        # Detach from projects.
        for project in self._store.list():
            if project.knowledge_base_id == kb_id:
                project.knowledge_base_id = None
                self._store.save(project)
        self._kbs.pop(kb_id, None)
        self._sync_retriever()

    def _sync_retriever(self) -> None:
        self._retriever.replace_all(list(self._chunks.values()))

    def _rechunk_kb(self, kb: KnowledgeBase) -> None:
        """Re-run the template over every document's source text."""
        doc_ids = [d.id for d in self._kb_documents.values() if d.kb_id == kb.id]
        sources: dict[str, str] = {}
        for doc_id in doc_ids:
            doc_chunks = [c for c in self._chunks.values() if c.document_id == doc_id]
            if doc_chunks:
                sources[doc_id] = "\n\n".join(c.text for c in doc_chunks)
        for doc_id, text in sources.items():
            self._chunk_and_store(kb, doc_id, text)
        self._refresh_kb_counts(kb)
        self._sync_retriever()

    def ingest_text(self, kb_id: str, data: KBIngestText) -> KBDocument:
        """Ingest raw text: chunk with the template, index for retrieval."""
        kb = self.get_kb(kb_id)
        doc = KBDocument(
            id=uuid.uuid4().hex[:12],
            kb_id=kb.id,
            name=data.title,
            source_type=data.source_type,
            template=kb.template,
        )
        self._kb_documents[doc.id] = doc
        try:
            self._chunk_and_store(kb, doc.id, data.text)
            doc.status = KBDocumentStatus.PARSED
        except Exception as err:  # noqa: BLE001 - a failed parse is recorded on the document as FAILED
            doc.status = KBDocumentStatus.FAILED
            doc.error = str(err)
        self._refresh_kb_counts(kb)
        self._sync_retriever()
        return doc

    def ingest_file(self, kb_id: str, filename: str, content: bytes) -> KBDocument:
        """Ingest an uploaded file (txt/md/csv/html supported like library)."""
        suffix = Path(filename or "upload.txt").suffix.lower()
        if suffix not in (".txt", ".md", ".markdown", ".rst", ".csv", ".html", ".htm"):
            raise StateConflictError(
                f"Unsupported knowledge file type '{suffix}'. Use txt/md/csv/html."
            )
        text = content.decode("utf-8", errors="ignore")
        if suffix in (".html", ".htm"):
            text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
            text = re.sub(r"<[^>]+>", " ", text)
        return self.ingest_text(
            kb_id,
            KBIngestText(
                title=Path(filename).stem or "upload",
                text=text,
                source_type="file",
            ),
        )

    def _chunk_and_store(self, kb: KnowledgeBase, doc_id: str, text: str) -> None:
        """Cut text with the KB template and persist the chunks."""
        raw_chunks = rag.chunk_document(
            text,
            template=kb.template,
            chunk_tokens=kb.chunk_tokens,
            overlap=kb.chunk_overlap,
        )
        if not raw_chunks:
            raise StateConflictError("No extractable text to chunk.")
        # Drop previous chunks of this document (re-ingest / re-chunk).
        for chunk_id in [
            c for c, chunk in self._chunks.items() if chunk.document_id == doc_id
        ]:
            self._chunks.pop(chunk_id, None)
        doc = self._kb_documents.get(doc_id)
        doc_name = doc.name if doc else doc_id
        for index, raw in enumerate(raw_chunks):
            clean = raw.clean()
            chunk = Chunk(
                id=f"{doc_id[:6]}-{index:04d}",
                kb_id=kb.id,
                document_id=doc_id,
                document_name=doc_name,
                index=index,
                text=clean,
                token_count=rag.count_tokens(clean),
                kind=raw.kind,
                heading=raw.heading,
            )
            self._chunks[chunk.id] = chunk
        if doc is not None:
            doc.chunk_count = len(raw_chunks)
            doc.tokens = sum(rag.count_tokens(raw.clean()) for raw in raw_chunks)
            doc.template = kb.template

    def _refresh_kb_counts(self, kb: KnowledgeBase) -> None:
        kb.document_count = sum(
            1 for d in self._kb_documents.values() if d.kb_id == kb.id
        )
        kb.chunk_count = sum(1 for c in self._chunks.values() if c.kb_id == kb.id)
        kb.updated_at = utcnow()

    def list_kb_documents(self, kb_id: str) -> list[KBDocument]:
        self.get_kb(kb_id)
        return sorted(
            (d for d in self._kb_documents.values() if d.kb_id == kb_id),
            key=lambda d: d.created_at,
        )

    def list_chunks(self, kb_id: str, document_id: str | None = None) -> list[Chunk]:
        """Visualize chunks for review (RAGFlow's chunk visualization)."""
        self.get_kb(kb_id)
        chunks = [
            c
            for c in self._chunks.values()
            if c.kb_id == kb_id
            and (document_id is None or c.document_id == document_id)
        ]
        return sorted(chunks, key=lambda c: (c.document_id, c.index))

    def edit_chunk(self, kb_id: str, chunk_id: str, data: ChunkEdit) -> Chunk:
        """Human intervention on one chunk: edit text or split it in two."""
        self.get_kb(kb_id)
        chunk = self._chunks.get(chunk_id)
        if chunk is None or chunk.kb_id != kb_id:
            raise NotFoundError(f"No chunk '{chunk_id}'.")
        if data.split_at_chars:
            return self._split_chunk(chunk, data.split_at_chars)
        if data.text is not None:
            clean = data.text.strip()
            if not clean:
                raise StateConflictError("Chunk text cannot be empty.")
            chunk.text = clean
            chunk.token_count = rag.count_tokens(clean)
        if data.heading is not None:
            chunk.heading = data.heading.strip()
        chunk.edited = True
        chunk.updated_at = utcnow()
        self._sync_retriever()
        return chunk

    def _split_chunk(self, chunk: Chunk, split_at_chars: list[int]) -> Chunk:
        """Split one chunk at character offsets into sequential chunks."""
        text = chunk.text
        offsets = sorted({o for o in split_at_chars if 0 < o < len(text)})
        if not offsets:
            raise StateConflictError("Split offsets must be inside the chunk text.")
        bounds = [0, *offsets, len(text)]
        parts = [text[a:b].strip() for a, b in itertools.pairwise(bounds)]
        parts = [p for p in parts if p]
        if len(parts) < 2:
            raise StateConflictError(
                "Split produced a single piece; choose offsets inside the text."
            )
        # First part stays in this chunk; the rest become new chunks.
        chunk.text = parts[0]
        chunk.token_count = rag.count_tokens(parts[0])
        chunk.edited = True
        chunk.updated_at = utcnow()
        for extra_index, part in enumerate(parts[1:], start=1):
            new_id = f"{chunk.id}-{extra_index}"
            self._chunks[new_id] = Chunk(
                id=new_id,
                kb_id=chunk.kb_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                index=chunk.index + extra_index,
                text=part,
                token_count=rag.count_tokens(part),
                kind=chunk.kind,
                heading=chunk.heading,
                edited=True,
            )
        self._sync_retriever()
        kb = self._kbs.get(chunk.kb_id)
        if kb:
            self._refresh_kb_counts(kb)
        return chunk

    def merge_chunks(self, kb_id: str, chunk_ids: list[str]) -> Chunk:
        """Merge 2+ consecutive chunks of the same document into one."""
        self.get_kb(kb_id)
        chunks = []
        for cid in chunk_ids:
            chunk = self._chunks.get(cid)
            if chunk is None or chunk.kb_id != kb_id:
                raise NotFoundError(f"No chunk '{cid}'.")
            chunks.append(chunk)
        chunks.sort(key=lambda c: c.index)
        documents = {c.document_id for c in chunks}
        if len(documents) != 1:
            raise StateConflictError("Can only merge chunks of the same document.")
        merged_text = "\n".join(c.text for c in chunks)
        first = chunks[0]
        first.text = merged_text
        first.token_count = rag.count_tokens(merged_text)
        first.edited = True
        first.updated_at = utcnow()
        for chunk in chunks[1:]:
            self._chunks.pop(chunk.id, None)
        self._sync_retriever()
        kb = self._kbs.get(kb_id)
        if kb:
            self._refresh_kb_counts(kb)
        return first

    def delete_chunk(self, kb_id: str, chunk_id: str) -> None:
        self.get_kb(kb_id)
        chunk = self._chunks.get(chunk_id)
        if chunk is None or chunk.kb_id != kb_id:
            raise NotFoundError(f"No chunk '{chunk_id}'.")
        self._chunks.pop(chunk_id, None)
        self._sync_retriever()
        kb = self._kbs.get(kb_id)
        if kb:
            self._refresh_kb_counts(kb)

    def retrieve_kb(
        self, request: RetrievalRequest, kb_id: str | None = None
    ) -> RetrievalResponse:
        """Test hybrid retrieval across one KB or all of them."""
        if kb_id is not None:
            self.get_kb(kb_id)
        retriever = self._retriever
        if kb_id is not None:
            scoped = KnowledgeRetriever()
            scoped.replace_all([c for c in self._chunks.values() if c.kb_id == kb_id])
            retriever = scoped
        hits = retriever.retrieve(
            request.query,
            top_k=request.top_k,
            use_vector=request.use_vector,
            use_keywords=request.use_keywords,
            rerank=request.rerank,
            similarity_threshold=request.similarity_threshold,
        )
        return RetrievalResponse(
            query=request.query,
            top_k=request.top_k,
            hits=hits,
            kb_scanned=1 if kb_id else len(self._kbs),
        )

    def attach_kb(self, project_id: str, kb_id: str | None) -> Project:
        """Attach or detach a knowledge base to/from a project."""
        project = self.get_project(project_id)
        if kb_id is not None:
            self.get_kb(kb_id)
        project.knowledge_base_id = kb_id
        return self._store.save(project)

    def ground_project(self, project_id: str, data: GroundRequest) -> Project:
        """Retrieve knowledge for the topic and attach the citation bundle."""
        project = self.get_project(project_id)
        kb_id = project.knowledge_base_id
        query = (data.query or project.topic or project.name).strip()
        if not kb_id:
            raise StateConflictError(
                "No knowledge base attached. Create one and attach it first."
            )
        scoped = KnowledgeRetriever()
        scoped.replace_all([c for c in self._chunks.values() if c.kb_id == kb_id])
        hits = scoped.retrieve(query, top_k=data.top_k, rerank=self._settings.kb_rerank)
        project.grounding = rag.build_grounding(query, hits, kb_id=kb_id)
        return self._store.save(project)

    def _grounding_context(self, project: Project) -> str | None:
        """Grounded citation context for prompts, or None when absent."""
        if project.grounding and project.grounding.context_text:
            return project.grounding.context_text
        return None
