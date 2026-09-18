"""AI provider adapters and the routing chain."""

from __future__ import annotations

import enum
from typing import NamedTuple, Protocol

import httpx

from .config import Settings
from .models import AgentInfo
from .resilience import CircuitBreaker, CircuitOpenError, TokenBucket, retry


class ProviderError(Exception):
    """Raised when a single provider cannot produce a script."""


class ProviderUnavailableError(ProviderError):
    """Raised when no enabled provider can serve the request."""


class ProviderTier(enum.StrEnum):
    """Relative strength/cost of a provider."""

    LOCAL = "local"
    WEAK = "weak"
    STRONG = "strong"


#: What each tier is trusted with, in the vocabulary the studio UI shows.
#: Script writing is the one job every tier can be routed, so it is always
#: present; the heavier tiers additionally serve the pipeline's other AI stages.
_TIER_CAPABILITIES: dict[ProviderTier, tuple[str, ...]] = {
    ProviderTier.LOCAL: ("script", "offline"),
    ProviderTier.WEAK: ("script", "research"),
    ProviderTier.STRONG: ("script", "research", "seo", "vision"),
}


def _slug(name: str) -> str:
    """A stable, URL-safe identifier for a vendor name."""
    cleaned = [
        character.lower() if character.isalnum() else "-" for character in name.strip()
    ]
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "provider"


class GenerationResult(NamedTuple):
    """Successful generation outcome."""

    text: str
    tier: ProviderTier
    provider: str
    model: str | None


class ScriptProvider(Protocol):
    """Interface every provider adapter implements."""

    tier: ProviderTier
    name: str
    kind: str
    model: str | None

    async def generate_script(self, prompt: str) -> str: ...


SYSTEM_PROMPT = (
    "You write short-form narration scripts. Learn the topic, facts, and "
    "pacing from the source, but always produce an original script. Never "
    "copy the source verbatim."
)


def _field(prompt: str, key: str, default: str) -> str:
    """Extract ``key: value`` from the prompt lines used by the service."""
    prefix = f"{key}: "
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip() or default
    return default


def _facts(prompt: str) -> list[str]:
    """Extract the ``Key facts:`` bullet list from the prompt, if present."""
    lines = prompt.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith("Key facts:"):
            start = index
            break
    if start is None:
        return []
    facts: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            break
        facts.append(stripped.lstrip("- ").strip())
    return facts


class TemplateProvider:
    """Built-in offline provider that drafts a script from the topic.

    Guarantees the pipeline works with zero configuration. Intended as a
    placeholder for demos and tests; swap in a real provider for production
    scripts.
    """

    tier: ProviderTier = ProviderTier.LOCAL
    name: str = "template"
    kind: str = "builtin"
    model: str | None = "template-v1"
    base_url: str | None = None

    async def generate_script(self, prompt: str) -> str:
        topic = _field(prompt, "Topic", "your everyday surroundings")
        language = _field(prompt, "Language", "en")
        duration = _field(prompt, "Target duration", "45")
        facts = _facts(prompt)[:3]

        body = [
            "[Hook]",
            f"Have you noticed how {topic} quietly shapes your day?",
            "",
            "[Context]",
            "Most people walk past it, but the details tell a bigger story.",
            "",
        ]
        if facts:
            body.extend(
                [
                    "[Evidence]",
                    *[f"- {fact}" for fact in facts],
                    "",
                ]
            )
        body.extend(
            [
                "[Turn]",
                "Look closer and the pattern becomes obvious — it changes how you see",
                "everything.",
                "",
                "[Payoff]",
                "That is the quiet power hiding in plain sight.",
                "",
                "[CTA]",
                "Follow for more stories like this.",
                "",
                (
                    f"(Drafted by the built-in template provider for a ~{duration} "
                    f"narration in {language}; swap in a real provider for "
                    "production scripts.)"
                ),
            ]
        )
        return "\n".join(body)


class OpenAiCompatibleProvider:
    """Minimal OpenAI-compatible ``/chat/completions`` client."""

    tier: ProviderTier
    name: str
    kind: str = "openai-compatible"
    model: str | None

    def __init__(
        self,
        *,
        tier: ProviderTier,
        name: str,
        base_url: str,
        model: str | None,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 5.0,
        max_tokens: int | None = None,
    ) -> None:
        self.tier = tier
        self.name = name
        self.model = model
        self._max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)

    async def generate_script(self, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        if self._max_tokens:
            payload["max_tokens"] = self._max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            snippet = response.text[:200]
            raise ProviderError(
                f"{self.name} returned HTTP {response.status_code}: {snippet}"
            )
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name} returned an unexpected payload") from exc
        text = content.strip() if isinstance(content, str) else ""
        if not text:
            raise ProviderError(f"{self.name} returned an empty script")
        return text


