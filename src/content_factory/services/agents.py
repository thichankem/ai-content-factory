"""Bridge to external AI agents: catalogs, briefs and imported results."""

from __future__ import annotations

from .. import agent_bridge, script_engine, smart
from ..models import (
    AgentCatalog,
    AgentResultCreate,
    Project,
    ProjectStatus,
    ScriptStyle,
    utcnow,
)
from ..scenes import build_video_project
from .errors import (
    StateConflictError,
)
from .scripting import ScriptingMixin


class AgentsMixin(ScriptingMixin):
    """Bridge to external AI agents: catalogs, briefs and imported results."""

    # --- External AI agent bridge ---------------------------------------------

    def agent_catalog(self) -> AgentCatalog:
        """Describe every AI agent and preset the operator can route work to."""
        return AgentCatalog(
            strategy=self._settings.provider_strategy,
            tts_engine=self._settings.tts_engine,
            agents=self._providers.catalog(),
            preset_styles=self._presets.names(),
        )

    def export_brief(self, project_id: str, agent: str | None = None) -> str:
        """Render the Markdown brief handed to an external AI agent."""
        project = self.get_project(project_id)
        style = self._presets.resolve(project.script_style)
        analysis = None
        if project.script:
            analysis = script_engine.analyze_script(
                project.script,
                language=project.target_language,
                target_seconds=project.duration_target_seconds,
                style=style,
                research=project.research,
            )
        return agent_bridge.render_brief(
            project, style=style, analysis=analysis, agent=agent
        )

    def import_agent_result(self, project_id: str, data: AgentResultCreate) -> Project:
        """Apply a Markdown result produced by an external AI agent.

        Source rights are never auto-confirmed: whatever the agent returns,
        a human still has to confirm rights before the script can be approved.
        """
        project = self.get_project(project_id)
        result = agent_bridge.parse_agent_result(data.markdown)
        if result.is_empty:
            raise StateConflictError(
                "The agent reply contained no script, scenes, or style block."
            )
        if result.script:
            if project.status not in (
                ProjectStatus.DRAFT,
                ProjectStatus.SCRIPT_REVIEW,
            ):
                raise StateConflictError(
                    "Cannot import a new script while status is "
                    f"'{project.status.value}'."
                )
            project.script = result.script.strip()
            project.source_rights_confirmed = False
            if project.status == ProjectStatus.DRAFT:
                self._transition(project, ProjectStatus.SCRIPT_REVIEW)
        style = self._style_from_agent(result.style)
        if style is not None:
            project.script_style = style.name
        if result.scenes:
            self._apply_agent_scenes(project, result.scenes)
        project.agent_used = data.agent
        project.provider_used = f"agent:{data.agent}"
        project.error = None
        self._refresh_analysis(project)
        return self._store.save(project)

    def _style_from_agent(self, payload: dict | None) -> ScriptStyle | None:
        """Validate and persist a style block returned by an agent."""
        if not payload:
            return None
        candidate = dict(payload)
        candidate.setdefault("name", "agent-style")
        candidate.pop("builtin", None)
        try:
            style = ScriptStyle.model_validate(candidate)
        except Exception:
            return None
        try:
            return self._presets.save(style)
        except Exception:
            return style

    def _apply_agent_scenes(self, project: Project, scenes: list[dict]) -> None:
        """Merge agent-authored scenes into the editable video project."""
        if project.video_project is None:
            if not project.script:
                return
            project.video_project = build_video_project(
                project.script,
                project.duration_target_seconds,
                project.target_language,
            )
        existing = project.video_project.scenes
        for index, incoming in enumerate(scenes):
            if index >= len(existing):
                break
            scene = existing[index]
            if incoming.get("label"):
                scene.label = str(incoming["label"])[:120]
            if incoming.get("text"):
                scene.text = str(incoming["text"])
            if incoming.get("narration"):
                scene.narration = str(incoming["narration"])
            if incoming.get("background"):
                scene.background = str(incoming["background"])
        smart.auto_fit_durations(project.video_project)
        project.video_project.updated_at = utcnow()
