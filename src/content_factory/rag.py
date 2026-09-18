"""RAGFlow-style knowledge engine: chunking, hybrid retrieval, grounding.

Ported concepts from `infiniflow/ragflow` (Apache-2.0), adapted to this
project's zero-heavy-dependency architecture:

* **Template-based chunking** — eight explainable templates (:class:`ChunkTemplate`)
  that cut raw text into semantic units and label every unit (``Q&A``,
  ``Article 3``, ``Slide 2``, ``Abstract``) so the UI can visualize the cut
  and a human can intervene before anything is indexed.
* **Hybrid retrieval** — every chunk gets a lightweight hashed embedding (a
  bag-of-character-n-grams projected through signed hashes, the same idea as
  RAGFlow's vector store but dependency-free) plus a BM25 lexical index.
  Both channels are retrieved in parallel and fused with **Reciprocal Rank
  Fusion** (RRF), then optionally re-ranked by token overlap — RAGFlow's
  "multiple recall paired with fused re-ranking".
* **Grounded citations** — :class:`GroundingBundle` turns retrieved chunks
  into numbered, traceable citations that flow into the script prompt, the
  external-agent brief, and the copy-risk linter, so every claim in the
  final video can be traced back to a source chunk.

Everything is pure Python + stdlib, synchronous where it can be, and tested
directly.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from hashlib import blake2b

from .models import Chunk, ChunkTemplate, GroundingBundle, RetrievalHit
from .text import word_tokens

# --- Tokenization ---------------------------------------------------------------


#: Sentence terminator split for long-paragraph fallback (Latin + CJK).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…。！？])\s+")

#: Simple, deterministic token count used for chunk budgets and stats. Good
#: enough for budgeting; not a model tokenizer, and intentionally so.
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]|\S")


def count_tokens(text: str) -> int:
    """Approximate token count: words + CJK chars + other glyphs."""
    if not text:
        return 0
    return len(_TOKEN_RE.findall(text))


def _tokens(text: str) -> list[str]:
    """Unicode-aware tokens, so non-English words survive intact."""
    return word_tokens(text)


# --- Character n-gram hashing embedder -----------------------------------------------

_DIM = 512


def _hash_ngrams(text: str, n_min: int, n_max: int) -> Iterable[tuple[int, float]]:
    """Yield (bucket index, ±1) for character n-grams of normalized text."""
    norm = unicodedata.normalize("NFKC", (text or "")).lower()
    norm = re.sub(r"\s+", " ", norm).strip()
    if not norm:
        return
    for size in range(n_min, n_max + 1):
        for i in range(0, max(0, len(norm) - size + 1)):
            gram = norm[i : i + size]
            digest = blake2b(gram.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest, "little") % _DIM
            sign = 1.0 if digest[0] & 1 else -1.0
            yield bucket, sign


def embed_text(text: str) -> list[float]:
    """Deterministic hashed embedding of a text (unit length).

    Works for any language — including tone-marked Vietnamese — with zero
    dependencies and no model download. Swap for an API embedder later by
    replacing this function only; retrieval math stays identical.
    """
    vec = [0.0] * _DIM
    for bucket, sign in _hash_ngrams(text, 2, 4):
        vec[bucket] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


# --- BM25 over chunk texts -----------------------------------------------------------


class BM25Index:
    """Minimal BM25 (Okapi) index over chunk texts — rebuilt on demand."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._docs: list[list[str]] = []
        self._df: dict[str, int] = {}
        self._avgdl: float = 0.0

    def rebuild(self, texts: Sequence[str]) -> None:
        self._docs = [_tokens(t) for t in texts]
        self._df = {}
        for doc in self._docs:
            for term in set(doc):
                self._df[term] = self._df.get(term, 0) + 1
        total = sum(len(d) for d in self._docs)
        self._avgdl = (total / len(self._docs)) if self._docs else 0.0

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Return ``(chunk_position, score)`` for the top_k lexical matches."""
        if not self._docs or self._avgdl == 0.0:
            return []
        q_tokens = _tokens(query)
        if not q_tokens:
            return []
        n_docs = len(self._docs)
        scores: list[tuple[int, float]] = []
        for pos, doc in enumerate(self._docs):
            if not doc:
                scores.append((pos, 0.0))
                continue
            tf: dict[str, int] = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            score = 0.0
            for term in q_tokens:
                f = tf.get(term, 0)
                if not f:
                    continue
                df = self._df.get(term, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = f + self._k1 * (
                    1.0 - self._b + self._b * len(doc) / self._avgdl
                )
                score += idf * (f * (self._k1 + 1.0)) / denom
            scores.append((pos, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]


# --- Template-based chunking ----------------------------------------------------------


@dataclass
class RawChunk:
    """A chunk produced by a template, before IDs and embeddings."""

    text: str
    kind: str = "text"
    heading: str = ""

    def clean(self) -> str:
        return re.sub(r"[ \t]+", " ", self.text or "").strip()


_QA_PAIR_RE = re.compile(
    r"^\s*(?:Q|Câu hỏi|Question)\s*[:.)]?\s*(.+?)\s*\n+"
    r"\s*(?:A|Trả lời|Answer)\s*[:.)]?\s*(.+)",
    re.DOTALL,
)
_ARTICLE_RE = re.compile(
    r"^(?:Điều|Article|Art\.?|Mục|Section|Chương|Chapter)\s+[\w\d]+", re.IGNORECASE
)
_SLIDE_RE = re.compile(
    r"^(?:#+\s*)?(?:Slide|Trang trình bày|Trang)\s*(\d+)\s*[:\-—]?\s*(.*)$",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _heading_of(line: str) -> str | None:
    m = _HEADING_RE.match(line.strip())
    if m:
        return m.group(2).strip()
    stripped = line.strip()
    if (
        stripped
        and len(stripped) <= 80
        and not stripped.endswith((".", "!", "?", ",", ";", ":"))
        and (stripped.isupper() or stripped.istitle())
    ):
        return stripped
    return None


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]


def chunk_naive(text: str, chunk_tokens: int, overlap: int) -> list[RawChunk]:
    """Fixed-token windows with overlap — the universal fallback.

    Long single paragraphs (common in PDF extracts) are first split into
    sentences so the window budget is honoured even without blank lines.
    """
    chunks: list[RawChunk] = []
    target = max(32, int(chunk_tokens))
    overlap = max(0, min(int(overlap), target // 2))

    pieces: list[str] = []
    for para in _split_paragraphs(text):
        if count_tokens(para) <= target:
            pieces.append(para)
            continue
        # Sentence split first; a still-oversized sentence (no terminators,
        # e.g. a wall of words) is hard-split by fixed token windows.
        sentences = [s for s in _SENTENCE_SPLIT_RE.split(para) if s and s.strip()]
        for sentence in sentences:
            if count_tokens(sentence) <= target:
                pieces.append(sentence)
                continue
            words = sentence.split()
            window: list[str] = []
            window_tokens = 0
            for word in words:
                w_tokens = count_tokens(word)
                if window and window_tokens + w_tokens > target:
                    pieces.append(" ".join(window))
                    window, window_tokens = [], 0
                window.append(word)
                window_tokens += w_tokens
            if window:
                pieces.append(" ".join(window))
    if not pieces:
        return chunks

    current: list[str] = []
    current_tokens = 0
    for piece in pieces:
        piece_tokens = count_tokens(piece)
        if current and current_tokens + piece_tokens > target:
            chunks.append(RawChunk(" ".join(current)))
            tail: list[str] = []
            tail_tokens = 0
            # Carry the tail of the previous window as overlap.
            for prev in reversed(current):
                prev_tokens = count_tokens(prev)
                if tail_tokens + prev_tokens > overlap:
                    break
                tail.insert(0, prev)
                tail_tokens += prev_tokens
            current = [*tail, piece]
            current_tokens = sum(count_tokens(p) for p in current)
        else:
            current.append(piece)
            current_tokens += piece_tokens
    if current:
        chunks.append(RawChunk(" ".join(current)))
    return chunks


def chunk_qa(text: str) -> list[RawChunk]:
    """One chunk per Q&A pair; unpaired prose falls back to naive windows."""
    chunks: list[RawChunk] = []
    for match in _QA_PAIR_RE.finditer(text):
        question, answer = match.group(1).strip(), match.group(2).strip()
        chunks.append(
            RawChunk(f"Q: {question}\nA: {answer}", kind="qa", heading=question[:120])
        )
    if not chunks:
        return chunk_naive(text, 256, 48)
    return chunks


def chunk_resume(text: str) -> list[RawChunk]:
    """Split a résumé/CV into contact, experience, education, skills blocks."""
    sections = _split_sections_by_headings(
        text,
        keywords=(
            "experience",
            "education",
            "skills",
            "projects",
            "contact",
            "summary",
        ),
    )
    if not sections:
        return chunk_naive(text, 256, 48)
    return [
        RawChunk(body, kind="resume", heading=heading) for heading, body in sections
    ]


def chunk_paper(text: str) -> list[RawChunk]:
    """Academic paper structure: abstract, sections, references."""
    sections = _split_sections_by_headings(
        text,
        keywords=(
            "abstract",
            "introduction",
            "methods",
            "results",
            "discussion",
            "conclusion",
            "references",
        ),
    )
    if not sections:
        return chunk_naive(text, 256, 48)
    return [RawChunk(body, kind="paper", heading=heading) for heading, body in sections]


def chunk_book(text: str) -> list[RawChunk]:
    """Chapters and hierarchical headings; long chapters get naive windows."""
    sections = _split_sections_by_headings(text, min_heading_level=1)
    chunks: list[RawChunk] = []
    for heading, body in sections:
        pieces = (
            chunk_naive(body, 512, 64) if count_tokens(body) > 600 else [RawChunk(body)]
        )
        for piece in pieces:
            chunks.append(RawChunk(piece.text or body, kind="book", heading=heading))
    return chunks or chunk_naive(text, 512, 64)


def chunk_laws(text: str) -> list[RawChunk]:
    """Legal text: one chunk per article/clause, keeping the article header."""
    chunks: list[RawChunk] = []
    current_heading = ""
    buffer: list[str] = []
    for line in (text or "").splitlines():
        if _ARTICLE_RE.match(line.strip()):
            if buffer:
                chunks.append(
                    RawChunk("\n".join(buffer), kind="law", heading=current_heading)
                )
                buffer = []
            current_heading = line.strip()[:120]
        buffer.append(line)
    if buffer:
        chunks.append(RawChunk("\n".join(buffer), kind="law", heading=current_heading))
    chunks = [c for c in chunks if c.clean()]
    return chunks or chunk_naive(text, 256, 48)


def chunk_presentation(text: str) -> list[RawChunk]:
    """Slide-per-chunk, preserving the slide title with its bullets."""
    chunks: list[RawChunk] = []
    current_title = ""
    buffer: list[str] = []
    for line in (text or "").splitlines():
        m = _SLIDE_RE.match(line.strip())
        if m:
            if buffer:
                chunks.append(
                    RawChunk("\n".join(buffer), kind="slide", heading=current_title)
                )
                buffer = []
            current_title = (m.group(2) or f"Slide {m.group(1)}").strip()[:120]
            continue
        buffer.append(line)
    if buffer:
        chunks.append(RawChunk("\n".join(buffer), kind="slide", heading=current_title))
    chunks = [c for c in chunks if c.clean()]
    return chunks or chunk_naive(text, 256, 48)


def chunk_one(text: str) -> list[RawChunk]:
    """Whole document as one chunk — best for short notes and prompts."""
    return [RawChunk(text.strip(), kind="doc")] if text.strip() else []


#: Dispatch table: template -> chunker(text, chunk_tokens, overlap).
TEMPLATE_CHUNKERS: dict[ChunkTemplate, Callable] = {
    ChunkTemplate.NAIVE: lambda text, tokens, overlap: chunk_naive(
        text, tokens, overlap
    ),
    ChunkTemplate.QA: lambda text, tokens, overlap: chunk_qa(text),
    ChunkTemplate.RESUME: lambda text, tokens, overlap: chunk_resume(text),
    ChunkTemplate.PAPER: lambda text, tokens, overlap: chunk_paper(text),
    ChunkTemplate.BOOK: lambda text, tokens, overlap: chunk_book(text),
    ChunkTemplate.LAWS: lambda text, tokens, overlap: chunk_laws(text),
    ChunkTemplate.PRESENTATION: lambda text, tokens, overlap: chunk_presentation(text),
    ChunkTemplate.ONE: lambda text, tokens, overlap: chunk_one(text),
}


def chunk_document(
    text: str, *, template: ChunkTemplate, chunk_tokens: int = 256, overlap: int = 48
) -> list[RawChunk]:
    """Cut a document with the chosen template. Pure function."""
    text = (text or "").strip()
    if not text:
        return []
    chunker = TEMPLATE_CHUNKERS.get(template)
    if chunker is None:
        chunker = TEMPLATE_CHUNKERS[ChunkTemplate.NAIVE]
    chunks = chunker(text, chunk_tokens, overlap)
    return [c for c in chunks if c.clean()]


def describe_template(template: ChunkTemplate) -> str:
    """Human explanation shown next to the template picker (explainability)."""
    return {
        ChunkTemplate.NAIVE: (
            "Cửa sổ token cố định có chồng lấn — dùng cho văn bản bất kỳ."
        ),
        ChunkTemplate.QA: "Mỗi cặp Hỏi–Đáp một chunk — tốt cho FAQ, sổ tay hỗ trợ.",
        ChunkTemplate.RESUME: "Chia theo CV: kinh nghiệm, học vấn, kỹ năng.",
        ChunkTemplate.PAPER: "Chia theo bài báo: tóm tắt, phương pháp, kết quả.",
        ChunkTemplate.BOOK: "Chia theo chương/tiêu đề; chương dài cắt tiếp.",
        ChunkTemplate.LAWS: "Mỗi Điều/Khoản một chunk — hợp đồng, văn bản pháp luật.",
        ChunkTemplate.PRESENTATION: "Mỗi slide một chunk, giữ tiêu đề với nội dung.",
        ChunkTemplate.ONE: "Toàn tài liệu là một chunk — ghi chú ngắn, prompt mẫu.",
    }.get(template, "Không rõ template.")


# --- Section splitting helper ------------------------------------


def _split_sections_by_headings(
    text: str,
    *,
    keywords: tuple[str, ...] = (),
    min_heading_level: int = 2,
) -> list[tuple[str, str]]:
    """Split markdown-ish text into (heading, body) sections."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    buffer: list[str] = []
    for line in (text or "").splitlines():
        m = _HEADING_RE.match(line.strip())
        if m and len(m.group(1)) >= min_heading_level:
            if buffer:
                sections.append((current_heading, "\n".join(buffer).strip()))
                buffer = []
            current_heading = m.group(2).strip()
            buffer.append(line)
            continue
        stripped = line.strip().lower()
        if keywords and any(stripped.startswith(k) or stripped == k for k in keywords):
            if buffer:
                sections.append((current_heading, "\n".join(buffer).strip()))
                buffer = []
            current_heading = line.strip().rstrip(":")[:120]
            buffer.append(line)
            continue
        buffer.append(line)
    if buffer:
        sections.append((current_heading, "\n".join(buffer).strip()))
    return [(h, b) for h, b in sections if b.strip()]