class AnthropicProvider:
    """Anthropic Claude through the native ``/v1/messages`` API.

    Unlike the OpenAI-compatible shim this uses Claude's own wire format
    (``system`` + ``content`` blocks), so tool use, prompt caching, and future
    Claude-only features can be layered on without a translation layer.
    """

    tier: ProviderTier = ProviderTier.STRONG
    kind: str = "anthropic"

    def __init__(
        self,
        *,
        name: str = "claude",
        base_url: str,
        model: str | None,
        api_key: str | None = None,
        version: str = "2023-06-01",
        max_tokens: int = 4096,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 5.0,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._version = version
        self._max_tokens = max_tokens
        self._timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)

    async def generate_script(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self._version,
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        payload = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "system": SYSTEM_PROMPT,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages", json=payload, headers=headers
            )
        if response.status_code != 200:
            snippet = response.text[:200]
            raise ProviderError(
                f"{self.name} returned HTTP {response.status_code}: {snippet}"
            )
        data = response.json()
        blocks = data.get("content") if isinstance(data, dict) else None
        if not isinstance(blocks, list):
            raise ProviderError(f"{self.name} returned an unexpected payload")
        text = "".join(
            block.get("text", "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        if not text:
            raise ProviderError(f"{self.name} returned an empty script")
        return text


class GeminiProvider:
    """Google Gemini through the native ``generateContent`` API."""

    tier: ProviderTier = ProviderTier.STRONG
    kind: str = "google"

    def __init__(
        self,
        *,
        name: str = "gemini",
        base_url: str,
        model: str | None,
        api_key: str | None = None,
        max_tokens: int = 4096,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 5.0,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)

    async def generate_script(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-goog-api-key"] = self._api_key
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": self._max_tokens,
            },
        }
        url = f"{self.base_url}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            snippet = response.text[:200]
            raise ProviderError(
                f"{self.name} returned HTTP {response.status_code}: {snippet}"
            )
        data = response.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name} returned an unexpected payload") from exc
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
        if not text:
            raise ProviderError(f"{self.name} returned an empty script")
        return text


