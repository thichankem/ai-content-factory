"""Tests for the in-memory project store."""

from __future__ import annotations

import pytest

from content_factory.models import ProjectCreate, ProjectStatus
from content_factory.store import Store, StoreConflictError


def test_create_and_get_roundtrip() -> None:
    store = Store()
    project = store.create(
        ProjectCreate(
            name="A", topic="B", target_language="en", duration_target_seconds=30
        )
    )
    assert project.status == ProjectStatus.DRAFT
    fetched = store.get(project.id)
    assert fetched is not None
    assert fetched.id == project.id
    assert fetched.name == "A"
    assert fetched.topic == "B"


def test_get_missing_returns_none() -> None:
    assert Store().get("does-not-exist") is None


def test_list_returns_all_projects() -> None:
    store = Store()
    first = store.create(ProjectCreate(name="A", topic="T"))
    second = store.create(ProjectCreate(name="B", topic="T"))
    ids = {p.id for p in store.list()}
    assert ids == {first.id, second.id}


def test_save_bumps_updated_at() -> None:
    store = Store()
    project = store.create(ProjectCreate(name="A", topic="T"))
    before = project.updated_at
    project.script = "Hello"
    saved = store.save(project)
    assert saved.updated_at >= before
    assert store.get(project.id).script == "Hello"


def test_ids_are_unique() -> None:
    store = Store()
    ids = {store.create(ProjectCreate(name=f"N{i}", topic="T")).id for i in range(50)}
    assert len(ids) == 50


def test_save_if_unchanged_saves_when_expected_matches() -> None:
    store = Store()
    project = store.create(ProjectCreate(name="A", topic="T"))
    working = project.model_copy(deep=True)
    snapshot = working.model_copy(deep=True)
    working.script = "Hello"
    saved = store.save_if_unchanged(working, snapshot)
    assert store.get(project.id).script == "Hello"
    assert saved.updated_at >= snapshot.updated_at


def test_save_if_unchanged_rejects_concurrent_change() -> None:
    store = Store()
    project = store.create(ProjectCreate(name="A", topic="T"))
    stale = project.model_copy(deep=True)
    concurrent = project.model_copy(deep=True)
    concurrent.name = "B"
    store.save(concurrent)
    project.script = "Hello"
    with pytest.raises(StoreConflictError):
        store.save_if_unchanged(project, stale)
    # The concurrent editor's state survives; our stale write is discarded.
    stored = store.get(project.id)
    assert stored.name == "B"
    assert stored.script is None


def test_save_if_unchanged_rejects_unknown_project() -> None:
    store = Store()
    project = store.create(ProjectCreate(name="A", topic="T"))
    ghost = project.model_copy(deep=True)
    ghost.id = "missing-id"
    with pytest.raises(StoreConflictError):
        store.save_if_unchanged(ghost, ghost)
