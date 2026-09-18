"""Federated document search across multiple public sources.

Ports the best ideas from the Scribd-Doc-Downloader-ToolKit: a unified result
type with rich metadata (DOI, PDF URL, citations, open-access), concurrent
multi-provider search, deduplication, and a zero-dependency lexical reranker
that scores phrase matches, term coverage, and bigram continuity while
penalizing off-topic single-word hits.

Every provider degrades gracefully: on any network or parsing error it returns
an empty list, so a dead source never breaks the whole search.
"""

from __future__ import annotations

import asyncio
import html as _html
import re
import time
import xml.etree.ElementTree as ET
from typing import Protocol

import httpx

from .config import Settings
from .models import DocumentResult
from .text import normalize_title as _normalize_title
from .text import tokenize

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "of",
        "for",
        "with",
        "on",
        "in",
        "to",
        "at",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "their",
        "his",
        "her",
        "our",
        "your",
        "about",
        "into",
        "how",
        "why",
        "what",
        "when",
        "where",
        "who",
        "which",
        "study",
        "research",
        "paper",
        "analysis",
    }
)


def _tokenize(text: str) -> list[str]:
    """Search tokenizer policy: drop one-letter words and English stopwords."""
    return tokenize(text, min_length=2, stopwords=STOPWORDS)


class LexicalReranker:
    """Zero-dependency relevance scorer for search results."""

    def rerank(self, query: str, results: list[DocumentResult]) -> list[DocumentResult]:
        scores = self._score(query, results)
        for result, score in zip(results, scores, strict=False):
            result.score = round(max(0.0, min(1.0, score)), 4)
        results.sort(
            key=lambda d: (
                -d.score,
                d.citations is None,
                -(d.citations or 0),
                (d.title or "").lower(),
            )
        )
        return results

    def _score(self, query: str, results: list[DocumentResult]) -> list[float]:
        q_clean = query.strip().lower()
        q_tokens = _tokenize(q_clean)
        q_set = set(q_tokens)
        q_len = len(q_set)
        if not q_len:
            return [1.0 for _ in results]

        q_bigrams = {(q_tokens[i], q_tokens[i + 1]) for i in range(len(q_tokens) - 1)}

        scores: list[float] = []
        for doc in results:
            title = (doc.title or "").lower()
            abstract = (doc.abstract or "").lower()
            t_set = set(_tokenize(title))
            a_set = set(_tokenize(abstract))

            phrase_bonus = 0.0
            if q_clean and len(q_clean) >= 6:
                if q_clean in title:
                    phrase_bonus = 0.45
                elif len(title) >= 10 and title in q_clean:
                    phrase_bonus = 0.40
                elif q_clean in abstract:
                    phrase_bonus = 0.20
                else:
                    q_words = q_clean.split()
                    for n in range(min(5, len(q_words)), 1, -1):
                        for i in range(len(q_words) - n + 1):
                            if " ".join(q_words[i : i + n]) in title:
                                phrase_bonus = max(phrase_bonus, 0.08 * n)
                        if phrase_bonus > 0:
                            break

            title_hits = q_set & t_set
            abstract_hits = q_set & a_set
            all_hits = title_hits | abstract_hits
            title_cov = len(title_hits) / q_len
            abstract_cov = len(abstract_hits) / q_len
            total_cov = len(all_hits) / q_len

            bigram_bonus = 0.0
            if q_bigrams:
                doc_words = _tokenize(f"{title} {abstract}")
                doc_bigrams = {
                    (doc_words[i], doc_words[i + 1]) for i in range(len(doc_words) - 1)
                }
                bigram_bonus = len(q_bigrams & doc_bigrams) / len(q_bigrams) * 0.15

            raw = (
                0.35 * total_cov
                + 0.35 * title_cov
                + 0.15 * abstract_cov
                + phrase_bonus
                + bigram_bonus
            )
            if total_cov < 0.50 and q_len >= 2:
                raw *= 0.40
            elif total_cov <= 0.50 and abstract_cov == 0 and q_len >= 2:
                raw *= 0.50
            scores.append(max(0.0, min(1.0, raw)))
        return scores


class DocumentProvider(Protocol):
    """Interface every search provider implements."""

    name: str

    async def search(self, query: str, limit: int) -> list[DocumentResult]: ...


