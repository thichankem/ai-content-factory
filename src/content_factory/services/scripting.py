"""Script drafting, prompt construction and style selection."""

from __future__ import annotations

from .. import script_engine
from ..models import Project, ProjectStatus, ScriptAnalysis, ScriptAnalyzeRequest
from .errors import (
    NotFoundError,
    StateConflictError,
)
from .research import ResearchMixin


class ScriptingMixin(ResearchMixin):
    """Script drafting, prompt construction and style selection."""

    async def generate_script(self, project_id: str) -> Project:
        """Gather research (if missing), then draft a script grounded in it."""
        project = self.get_project(project_id)
        if project.status not in (ProjectStatus.DRAFT, ProjectStatus.SCRIPT_REVIEW):
            raise StateConflictError(
                f"Cannot generate a script while status is '{project.status.value}'."
            )
        if project.research is None:
            await self.research(project_id)
            project = self.get_project(project_id)
        prompt = self._build_prompt(project)
        result = await self._providers.generate(prompt)
        project.script = result.text
        project.source_rights_confirmed = False
        project.provider_used = result.provider
        project.agent_used = None
        project.error = None
        if project.status == ProjectStatus.DRAFT:
            self._transition(project, ProjectStatus.SCRIPT_REVIEW)
        self._refresh_analysis(project)
        return self._store.save(project)

    def _build_prompt(self, project: Project) -> str:
        """Render the contract-style prompt for the configured strong model."""
        return script_engine.build_script_prompt(
            topic=project.topic,
            language=project.target_language,
            target_seconds=project.duration_target_seconds,
            style=self._presets.resolve(project.script_style),
            research=project.research,
            grounding=project.grounding,
        )

    def analyze_project_script(
        self, project_id: str, request: ScriptAnalyzeRequest
    ) -> ScriptAnalysis:
        """Plan and lint a script without persisting anything."""
        project = self.get_project(project_id)
        style = self._presets.resolve(request.style or project.script_style)
        return script_engine.analyze_script(
            request.script if request.script is not None else project.script,
            language=project.target_language,
            target_seconds=project.duration_target_seconds,
            style=style,
            research=project.research,
        )

    def select_script_style(self, project_id: str, name: str) -> Project:
        """Choose which preset drives prompt building and linting."""
        project = self.get_project(project_id)
        style = self._presets.get(name)
        if style is None:
            raise NotFoundError(f"No script style named '{name}'.")
        project.script_style = style.name
        self._refresh_analysis(project)
        return self._store.save(project)
