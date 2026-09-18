"""Tests for configuration loading and defaults."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from content_factory.config import Settings


def test_defaults_match_template() -> None:
    settings = Settings()
    assert settings.app_name == "ai-content-factory"
    assert settings.debug is False
    assert settings.provider_strategy == "cost_first"
    assert settings.money_printer_enabled is True
    assert settings.money_printer_base_url == "http://127.0.0.1:8080"
    assert settings.strong_llm_enabled is False
    assert settings.strong_llm_model == "gpt-4o-mini"
    assert settings.template_enabled is True
    assert settings.research_max_sources == 6
    assert settings.documents_web_enabled is True
    assert settings.documents_search_timeout_seconds == 8.0
    assert settings.library_dir == "./library"
    assert settings.generation_steps == 10
    assert settings.generation_step_delay_seconds == 0.3
    assert settings.video_format == "mp4"
    assert settings.retry_max_attempts == 3
    assert settings.circuit_failure_threshold == 5
    assert settings.rate_limit_capacity == 4


def test_env_vars_override_defaults(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_FACTORY_APP_NAME", "my-factory")
    monkeypatch.setenv("CONTENT_FACTORY_STRONG_LLM_ENABLED", "true")
    monkeypatch.setenv("CONTENT_FACTORY_PROVIDER_STRATEGY", "quality_first")
    settings = Settings()
    assert settings.app_name == "my-factory"
    assert settings.strong_llm_enabled is True
    assert settings.provider_strategy == "quality_first"


def test_constructor_kwargs_win_over_env(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_FACTORY_APP_NAME", "from-env")
    settings = Settings(app_name="from-kwarg")
    assert settings.app_name == "from-kwarg"


def test_strategy_is_restricted() -> None:
    with pytest.raises(ValidationError):
        Settings(provider_strategy="sideways")  # type: ignore[arg-type]
