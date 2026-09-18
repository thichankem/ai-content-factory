"""Research passes, document ingestion and local library search."""

from __future__ import annotations

from ..models import (
    DocumentRef,
    DocumentResult,
    LibraryHit,
    LibraryStats,
    Project,
    ResearchSource,
)
from ..text import normalize_title
from .context import ServiceContext


class ResearchMixin(ServiceContext):
    """Research passes, document ingestion and local library search."""

    async def research(self, project_id: str, include_web: bool = True) -> Project:
        """Run a research pass: curated library plus federated web sources."""
        project = self.get_project(project_id)
        bundle = self._research.research(project.topic)
        if include_web and self._settings.documents_web_enabled:
            try:
                web = await self._searcher.search(
                    project.topic, limit=self._settings.research_max_sources
                )
            except Exception:
                web = []
            for result in web:
                if len(bundle.sources) >= self._settings.research_max_sources + 2:
                    break
                if any(
                    normalize_title(source.title) == normalize_title(result.title)
                    for source in bundle.sources
                ):
                    continue
                bundle.sources.append(
                    ResearchSource(
                        id=result.id,
                        title=result.title,
                        url=result.landing_url or result.pdf_url or "",
                        source_type=result.source,
                        summary=(result.abstract or result.title)[:300],
                        highlights=[result.abstract[:400]] if result.abstract else [],
                        relevance=round(result.score, 2),
                    )
                )
        project.research = bundle
        return self._store.save(project)

    async def search_documents(
        self, query: str, limit: int = 10
    ) -> list[DocumentResult]:
        """Federated search across all enabled document providers."""
        return await self._searcher.search(query, limit=limit)

    async def add_document(self, project_id: str, result: DocumentResult) -> Project:
        """Download a document into the library, index it, and attach it."""
        project = self.get_project(project_id)
        path = await self._library.download(
            result, timeout_seconds=self._settings.http_timeout_seconds
        )
        project.documents.append(
            DocumentRef(
                id=result.id,
                title=result.title,
                source=result.source,
                doi=result.doi,
                url=result.landing_url or result.pdf_url,
                pdf_path=str(path),
            )
        )
        return self._store.save(project)

    def search_library(self, query: str, limit: int = 20) -> list[LibraryHit]:
        """Full-text BM25 search across downloaded documents."""
        return self._library.search(query, limit=limit)

    def list_library(self, limit: int = 100) -> list[dict]:
        return self._library.list_documents(limit=limit)

    def library_stats(self) -> LibraryStats:
        return self._library.stats()
