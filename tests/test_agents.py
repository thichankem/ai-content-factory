"""Tests for multi-vendor AI agents: adapters, routing, and API surface."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings
from content_factory.presets import PresetLibrary
from content_factory.providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAiCompatibleProvider,
    ProviderChain,
    ProviderError,
    ProviderTier,
)
from content_factory.script_engine import build_script_prompt


def _multi_vendor_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "template_enabled": False,
        "money_printer_enabled": False,
        "strong_llm_enabled": False,
        "documents_web_enabled": False,
        "anthropic_enabled": True,
        "anthropic_api_key": "sk-ant-test",
        "google_enabled": True,
        "google_api_key": "goog-test",
        "deepseek_enabled": True,
        "deepseek_api_key": "ds-test",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


# --- Anthropic adapter -------------------------------------------------------


def test_anthropic_provider_parses_content_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AnthropicProvider(
        base_url="https://api.anthropic.test/v1",
        model="claude-sonnet-4-5",
        api_key="sk-ant-test",
    )
    captured: dict[str, object] = {}

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        return SimpleNamespace(
            status_code=200,
            text="{}",
            json=lambda: {
                "content": [
                    {"type": "text", "text": "[Hook]  "},
                    {"type": "text", "text": "Hello world"},
                ]
            },
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    text = asyncio.run(provider.generate_script("write a script"))
    assert text == "[Hook]  Hello world"
    assert captured["url"] == "https://api.anthropic.test/v1/messages"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-api-key"] == "sk-ant-test"
    assert "anthropic-version" in headers
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["max_tokens"] == 4096


def test_anthropic_provider_rejects_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = AnthropicProvider(base_url="https://api.anthropic.test/v1", model="m")

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        return SimpleNamespace(status_code=401, text="unauthorized", json=lambda: {})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    with pytest.raises(ProviderError):
        asyncio.run(provider.generate_script("prompt"))


def test_anthropic_provider_rejects_empty_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AnthropicProvider(base_url="https://api.anthropic.test/v1", model="m")

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        return SimpleNamespace(status_code=200, text="{}", json=lambda: {"content": []})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    with pytest.raises(ProviderError):
        asyncio.run(provider.generate_script("prompt"))


# --- Gemini adapter ----------------------------------------------------------


def test_gemini_provider_parses_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(
        base_url="https://generativelanguage.test/v1beta", model="gemini-2.5-flash"
    )
    captured: dict[str, object] = {}

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        captured["url"] = url
        captured["payload"] = json
        return SimpleNamespace(
            status_code=200,
            text="{}",
            json=lambda: {
                "candidates": [
                    {"content": {"parts": [{"text": "Script "}, {"text": "body"}]}}
                ]
            },
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    text = asyncio.run(provider.generate_script("topic"))
    assert text == "Script body"
    assert captured["url"] == (
        "https://generativelanguage.test/v1beta/models/gemini-2.5-flash:generateContent"
    )


def test_gemini_provider_rejects_missing_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiProvider(base_url="https://generativelanguage.test", model="m")

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        return SimpleNamespace(status_code=200, text="{}", json=lambda: {"blocked": 1})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    with pytest.raises(ProviderError):
        asyncio.run(provider.generate_script("prompt"))


# --- Multi-vendor routing ----------------------------------------------------


def test_strong_tier_follows_configured_vendor_order() -> None:
    chain = ProviderChain(_multi_vendor_settings())
    strong = chain._providers[ProviderTier.STRONG]
    assert [provider.name for provider in strong] == ["claude", "gemini", "deepseek"]


def test_strong_tier_order_is_configurable() -> None:
    chain = ProviderChain(
        _multi_vendor_settings(strong_provider_order="deepseek,claude")
    )
    strong = chain._providers[ProviderTier.STRONG]
    assert [provider.name for provider in strong] == ["deepseek", "claude"]


def test_disabled_vendors_are_skipped() -> None:
    settings = _multi_vendor_settings(google_enabled=False, deepseek_enabled=False)
    chain = ProviderChain(settings)
    assert [provider.name for provider in chain._providers[ProviderTier.STRONG]] == [
        "claude"
    ]


def test_tier_falls_through_to_next_vendor() -> None:
    settings = _multi_vendor_settings(retry_max_attempts=1)
    chain = ProviderChain(settings)

    async def boom(prompt: str) -> str:
        raise ProviderError("claude is down")

    async def ok(prompt: str) -> str:
        return "[Hook] from gemini"

    strong = chain._providers[ProviderTier.STRONG]
    assert [provider.name for provider in strong] == ["claude", "gemini", "deepseek"]
    strong[0].generate_script = boom  # type: ignore[method-assign]
    strong[1].generate_script = ok  # type: ignore[method-assign]
    strong[2].generate_script = boom  # type: ignore[method-assign]

    result = asyncio.run(chain.generate("prompt"))
    assert result.provider == "gemini"
    assert result.text == "[Hook] from gemini"


def test_catalog_describes_every_agent() -> None:
    chain = ProviderChain(_multi_vendor_settings())
    catalog = {agent.name: agent for agent in chain.catalog()}
    assert catalog["claude"].kind == "anthropic"
    assert catalog["gemini"].kind == "google"
    assert catalog["deepseek"].kind == "openai-compatible"
    assert catalog["claude"].tier == "strong"
    assert all(agent.enabled for agent in catalog.values())


def test_ollama_registers_in_local_tier() -> None:
    settings = Settings(
        money_printer_enabled=False,
        strong_llm_enabled=False,
        template_enabled=False,
        ollama_enabled=True,
    )
    chain = ProviderChain(settings)
    local = chain._providers[ProviderTier.LOCAL]
    assert [provider.name for provider in local] == ["ollama"]
    assert isinstance(local[0], OpenAiCompatibleProvider)


def test_script_prompt_is_provider_agnostic() -> None:
    """Every vendor gets the same contract-style prompt."""
    style = PresetLibrary().resolve("documentary")
    prompt = build_script_prompt(
        topic="Deep sea vents", language="en", target_seconds=60, style=style
    )
    assert "# OUTPUT CONTRACT" in prompt
    assert "Topic: Deep sea vents" in prompt


# --- API surface -------------------------------------------------------------


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(
        create_app(
            settings.model_copy(
                update={
                    "anthropic_enabled": True,
                    "anthropic_api_key": "sk-ant-test",
                }
            )
        )
    )


def test_agents_endpoint_lists_configured_agents(client: TestClient) -> None:
    response = client.get("/agents")
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "cost_first"
    assert any(agent["name"] == "claude" for agent in body["agents"])
    assert "viral-short" in body["preset_styles"]


def test_script_styles_endpoint_lists_builtins(client: TestClient) -> None:
    response = client.get("/script/styles")
    assert response.status_code == 200
    names = {style["name"] for style in response.json()}
    assert {"viral-short", "documentary", "educational"} <= names


def test_script_style_markdown_endpoint(client: TestClient) -> None:
    response = client.get("/script/styles/viral-short/md")
    assert response.status_code == 200
    assert "# Style: viral-short" in response.text
    assert response.headers["content-type"].startswith("text/markdown")


def test_script_style_can_be_created_and_read(client: TestClient) -> None:
    created = client.put(
        "/script/styles/my-house-style",
        json={"name": "ignored", "tone": "urgent", "sentence_max_units": 8},
    )
    assert created.status_code == 200
    assert created.json()["name"] == "my-house-style"
    assert created.json()["tone"] == "urgent"

    fetched = client.get("/script/styles/my-house-style")
    assert fetched.status_code == 200
    assert fetched.json()["sentence_max_units"] == 8

    deleted = client.delete("/script/styles/my-house-style")
    assert deleted.json() == {"deleted": True}
    assert client.delete("/script/styles/viral-short").json() == {"deleted": False}


def test_unknown_script_style_returns_404(client: TestClient) -> None:
    assert client.get("/script/styles/nope").status_code == 404
    assert client.get("/script/styles/nope/md").status_code == 404
