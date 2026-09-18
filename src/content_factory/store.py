"""In-memory, thread-safe project store."""

from __future__ import annotations

import threading
import uuid

from .models import Project, ProjectCreate, utcnow


class Store:
    """Process-local project repository (vertical-slice storage)."""

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