class ProviderChain:
    """Routes a request through enabled providers according to strategy.

    Each tier holds an ordered list of vendors, so the strong tier can try
    Claude, then Gemini, then DeepSeek, then any OpenAI-compatible endpoint.
    Every provider is protected by its own circuit breaker and a shared rate
    limiter; individual calls are retried with backoff. If all providers fail,
    :class:`ProviderUnavailableError` is raised.
    """

    def __init__(
        self,
        settings: Settings,
        providers: dict[ProviderTier, ScriptProvider] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = (
            {tier: [provider] for tier, provider in providers.items()}
            if providers is not None
            else self._build(settings)
        )
        self._breakers: dict[ProviderTier, CircuitBreaker] = {
            tier: CircuitBreaker(
                failure_threshold=settings.circuit_failure_threshold,
                success_threshold=settings.circuit_success_threshold,
                open_timeout_seconds=settings.circuit_open_timeout_seconds,
            )
            for tier in self._providers
        }
        self._limiter = TokenBucket(
            capacity=settings.rate_limit_capacity,
            refill_per_second=settings.rate_limit_refill_per_second,
        )

    def _build(self, settings: Settings) -> dict[ProviderTier, list[ScriptProvider]]:
        built: dict[ProviderTier, list[ScriptProvider]] = {}

        local: list[ScriptProvider] = []
        if settings.template_enabled:
            local.append(TemplateProvider())
        if settings.ollama_enabled:
            local.append(
                OpenAiCompatibleProvider(
                    tier=ProviderTier.LOCAL,
                    name="ollama",
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    api_key=settings.ollama_api_key,
                    timeout_seconds=settings.http_timeout_seconds,
                    connect_timeout_seconds=settings.http_connect_timeout_seconds,
                )
            )
        if local:
            built[ProviderTier.LOCAL] = local

        weak: list[ScriptProvider] = []
        if settings.money_printer_enabled:
            weak.append(
                OpenAiCompatibleProvider(
                    tier=ProviderTier.WEAK,
                    name="money-printer-turbo",
                    base_url=settings.money_printer_base_url,
                    model="local",
                    api_key=settings.money_printer_api_key,
                    timeout_seconds=settings.http_timeout_seconds,
                    connect_timeout_seconds=settings.http_connect_timeout_seconds,
                )
            )
        if weak:
            built[ProviderTier.WEAK] = weak

        strong = [
            provider
            for provider in (
                self._build_strong(name, settings)
                for name in self._strong_order(settings)
            )
            if provider is not None
        ]
        if strong:
            built[ProviderTier.STRONG] = strong
        return built

    @staticmethod
    def _strong_order(settings: Settings) -> list[str]:
        names = [
            chunk.strip().lower()
            for chunk in settings.strong_provider_order.split(",")
            if chunk.strip()
        ]
        return names or ["anthropic", "google", "deepseek", "openai"]

    @staticmethod
    def _build_strong(name: str, settings: Settings) -> ScriptProvider | None:
        """Instantiate one strong-tier vendor if it is enabled."""
        if name in {"anthropic", "claude"} and settings.anthropic_enabled:
            return AnthropicProvider(
                name="claude",
                base_url=settings.anthropic_base_url,
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                version=settings.anthropic_version,
                max_tokens=settings.strong_max_tokens,
                timeout_seconds=settings.strong_llm_timeout_seconds,
                connect_timeout_seconds=settings.http_connect_timeout_seconds,
            )
        if name in {"google", "gemini"} and settings.google_enabled:
            return GeminiProvider(
                name="gemini",
                base_url=settings.google_base_url,
                model=settings.google_model,
                api_key=settings.google_api_key,
                max_tokens=settings.strong_max_tokens,
                timeout_seconds=settings.strong_llm_timeout_seconds,
                connect_timeout_seconds=settings.http_connect_timeout_seconds,
            )
        if name == "deepseek" and settings.deepseek_enabled:
            return OpenAiCompatibleProvider(
                tier=ProviderTier.STRONG,
                name="deepseek",
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                timeout_seconds=settings.strong_llm_timeout_seconds,
                connect_timeout_seconds=settings.http_connect_timeout_seconds,
            )
        if name in {"openai", "strong", "strong-llm"} and settings.strong_llm_enabled:
            return OpenAiCompatibleProvider(
                tier=ProviderTier.STRONG,
                name="strong-llm",
                base_url=settings.strong_llm_base_url,
                model=settings.strong_llm_model,
                api_key=settings.strong_llm_api_key,
                timeout_seconds=settings.strong_llm_timeout_seconds,
                connect_timeout_seconds=settings.http_connect_timeout_seconds,
                max_tokens=settings.strong_max_tokens,
            )
        return None

    @property
    def enabled_tiers(self) -> list[str]:
        return [tier.value for tier in self._providers]

    @property
    def provider_names(self) -> list[str]:
        return [
            provider.name
            for tier in self._providers
            for provider in self._providers[tier]
        ]

    def health(self) -> dict[str, str]:
        return {tier.value: self._breakers[tier].state for tier in self._providers}

    def catalog(self) -> list[AgentInfo]:
        """Describe every configured vendor for the operator-facing API.

        Each entry is filled for both audiences at once: ``kind``/``tier``/
        ``breaker`` describe the routing the pipeline performs, while
        ``id``/``role``/``provider``/``capabilities`` are the same facts in the
        vocabulary the studio renderer uses, so neither client has to map one
        onto the other. A vendor's ``role`` is the tier it serves, because that
        is exactly what the pipeline routes by.
        """
        agents: list[AgentInfo] = []
        for tier, providers in self._providers.items():
            for provider in providers:
                name = provider.name
                kind = getattr(provider, "kind", "openai-compatible")
                agents.append(
                    AgentInfo(
                        name=name,
                        kind=kind,
                        tier=tier.value,
                        enabled=True,
                        model=provider.model,
                        base_url=getattr(provider, "base_url", None),
                        breaker=self._breakers[tier].state,
                        id=_slug(name),
                        role=tier.value,
                        provider=kind,
                        capabilities=list(_TIER_CAPABILITIES.get(tier, ())),
                    )
                )
        return agents

    def _ordered_tiers(self) -> list[ProviderTier]:
        tiers = list(self._providers)
        if self._settings.provider_strategy == "quality_first":
            tiers.reverse()
        return tiers

    async def generate(self, prompt: str) -> GenerationResult:
        """Try each provider in strategy order; raise if all fail."""
        failures: list[str] = []
        for tier in self._ordered_tiers():
            breaker = self._breakers[tier]
            for provider in self._providers[tier]:
                try:
                    await self._limiter.acquire()
                    text = await retry(
                        breaker.wrap(provider.generate_script),
                        prompt,
                        attempts=self._settings.retry_max_attempts,
                        base_delay=self._settings.retry_base_delay_seconds,
                        max_delay=self._settings.retry_max_delay_seconds,
                        jitter_ratio=self._settings.retry_jitter_ratio,
                    )
                except CircuitOpenError as exc:
                    failures.append(f"{provider.name}: {exc}")
                    continue
                except Exception as exc:
                    failures.append(f"{provider.name}: {exc}")
                    continue
                return GenerationResult(
                    text=text,
                    tier=tier,
                    provider=provider.name,
                    model=provider.model,
                )
        raise ProviderUnavailableError("; ".join(failures) or "No providers enabled")
