"""In-memory, thread-safe project store."""

from __future__ import annotations

import threading
import uuid

from .models import Project, ProjectCreate, utcnow


class StoreConflictError(RuntimeError):
    """Raised when a compare-and-save detects a concurrent modification."""


class Store:
    """Process-local project repository (vertical-slice storage).

    Projects are stored by live reference: whoever fetches a project and
    mutates it without ``save`` mutates the stored copy in place. Writers
    that must not lose a concurrent update should use
    :meth:`save_if_unchanged` instead of a blind :meth:`save`.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._projects: dict[str, Project] = {}

    def create(self, data: ProjectCreate) -> Project:
        project = Project(
            id=uuid.uuid4().hex[:12],
            name=data.name,
            topic=data.topic,
            target_language=data.target_language,
            duration_target_seconds=data.duration_target_seconds,
        )
        with self._lock:
            self._projects[project.id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        with self._lock:
            return self._projects.get(project_id)

    def list(self) -> list[Project]:
        with self._lock:
            return list(self._projects.values())

    def save(self, project: Project) -> Project:
        project.updated_at = utcnow()
        with self._lock:
            self._projects[project.id] = project
        return project

    def save_if_unchanged(self, project: Project, expected: Project) -> Project:
        """Compare-and-save: store the project only if the store still holds it.

        The comparison and the write happen under one lock, so an editor that
        lands between the caller's read and its save is detected and rejected
        instead of being silently overwritten (a lost update).

        ``expected`` must be a snapshot taken from a working copy (as in the
        render flow): the caller mutates the copy, and the store compares its
        own stored object against the untouched snapshot. Mutating the stored
        object in place defeats the check — the baseline is then already gone.
        Callers map :class:`StoreConflictError` onto their own conflict type.
        """
        with self._lock:
            stored = self._projects.get(project.id)
            if stored is None or stored != expected:
                raise StoreConflictError(
                    f"Project '{project.id}' changed concurrently; save rejected."
                )
            project.updated_at = utcnow()
            self._projects[project.id] = project
            return project
