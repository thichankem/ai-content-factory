"""Tests for resilience primitives and the provider chain."""

from __future__ import annotations

import asyncio

import pytest

from content_factory.config import Settings
from content_factory.providers import (
    GenerationResult,
    OpenAiCompatibleProvider,
    ProviderChain,
    ProviderError,
    ProviderTier,
    ProviderUnavailableError,
    ScriptProvider,
    TemplateProvider,
)
from content_factory.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    TokenBucket,
    retry,
)


class FakeProvider(ScriptProvider):
    def __init__(
        self,
        tier: ProviderTier,
        name: str,
        *,
        responses: list[str] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.tier = tier
        self.name = name
        self.model = name
        self._responses = list(responses or [])
        self._errors = list(errors or [])
        self.calls = 0

    async def generate_script(self, prompt: str) -> str:
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        if self._responses:
            return self._responses.pop(0)
        return f"script-from-{self.name}"


def make_chain(
    *,
    strategy: str = "cost_first",
    providers: dict[ProviderTier, ScriptProvider],
) -> ProviderChain:
    settings = Settings(
        provider_strategy=strategy,  # type: ignore[arg-type]
        money_printer_enabled=False,
        strong_llm_enabled=False,
        retry_max_attempts=1,
        retry_base_delay_seconds=0.0,
        retry_max_delay_seconds=0.0,
        retry_jitter_ratio=0.0,
    )
    return ProviderChain(settings, providers=providers)


# --- Circuit breaker --------------------------------------------------------


def test_circuit_breaker_opens_after_failures() -> None:
    breaker = CircuitBreaker(
        failure_threshold=2, success_threshold=1, open_timeout_seconds=60
    )
    assert breaker.state == "closed"

    async def boom() -> str:
        raise RuntimeError("boom")

    async def run() -> None:
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.wrap(boom)()

    asyncio.run(run())
    assert breaker.state == "open"


def test_circuit_breaker_rejects_while_open() -> None:
    breaker = CircuitBreaker(
        failure_threshold=1, success_threshold=1, open_timeout_seconds=3600
    )

    async def boom() -> str:
        raise RuntimeError("boom")

    async def run() -> None:
        with pytest.raises(RuntimeError):
            await breaker.wrap(boom)()
        with pytest.raises(CircuitOpenError):
            await breaker.wrap(boom)()

    asyncio.run(run())


def test_circuit_breaker_recovers_after_successes() -> None:
    breaker = CircuitBreaker(
        failure_threshold=1, success_threshold=2, open_timeout_seconds=0.05
    )
    breaker.record_failure()
    assert breaker.state == "open"
    breaker.record_success()
    breaker.record_success()
    assert breaker.state == "closed"


def test_circuit_breaker_half_open_after_timeout() -> None:
    breaker = CircuitBreaker(
        failure_threshold=1, success_threshold=1, open_timeout_seconds=0.01
    )
    breaker.record_failure()
    assert breaker.state in ("open", "half_open")


# --- Token bucket -----------------------------------------------------------


def test_token_bucket_acquires_initial_tokens() -> None:
    bucket = TokenBucket(capacity=3, refill_per_second=10.0)

    async def run() -> None:
        for _ in range(3):
            await bucket.acquire()

    asyncio.run(run())


def test_token_bucket_waits_when_empty() -> None:
    bucket = TokenBucket(capacity=1, refill_per_second=100.0)

    async def run() -> None:
        await bucket.acquire()
        await bucket.acquire()  # must wait for a refill

    asyncio.run(run())


# --- Retry ------------------------------------------------------------------


def test_retry_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = asyncio.run(
        retry(flaky, attempts=5, base_delay=0.0, max_delay=0.0, jitter_ratio=0.0)
    )
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_after_attempts() -> None:
    async def always_fails() -> str:
        raise ProviderError("nope")

    with pytest.raises(ProviderError):
        asyncio.run(
            retry(
                always_fails,
                attempts=3,
                base_delay=0.0,
                max_delay=0.0,
                jitter_ratio=0.0,
            )
        )


def test_retry_does_not_retry_circuit_open() -> None:
    calls = {"n": 0}

    async def open_circuit() -> str:
        calls["n"] += 1
        raise CircuitOpenError("open")

    with pytest.raises(CircuitOpenError):
        asyncio.run(
            retry(
                open_circuit,
                attempts=5,
                base_delay=0.0,
                max_delay=0.0,
                jitter_ratio=0.0,
            )
        )
    assert calls["n"] == 1


# --- Provider chain ---------------------------------------------------------


def test_chain_cost_first_prefers_weak() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak")
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="cost_first",
        providers={ProviderTier.WEAK: weak, ProviderTier.STRONG: strong},
    )

    result = asyncio.run(chain.generate("prompt"))
    assert isinstance(result, GenerationResult)
    assert result.tier == ProviderTier.WEAK
    assert result.provider == "weak"
    assert weak.calls == 1
    assert strong.calls == 0