class _HttpProvider:
    """Shared plumbing: timeout handling and graceful error swallowing."""

    name = "http"

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = httpx.Timeout(
            timeout_seconds, connect=min(5.0, timeout_seconds)
        )

    async def _get_json(self, url: str, params: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
        except Exception:
            return None

    async def _get_text(self, url: str, params: dict) -> str | None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.text
        except Exception:
            return None


class ArxivProvider(_HttpProvider):
    """arXiv API (export.arxiv.org) — papers with PDF links and abstracts.

    arXiv enforces a strict rate limit (about one request per three seconds),
    so this provider throttles itself and retries once when throttled.
    """

    name = "arxiv"
    MIN_INTERVAL = 3.2

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(timeout_seconds)
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def _throttled_fetch(self, query: str, limit: int) -> str | None:
        async with self._lock:
            await self._wait_if_needed()
            text = await self._get_text(
                "http://export.arxiv.org/api/query",
                {"search_query": f"all:{query}", "max_results": limit},
            )
            self._last_request = time.monotonic()
            if text is None or "Rate exceeded" in text:
                await asyncio.sleep(self.MIN_INTERVAL)
                text = await self._get_text(
                    "http://export.arxiv.org/api/query",
                    {"search_query": f"all:{query}", "max_results": limit},
                )
                self._last_request = time.monotonic()
            return text

    async def _wait_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.MIN_INTERVAL:
            await asyncio.sleep(self.MIN_INTERVAL - elapsed)

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        text = await self._throttled_fetch(query, limit)
        if not text:
            return []
        namespace = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        results: list[DocumentResult] = []
        for entry in root.findall("atom:entry", namespace):
            title = _clean_text(entry.findtext("atom:title", "", namespace))
            arxiv_id = (entry.findtext("atom:id", "", namespace) or "").rsplit(
                "/abs/", 1
            )[-1]
            authors = [
                _clean_text(node.findtext("atom:name", "", namespace))
                for node in entry.findall("atom:author", namespace)
            ]
            published = entry.findtext("atom:published", "", namespace)
            year = (
                int(published[:4])
                if len(published) >= 4 and published[:4].isdigit()
                else None
            )
            summary = _clean_text(entry.findtext("atom:summary", "", namespace))
            pdf_url = None
            for link in entry.findall("atom:link", namespace):
                if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                    break
            results.append(
                DocumentResult(
                    id=f"arxiv:{arxiv_id}",
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=summary,
                    source=self.name,
                    pdf_url=pdf_url,
                    landing_url=f"https://arxiv.org/abs/{arxiv_id}",
                    venue=None,
                    is_open_access=True,
                )
            )
        return results


class CrossrefProvider(_HttpProvider):
    """Crossref REST API — scholarly works with DOIs and citation counts."""

    name = "crossref"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://api.crossref.org/works",
            {
                "query": query,
                "rows": limit,
                "select": (
                    "DOI,title,author,issued,abstract,container-title,"
                    "is-referenced-by-count,URL,link"
                ),
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for item in data.get("message", {}).get("items", []):
            title = (item.get("title") or [""])[0]
            if not title:
                continue
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in item.get("author", [])
                if a.get("family")
            ]
            year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
            abstract = _strip_tags(item.get("abstract", ""))
            doi = item.get("DOI")
            pdf_url = None
            for link in item.get("link", []) or []:
                if link.get("content-type") == "application/pdf" or link.get(
                    "URL", ""
                ).endswith(".pdf"):
                    pdf_url = link.get("URL")
                    break
            results.append(
                DocumentResult(
                    id=f"crossref:{doi}",
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    source=self.name,
                    doi=doi,
                    pdf_url=pdf_url,
                    landing_url=item.get("URL")
                    or (f"https://doi.org/{doi}" if doi else None),
                    venue=(item.get("container-title") or [None])[0],
                    citations=item.get("is-referenced-by-count"),
                    is_open_access=bool(pdf_url),
                )
            )
        return results


class GutendexProvider(_HttpProvider):
    """Gutenberg via the Gutendex API — public-domain books."""

    name = "gutenberg"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json("https://gutendex.com/books", {"search": query})
        if not data:
            return []
        results: list[DocumentResult] = []
        for book in data.get("results", [])[:limit]:
            title = book.get("title", "")
            if not title:
                continue
            formats = book.get("formats", {})
            pdf_url = formats.get("application/pdf") or formats.get("text/html")
            ebook_id = book.get("id")
            authors = [
                a.get("name", "") for a in book.get("authors", []) if a.get("name")
            ]
            author_names = ", ".join(authors) or "unknown authors"
            results.append(
                DocumentResult(
                    id=f"gutenberg:{ebook_id}",
                    title=title,
                    authors=authors,
                    year=None,
                    abstract=f"Public-domain book by {author_names}.",
                    source=self.name,
                    pdf_url=pdf_url,
                    landing_url=f"https://www.gutenberg.org/ebooks/{ebook_id}",
                    venue=None,
                    citations=book.get("download_count"),
                    is_open_access=True,
                )
            )
        return results


class OpenLibraryProvider(_HttpProvider):
    """Open Library search API — books with editions and lending links."""

    name = "open-library"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://openlibrary.org/search.json", {"q": query, "limit": limit}
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for doc in data.get("docs", []):
            title = doc.get("title", "")
            if not title:
                continue
            key = doc.get("key")
            results.append(
                DocumentResult(
                    id=f"open-library:{key}",
                    title=title,
                    authors=doc.get("author_name", []) or [],
                    year=doc.get("first_publish_year"),
                    abstract=doc.get("first_sentence", [""])[0]
                    if doc.get("first_sentence")
                    else "",
                    source=self.name,
                    pdf_url=None,
                    landing_url=f"https://openlibrary.org{key}" if key else None,
                    venue=None,
                    citations=doc.get("ratings_count"),
                    is_open_access=False,
                )
            )
        return results


class WikipediaProvider(_HttpProvider):
    """Wikipedia search API — encyclopedia articles."""

    name = "wikipedia"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://en.wikipedia.org/w/api.php",
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": limit,
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for hit in data.get("query", {}).get("search", []):
            title = hit.get("title", "")
            if not title:
                continue
            snippet = _strip_tags(hit.get("snippet", ""))
            slug = re.sub(r"\s+", "_", title)
            results.append(
                DocumentResult(
                    id=f"wikipedia:{_normalize_title(title)}",
                    title=title,
                    authors=[],
                    year=None,
                    abstract=snippet,
                    source=self.name,
                    pdf_url=None,
                    landing_url=f"https://en.wikipedia.org/wiki/{slug}",
                    venue=None,
                    is_open_access=True,
                )
            )
        return results


class InternetArchiveProvider(_HttpProvider):
    """Internet Archive advanced search — scanned books and documents."""

    name = "internet-archive"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://archive.org/advancedsearch.php",
            {
                "q": query,
                "fl[]": ["identifier", "title", "creator", "year", "description"],
                "rows": limit,
                "output": "json",
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for doc in data.get("response", {}).get("docs", []):
            identifier = doc.get("identifier")
            if not identifier:
                continue
            title = doc.get("title") or identifier
            creators = doc.get("creator", [])
            if isinstance(creators, str):
                creators = [creators]
            description = doc.get("description", "")
            if isinstance(description, list):
                description = " ".join(str(d) for d in description)
            results.append(
                DocumentResult(
                    id=f"internet-archive:{identifier}",
                    title=str(title),
                    authors=[str(c) for c in creators],
                    year=doc.get("year"),
                    abstract=str(description)[:600],
                    source=self.name,
                    pdf_url=f"https://archive.org/download/{identifier}/{identifier}.pdf",
                    landing_url=f"https://archive.org/details/{identifier}",
                    venue=None,
                    is_open_access=True,
                )
            )
        return results


class WikimediaCommonsProvider(_HttpProvider):
    """Wikimedia Commons API — public domain archival photos and media."""

    name = "wikimedia-commons"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://commons.wikimedia.org/w/api.php",
            {
                "action": "query",
                "list": "search",
                "srsearch": f"{query} filetype:bitmap|drawing",
                "srnamespace": "6",  # File: namespace
                "format": "json",
                "srlimit": limit,
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for hit in data.get("query", {}).get("search", []):
            title = hit.get("title", "")
            if not title:
                continue
            clean_title = re.sub(r"^File:", "", title)
            snippet = _strip_tags(hit.get("snippet", ""))
            slug = re.sub(r"\s+", "_", title)
            results.append(
                DocumentResult(
                    id=f"wikimedia:{_normalize_title(clean_title)}",
                    title=clean_title,
                    authors=["Public Domain / CC Contributor"],
                    year=None,
                    abstract=snippet
                    or f"Archival historical visual asset for {clean_title}",
                    source=self.name,
                    pdf_url=None,
                    landing_url=f"https://commons.wikimedia.org/wiki/{slug}",
                    venue="Wikimedia Commons Archive",
                    is_open_access=True,
                )
            )
        return results


class ChroniclingAmericaProvider(_HttpProvider):
    """Library of Congress Chronicling America — historic newspapers 1777-1963."""

    name = "chronicling-america"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        data = await self._get_json(
            "https://chroniclingamerica.loc.gov/search/pages/results/",
            {
                "andtext": query,
                "format": "json",
                "rows": limit,
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for item in data.get("items", []):
            paper_title = (
                item.get("title_normal")
                or item.get("newspaper_title")
                or "Historic Newspaper"
            )
            date = item.get("date", "")
            year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
            ocr_text = item.get("ocr_eng", "") or ""
            city = item.get("city", [""])[0] if item.get("city") else ""
            state = item.get("state", [""])[0] if item.get("state") else ""
            venue = (
                f"{city}, {state}".strip(", ")
                if (city or state)
                else "Historic Newspaper Press"
            )
            page_url = f"https://chroniclingamerica.loc.gov{item.get('id', '')}"
            pdf_url = f"{page_url}.pdf" if item.get("id") else None

            snippet = _clean_text(ocr_text[:400])
            results.append(
                DocumentResult(
                    id=(
                        f"chronicling:{item.get('sequence', 0)}"
                        f"_{_normalize_title(paper_title)}"
                    ),
                    title=f"{paper_title} ({date or 'Archival Edition'})",
                    authors=[venue],
                    year=year,
                    abstract=snippet
                    or f"Original newspaper dispatch covering {query}.",
                    source=self.name,
                    pdf_url=pdf_url,
                    landing_url=page_url,
                    venue=venue,
                    is_open_access=True,
                )
            )
        return results


class USGSEarthquakeProvider(_HttpProvider):
    """USGS Earthquake Hazards API — historical seismic & geological disaster events."""

    name = "usgs-earthquakes"

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        # Filter for historical seismic significance if the query relates
        # to earthquakes/seismic
        if not re.search(
            r"earthquake|động đất|tsunami|sóng thần|seismic|richter",
            query,
            re.IGNORECASE,
        ):
            return []
        data = await self._get_json(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            {
                "format": "geojson",
                "minmagnitude": "6.5",
                "limit": limit,
                "orderby": "magnitude",
            },
        )
        if not data:
            return []
        results: list[DocumentResult] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            place = props.get("place", "Seismic Region")
            mag = props.get("mag", 0.0)
            time_ms = props.get("time", 0)
            year = time.gmtime(time_ms / 1000).tm_year if time_ms else None
            url = props.get("url")
            results.append(
                DocumentResult(
                    id=f"usgs:{feature.get('id', place)}",
                    title=f"M{mag} Major Earthquake — {place}",
                    authors=["USGS National Earthquake Information Center"],
                    year=year,
                    abstract=(
                        f"Magnitude {mag} seismic catastrophe recorded at "
                        f"{place}. Tsunami alert: {props.get('tsunami', 0)}. "
                        f"Significance score: {props.get('sig', 0)}."
                    ),
                    source=self.name,
                    pdf_url=None,
                    landing_url=url,
                    venue="USGS Global Seismic Network",
                    is_open_access=True,
                )
            )
        return results


def build_providers(settings: Settings) -> list[DocumentProvider]:
    """Construct the enabled provider list from settings."""
    if not settings.documents_web_enabled:
        return []
    timeout = settings.documents_search_timeout_seconds
    return [
        ArxivProvider(timeout),
        CrossrefProvider(timeout),
        GutendexProvider(timeout),
        OpenLibraryProvider(timeout),
        WikipediaProvider(timeout),
        InternetArchiveProvider(timeout),
        WikimediaCommonsProvider(timeout),
        ChroniclingAmericaProvider(timeout),
        USGSEarthquakeProvider(timeout),
    ]


class FederatedSearcher:
    """Runs all providers concurrently, merges, dedupes, and reranks."""

    def __init__(
        self, providers: list[DocumentProvider], reranker: LexicalReranker | None = None
    ) -> None:
        self._providers = providers
        self._reranker = reranker or LexicalReranker()

    @property
    def sources(self) -> list[str]:
        return [provider.name for provider in self._providers]

    async def search(self, query: str, limit: int = 10) -> list[DocumentResult]:
        if not self._providers:
            return []
        chunks = await asyncio.gather(
            *(provider.search(query, limit) for provider in self._providers),
            return_exceptions=True,
        )
        merged: list[DocumentResult] = []
        for chunk in chunks:
            if isinstance(chunk, list):
                merged.extend(chunk)
        deduped = self._dedupe(merged)
        return self._reranker.rerank(query, deduped)[: max(1, limit)]

    def _dedupe(self, results: list[DocumentResult]) -> list[DocumentResult]:
        seen: set[str] = set()
        deduped: list[DocumentResult] = []
        for result in results:
            key = _normalize_title(result.title)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(result)
        return deduped


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _strip_tags(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", _html.unescape(cleaned)).strip()
