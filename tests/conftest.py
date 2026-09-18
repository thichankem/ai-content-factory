"""Shared fixtures for the test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings
from content_factory.service import ContentFactoryService


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Deterministic, offline settings with every provider disabled."""
    return Settings(
        template_enabled=False,
        money_printer_enabled=False,
        strong_llm_enabled=False,
        documents_web_enabled=False,
        retry_max_attempts=1,
        retry_base_delay_seconds=0.0,
        retry_max_delay_seconds=0.0,
        retry_jitter_ratio=0.0,
        generation_steps=1,
        generation_step_delay_seconds=0.005,
        library_dir=str(tmp_path / "library"),
        library_db_path=str(tmp_path / "library" / ".index.db"),
        media_dir=str(tmp_path / "media"),
        presets_dir=str(tmp_path / "presets"),
    )


@pytest.fixture
def service(settings: Settings) -> ContentFactoryService:
    return ContentFactoryService(settings)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def client_with_template(settings: Settings) -> TestClient:
    """Client whose only enabled provider is the built-in template."""
    return TestClient(
        create_app(settings.model_copy(update={"template_enabled": True}))
    )


@pytest.fixture
def sample_project(service: ContentFactoryService):
    from content_factory.models import ProjectCreate

    return service.create_project(
        ProjectCreate(
            name="Demo",
            topic="Why morning light changes how cities feel",
            target_language="vi",
            duration_target_seconds=45,
        )
    )