def test_chain_quality_first_prefers_strong() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak")
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="quality_first",
        providers={ProviderTier.WEAK: weak, ProviderTier.STRONG: strong},
    )

    result = asyncio.run(chain.generate("prompt"))
    assert result.tier == ProviderTier.STRONG
    assert result.provider == "strong"
    assert weak.calls == 0
    assert strong.calls == 1


def test_chain_falls_back_when_primary_fails() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak", errors=[ProviderError("down")])
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="cost_first",
        providers={ProviderTier.WEAK: weak, ProviderTier.STRONG: strong},
    )

    result = asyncio.run(chain.generate("prompt"))
    assert result.provider == "strong"


def test_chain_raises_when_all_fail() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak", errors=[ProviderError("down")])
    strong = FakeProvider(ProviderTier.STRONG, "strong", errors=[ProviderError("down")])
    chain = make_chain(
        strategy="cost_first",
        providers={ProviderTier.WEAK: weak, ProviderTier.STRONG: strong},
    )

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(chain.generate("prompt"))


def test_chain_skips_open_circuit() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak", errors=[ProviderError("down")])
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="cost_first",
        providers={ProviderTier.WEAK: weak, ProviderTier.STRONG: strong},
    )

    # First call trips the weak breaker twice (failure_threshold=5 default, so
    # force it open directly to simulate repeated outages).
    chain._breakers[ProviderTier.WEAK].record_failure()
    chain._breakers[ProviderTier.WEAK].record_failure()
    chain._breakers[ProviderTier.WEAK].record_failure()
    chain._breakers[ProviderTier.WEAK].record_failure()
    chain._breakers[ProviderTier.WEAK].record_failure()

    result = asyncio.run(chain.generate("prompt"))
    assert result.provider == "strong"
    assert weak.calls == 0


# --- Template provider ------------------------------------------------------


def test_template_provider_drafts_a_script() -> None:
    provider = TemplateProvider()
    prompt = (
        "Topic: Morning light\n"
        "Language: vi\n"
        "Target duration: 45 seconds\n"
        "Write an original narration script for a short video."
    )
    text = asyncio.run(provider.generate_script(prompt))
    assert "Morning light" in text
    assert "[Hook]" in text
    assert "45" in text


def test_chain_cost_first_prefers_local_template() -> None:
    local = FakeProvider(ProviderTier.LOCAL, "local")
    weak = FakeProvider(ProviderTier.WEAK, "weak")
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="cost_first",
        providers={
            ProviderTier.LOCAL: local,
            ProviderTier.WEAK: weak,
            ProviderTier.STRONG: strong,
        },
    )
    result = asyncio.run(chain.generate("prompt"))
    assert result.tier == ProviderTier.LOCAL
    assert local.calls == 1
    assert weak.calls == 0
    assert strong.calls == 0


def test_chain_quality_first_skips_local() -> None:
    local = FakeProvider(ProviderTier.LOCAL, "local")
    strong = FakeProvider(ProviderTier.STRONG, "strong")
    chain = make_chain(
        strategy="quality_first",
        providers={ProviderTier.LOCAL: local, ProviderTier.STRONG: strong},
    )
    result = asyncio.run(chain.generate("prompt"))
    assert result.tier == ProviderTier.STRONG
    assert local.calls == 0


def test_chain_falls_back_to_local_last() -> None:
    weak = FakeProvider(ProviderTier.WEAK, "weak", errors=[ProviderError("down")])
    local = FakeProvider(ProviderTier.LOCAL, "local")
    chain = make_chain(
        strategy="quality_first",
        providers={ProviderTier.LOCAL: local, ProviderTier.WEAK: weak},
    )
    result = asyncio.run(chain.generate("prompt"))
    assert result.provider == "local"


# --- OpenAI-compatible adapter ----------------------------------------------


def test_openai_provider_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAiCompatibleProvider(
        tier=ProviderTier.STRONG,
        name="fake",
        base_url="http://example.test/v1",
        model="m",
    )

    async def fake_post(self, url, json=None, headers=None):
        from types import SimpleNamespace

        return SimpleNamespace(
            status_code=200,
            text="{}",
            json=lambda: {"choices": [{"message": {"content": "  hello world  "}}]},
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    text = asyncio.run(provider.generate_script("prompt"))
    assert text == "hello world"


def test_openai_provider_rejects_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAiCompatibleProvider(
        tier=ProviderTier.STRONG,
        name="fake",
        base_url="http://example.test/v1",
        model="m",
    )

    async def fake_post(self, url, json=None, headers=None):
        from types import SimpleNamespace

        return SimpleNamespace(status_code=500, text="boom", json=lambda: {})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    with pytest.raises(ProviderError):
        asyncio.run(provider.generate_script("prompt"))
