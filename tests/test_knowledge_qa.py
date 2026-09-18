"""NotebookLM-style grounded Q&A and URL ingestion tests.

Covers the two new knowledge-engine capabilities:

* ``POST /kb/{id}/ask`` — retrieve the top chunks, ground an answer on them,
  and return it with ``[n]`` citations. When no provider is configured the
  offline extractive fallback answers from the top hits instead.
* ``POST /kb/{id}/ingest-url`` — pull a web page, strip markup, and ingest it
  as a source, exactly like NotebookLM's "add a web source".
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from content_factory.models import (
    KBAskRequest,
    KBCreate,
    KBDocumentStatus,
    KBIngestText,
    KBIngestUrl,
    KBTurn,
)
from content_factory.providers import ProviderChain, ProviderTier, ScriptProvider


class _FakeProvider(ScriptProvider):
    """A deterministic provider that echoes a canned grounded answer."""

    def __init__(self, answer: str) -> None:
        self.name = "fake"
        self.model = "fake"
        self._answer = answer

    async def generate_script(self, prompt: str) -> str:
        return self._answer


@pytest.fixture
def kb(service):
    return service.create_kb(KBCreate(name="Sources", template="naive"))


@pytest.fixture
def populated_kb(service, kb):
    service.ingest_text(
        kb.id,
        KBIngestText(
            title="Morning light",
            text=(
                "Morning light changes how cities feel because low sun casts "
                "long shadows and warm tones. Architects plan streets around it."
            ),
        ),
    )
    return kb


def _ask(service, kb_id: str, query: str, **kwargs):
    return asyncio.run(service.ask_kb(kb_id, KBAskRequest(query=query, **kwargs)))


def _with_fake_provider(service, settings, answer: str) -> None:
    service._providers = ProviderChain(
        settings,
        providers={ProviderTier.STRONG: _FakeProvider(answer)},
    )


# --- Service: offline fallback ----------------------------------------------


def test_ask_offline_returns_extractive_answer_with_citations(
    service, populated_kb
) -> None:
    resp = _ask(service, populated_kb.id, "How does morning light affect cities?")
    assert resp.grounded is False
    assert resp.provider == "template"
    assert resp.citations, "offline answers must still carry citations"
    assert "morning light" in resp.answer.lower()
    assert resp.hits


def test_ask_empty_kb_answers_no_knowledge(service, kb) -> None:
    resp = _ask(service, kb.id, "anything at all")
    assert resp.grounded is False
    assert "No relevant knowledge" in resp.answer
    assert not resp.hits


# --- Service: grounded synthesis with a provider ----------------------------


def test_ask_grounded_with_provider_returns_synthesized_answer(
    service, settings, populated_kb
) -> None:
    _with_fake_provider(service, settings, "Low sun casts long shadows. [1]")
    resp = _ask(service, populated_kb.id, "How does morning light affect cities?")
    assert resp.grounded is True
    assert resp.provider == "fake"
    assert "shadows" in resp.answer
    assert resp.citations


def test_ask_includes_history_context(service, settings, populated_kb) -> None:
    _with_fake_provider(service, settings, "Yes — it shapes street grids. [1]")
    resp = _ask(
        service,
        populated_kb.id,
        "Does it affect architecture?",
        history=[KBTurn(role="user", content="Tell me about morning light.")],
    )
    assert resp.grounded is True
    assert resp.answer


# --- Service: ingest from URL ------------------------------------------------


def test_ingest_url_fetches_and_ingests(service, kb) -> None:
    html = "<html><body><h1>Doc</h1><p>Morning light matters.</p></body></html>"
    with patch("urllib.request.urlopen") as mock:
        mock.return_value.__enter__.return_value.read.return_value = html.encode()
        doc = service.ingest_url(kb.id, KBIngestUrl(url="https://example.com/doc"))
    assert doc.status == KBDocumentStatus.PARSED
    assert doc.source_type == "url"
    assert doc.chunk_count >= 1


def test_ingest_url_unreachable_marks_document_failed(service, kb) -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("boom")):
        doc = service.ingest_url(kb.id, KBIngestUrl(url="https://example.com/x"))
    assert doc.status == KBDocumentStatus.FAILED
    assert doc.error


# --- API ----------------------------------------------------------------------


def test_api_ask_offline(client: TestClient) -> None:
    kb = client.post("/kb", json={"name": "Api", "template": "naive"}).json()
    client.post(
        f"/kb/{kb['id']}/documents",
        json={"title": "City", "text": "Cities glow under low winter sun."},
    ).raise_for_status()
    resp = client.post(f"/kb/{kb['id']}/ask", json={"query": "Why do cities glow?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is False
    assert body["citations"]
    assert body["answer"]


def test_api_ask_with_only_template_provider_uses_extractive_fallback(
    client_with_template: TestClient,
) -> None:
    """The template provider drafts scripts, not answers — so it falls back to
    the extractive grounded answer rather than returning a canned script."""
    kb = client_with_template.post(
        "/kb", json={"name": "Api", "template": "naive"}
    ).json()
    client_with_template.post(
        f"/kb/{kb['id']}/documents",
        json={"title": "City", "text": "Cities glow under low winter sun."},
    ).raise_for_status()
    resp = client_with_template.post(
        f"/kb/{kb['id']}/ask", json={"query": "Why do cities glow?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is False
    assert body["provider"] == "template"
    assert body["citations"]
    assert "cities" in body["answer"].lower()


def test_api_ask_validates_query(client: TestClient) -> None:
    kb = client.post("/kb", json={"name": "Api"}).json()
    resp = client.post(f"/kb/{kb['id']}/ask", json={"query": ""})
    assert resp.status_code == 422


def test_api_ingest_url(client: TestClient) -> None:
    kb = client.post("/kb", json={"name": "Api"}).json()
    html = "<html><body><p>Morning light shapes city planning.</p></body></html>"
    with patch("urllib.request.urlopen") as mock:
        mock.return_value.__enter__.return_value.read.return_value = html.encode()
        resp = client.post(
            f"/kb/{kb['id']}/ingest-url",
            json={"url": "https://example.com/planning"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "parsed"
    assert body["source_type"] == "url"