# --- Retriever ----------------------------------------------------


@dataclass
class IndexedChunk:
    """Internal: a chunk plus its embedding, ready for retrieval."""

    chunk: Chunk
    vector: list[float]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[int]], *, k: int = 60
) -> dict[int, float]:
    """Fuse multiple rankings (lists of item positions) with RRF.

    Standard RRF: score(d) = sum over rankings of 1 / (k + rank(d)).
    """
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            fused[item] = fused.get(item, 0.0) + 1.0 / (k + rank + 1)
    return fused


def rerank_by_coverage(
    query: str, hits: list[RetrievalHit], top_k: int
) -> list[RetrievalHit]:
    """Light reranker: promote chunks covering more query tokens.

    Mirrors RAGFlow's fused re-ranking step, but with a lexical-coverage
    signal instead of a cross-encoder model.
    """
    q_tokens = set(_tokens(query))
    if not q_tokens:
        return hits[:top_k]
    scored: list[tuple[float, int, RetrievalHit]] = []
    for position, hit in enumerate(hits):
        coverage = len(q_tokens & set(_tokens(hit.text))) / len(q_tokens)
        scored.append((coverage * 0.6 + hit.fused_score * 0.4, position, hit))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:top_k]]


class KnowledgeRetriever:
    """In-memory hybrid retriever over one or more knowledge bases.

    Rebuilds its BM25 index lazily per query batch. The vector channel uses
    the deterministic hashed embedder, so retrieval works offline and tests
    stay stable.
    """

    def __init__(self) -> None:
        self._chunks: list[IndexedChunk] = []
        self._bm25 = BM25Index()

    def replace_all(self, chunks: Sequence[Chunk]) -> None:
        """Re-index every chunk (called after any mutation)."""
        self._chunks = [IndexedChunk(c, embed_text(c.text)) for c in chunks]
        self._bm25.rebuild([c.chunk.text for c in self._chunks])

    def __len__(self) -> int:
        return len(self._chunks)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 6,
        use_vector: bool = True,
        use_keywords: bool = True,
        rerank: bool = True,
        similarity_threshold: float = 0.0,
    ) -> list[RetrievalHit]:
        """Hybrid retrieval: vector + BM25, RRF fusion, optional rerank."""
        query = (query or "").strip()
        if not query or not self._chunks:
            return []
        top_k = max(1, min(int(top_k), 50))
        candidate_depth = min(len(self._chunks), max(top_k * 4, 12))

        rankings: list[list[int]] = []
        vector_scores: dict[int, float] = {}
        keyword_scores: dict[int, float] = {}

        if use_vector:
            q_vec = embed_text(query)
            sims: list[tuple[int, float]] = []
            for pos, item in enumerate(self._chunks):
                sim = cosine(q_vec, item.vector)
                sims.append((pos, sim))
            sims.sort(key=lambda item: item[1], reverse=True)
            sims = sims[:candidate_depth]
            rankings.append([pos for pos, _ in sims])
            vector_scores.update(dict(sims))

        if use_keywords:
            lexical = self._bm25.search(query, top_k=candidate_depth)
            lexical = [(pos, score) for pos, score in lexical if score > 0.0]
            rankings.append([pos for pos, _ in lexical])
            keyword_scores.update(dict(lexical))

        if not rankings:
            return []

        if len(rankings) == 1:
            fused = {pos: 1.0 / (60 + rank + 1) for rank, pos in enumerate(rankings[0])}
        else:
            fused = reciprocal_rank_fusion(rankings)

        order = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        hits: list[RetrievalHit] = []
        for position, score in order:
            item = self._chunks[position]
            vs = round(vector_scores.get(position, 0.0), 4)
            ks = round(keyword_scores.get(position, 0.0), 4)
            if use_vector and vs > 0 and vs < similarity_threshold:
                continue
            hits.append(
                RetrievalHit(
                    chunk_id=item.chunk.id,
                    kb_id=item.chunk.kb_id,
                    document_id=item.chunk.document_id,
                    document_name=item.chunk.document_name,
                    index=item.chunk.index,
                    text=item.chunk.text,
                    heading=item.chunk.heading,
                    kind=item.chunk.kind,
                    vector_score=vs,
                    keyword_score=ks,
                    fused_score=round(score, 6),
                    rank=0,
                )
            )
        if rerank and len(rankings) > 1:
            hits = rerank_by_coverage(query, hits, top_k)
        else:
            hits = hits[:top_k]
        for rank, hit in enumerate(hits, start=1):
            hit.rank = rank
        return hits


# --- Grounding --------------------------------------------------


def build_grounding(
    query: str, hits: list[RetrievalHit], *, kb_id: str | None = None
) -> GroundingBundle:
    """Turn retrieval hits into a citation-ready grounding bundle."""
    citations: list[str] = []
    lines: list[str] = ["Retrieved knowledge (cite as [n]):"]
    for hit in hits:
        n = len(citations) + 1
        label = f"[{n}] {hit.document_name}"
        if hit.heading:
            label += f" — {hit.heading}"
        citations.append(label)
        text = re.sub(r"\s+", " ", hit.text).strip()
        if len(text) > 280:
            text = text[:277] + "..."
        lines.append(f"[{n}] ({label}) {text}")
    return GroundingBundle(
        query=query,
        kb_id=kb_id,
        hits=hits,
        citations=citations,
        context_text="\n".join(lines),
        generated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
