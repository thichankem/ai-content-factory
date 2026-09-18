"""Tests for the external AI agent Markdown bridge."""

from __future__ import annotations

import pytest

from content_factory.agent_bridge import parse_agent_result, render_brief
from content_factory.models import (
    AgentResultCreate,
    ApprovalCreate,
    ApprovalStage,
    ApprovalVerdict,
    Project,
    ProjectCreate,
    ProjectStatus,
    ScriptUpdate,
)
from content_factory.presets import PresetLibrary
from content_factory.service import ContentFactoryService, StateConflictError

REPLY = """Here is the rewrite you asked for.

```script
[Hook]
The city whispers before it wakes.

[Turn]
Trucks and shutters are the only choir.

[Payoff]
Listen at 5am and you hear who really runs this place.
```

```json scenes
[{"label": "Hook", "text": "5am", "narration": "The city whispers before it wakes."}]
```

```json style
{"name": "agent-style", "tone": "hushed", "sentence_max_units": 10}
```
"""


def test_render_brief_contains_contract_and_context(
    service: ContentFactoryService, sample_project: Project
) -> None:
    project = service.update_script(
        sample_project.id,
        ScriptUpdate(script="[Hook]\nMorning light.", source_rights_confirmed=False),
    )
    brief = render_brief(project, style=PresetLibrary().resolve("viral-short"))
    assert f"project_id: {project.id}" in brief
    assert "# Agent brief" in brief
    assert "## 2. Style contract" in brief
    assert "## How to reply" in brief
    assert "```script" in brief
    assert "Target runtime" in brief


def test_parse_agent_result_extracts_every_block() -> None:
    result = parse_agent_result(REPLY)
    assert result.script is not None
    assert "[Hook]" in result.script
    assert len(result.scenes) == 1
    assert result.scenes[0]["label"] == "Hook"
    assert result.style is not None
    assert result.style["name"] == "agent-style"
    assert "rewrite you asked for" in result.notes
    assert result.is_empty is False


def test_parse_agent_result_handles_unfenced_reply() -> None:
    result = parse_agent_result("[Hook]\nJust markers, no fences.")
    assert result.script is not None
    assert "[Hook]" in result.script


def test_parse_agent_result_detects_json_prefixes() -> None:
    result = parse_agent_result(
        "```json script\n[Hook]\nSpoken line.\n```\n\n"
        '```json scenes\n{"scenes": [{"text": "A", "narration": "B"}]}\n```\n'
    )
    assert result.script is not None
    assert result.scenes == [{"text": "A", "narration": "B"}]


def test_parse_agent_result_without_fences_or_markers_is_empty() -> None:
    result = parse_agent_result("I could not do the task, sorry.")
    assert result.is_empty is True


def test_parse_agent_result_ignores_invalid_scene_json() -> None:
    result = parse_agent_result("```json scenes\nnot json at all\n```\n")
    assert result.scenes == []
    assert "not json at all" in result.notes


def test_import_agent_result_applies_script_and_style(
    service: ContentFactoryService, sample_project: Project
) -> None:
    project = service.import_agent_result(
        sample_project.id, AgentResultCreate(markdown=REPLY, agent="claude-code")
    )
    assert project.status == ProjectStatus.SCRIPT_REVIEW
    assert project.script is not None
    assert "[Hook]" in project.script
    # Rights are never auto-confirmed, even for an AI agent reply.
    assert project.source_rights_confirmed is False
    assert project.agent_used == "claude-code"
    assert project.provider_used == "agent:claude-code"
    assert project.script_style == "agent-style"
    assert service.get_script_style("agent-style") is not None
    assert project.script_plan is not None
    assert project.video_project is not None
    assert project.video_project.scenes[0].label == "Hook"


def test_import_agent_result_rejects_empty_reply(
    service: ContentFactoryService, sample_project: Project
) -> None:
    with pytest.raises(StateConflictError):
        service.import_agent_result(
            sample_project.id, AgentResultCreate(markdown="nothing useful")
        )


def test_import_agent_result_is_blocked_after_approval(
    service: ContentFactoryService, sample_project: Project
) -> None:
    service.update_script(
        sample_project.id,
        ScriptUpdate(script="[Hook]\nReady.", source_rights_confirmed=True),
    )
    service.approve(
        sample_project.id,
        ApprovalCreate(stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.APPROVED),
    )
    with pytest.raises(StateConflictError):
        service.import_agent_result(
            sample_project.id, AgentResultCreate(markdown=REPLY)
        )


def test_export_brief_includes_analysis_for_reviewable_script(
    service: ContentFactoryService, sample_project: Project
) -> None:
    service.update_script(
        sample_project.id,
        ScriptUpdate(script="[Hook]\nJust an ordinary statement."),
    )
    brief = service.export_brief(sample_project.id, agent="codex")
    assert "agent_hint: codex" in brief
    assert "## 5. Automatic analysis" in brief
    assert "weak_hook" in brief


def test_agent_catalog_lists_styles_and_agents(
    service: ContentFactoryService, sample_project: ProjectCreate
) -> None:
    catalog = service.agent_catalog()
    assert catalog.strategy == "cost_first"
    assert "viral-short" in catalog.preset_styles
    assert catalog.agents == []
