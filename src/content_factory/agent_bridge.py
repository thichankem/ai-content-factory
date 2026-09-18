"""Markdown bridge for external AI agents and human editors.

The factory does not care *which* agent drafts a script. This module renders
everything an agent needs into one self-contained Markdown brief (``brief.md``)
that can be pasted into Claude Code, Codex, DeepSeek, Gemini, or any chat
window — and parses the agent's reply back into structured edits.

The contract is intentionally plain text:

* :func:`render_brief` writes front matter, the style contract, the research
  grounding, the current script, and the scene table, then finishes with an
  exact "what to return" recipe.
* :func:`parse_agent_result` reads fenced blocks back out: ``script`` for
  narration, ``json scenes`` for a scene list, ``json style`` for preset
  overrides. A bare reply without fences still works if it contains section
  markers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .models import Project, ScriptAnalysis, ScriptStyle, utcnow
from .presets import style_to_markdown

_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
_SECTION_MARKER_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$", re.MULTILINE)

_SCRIPT_INFOS = {"script", "narration", "markdown", "md", "text", "script md"}
_SCENE_INFOS = {
    "scenes",
    "json scenes",
    "scene",
    "timeline",
    "video",
    "video project",
    "video-project",
}
_STYLE_INFOS = {"style", "json style", "preset", "script style", "script-style"}
_JSON_INFOS = {"json", "jsonc"}


@dataclass
class AgentResult:
    """Structured output produced by an external AI agent."""

    script: str | None = None
    scenes: list[dict[str, Any]] = field(default_factory=list)
    style: dict[str, Any] | None = None
    notes: str = ""

    @property
    def is_empty(self) -> bool:
        """True when the agent returned nothing usable."""
        return not self.script and not self.scenes and not self.style


def _normalize_info(info: str) -> str:
    return re.sub(r"\s+", " ", (info or "").replace(":", " ").strip().lower())


def _coerce_scenes(payload: Any) -> list[dict[str, Any]] | None:
    """Normalize a scene payload into a list of plain dicts."""
    if isinstance(payload, dict):
        payload = payload.get("scenes")
    if not isinstance(payload, list):
        return None
    scenes: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        scene: dict[str, Any] = {}
        for key in ("label", "text", "narration", "transition", "background"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                scene[key] = value.strip()
        duration = item.get("duration_seconds")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            scene["duration_seconds"] = float(duration)
        if scene.get("text") or scene.get("narration"):
            scenes.append(scene)
    return scenes or None


def parse_agent_result(markdown: str) -> AgentResult:
    """Parse an agent reply into structured edits.

    Fenced blocks win; anything unclassified is kept as ``notes``. When no
    ``script`` block exists but the body contains ``[Section]`` markers, the
    body itself is treated as the script.
    """
    result = AgentResult()
    text = markdown or ""
    leftovers = _FENCE_RE.sub("\n", text)

    for match in _FENCE_RE.finditer(text):
        info = _normalize_info(match.group(1))
        # "json scenes" and "scenes" mean the same thing.
        bare = re.sub(r"^(json|jsonc|yaml)\s+", "", info).strip()
        payload = match.group(2).strip()
        if not payload:
            continue
        if bare in _SCRIPT_INFOS:
            result.script = _join_script(result.script, payload)
            continue
        if bare in _SCENE_INFOS:
            scenes = _safe_json(payload)
            parsed = _coerce_scenes(scenes) if scenes is not None else None
            if parsed:
                result.scenes = parsed
            else:
                result.notes = _append_note(result.notes, payload)
            continue
        if bare in _STYLE_INFOS:
            style = _safe_json(payload)
            if isinstance(style, dict):
                result.style = style
            else:
                result.notes = _append_note(result.notes, payload)
            continue
        if info in _JSON_INFOS or info.startswith("json"):
            data = _safe_json(payload)
            if data is not None and _classify_json(data, result):
                continue
        if info in {"notes", "note", "commentary"}:
            result.notes = _append_note(result.notes, payload)
            continue
        result.notes = _append_note(result.notes, payload)

    if result.script is None:
        candidate = _script_from_body(leftovers)
        if candidate:
            result.script = candidate
    if not result.notes and leftovers.strip():
        # Unfenced prose is the agent talking to the human — keep it as notes.
        result.notes = leftovers.strip()
    if not result.notes and result.is_empty:
        stripped = _script_from_body(text)
        if stripped:
            result.script = stripped
    return result


def _classify_json(data: Any, result: AgentResult) -> bool:
    """Route a bare ``json`` block by the shape of its payload."""
    if data is None:
        return False
    if isinstance(data, list):
        scenes = _coerce_scenes(data)
        if scenes:
            result.scenes = scenes
            return True
        return False
    if isinstance(data, dict):
        if "scenes" in data:
            scenes = _coerce_scenes(data)
            if scenes:
                result.scenes = scenes
                return True
        if isinstance(data.get("script"), str):
            result.script = _join_script(result.script, data["script"].strip())
            return True
        if {"structure", "tone", "name"} & set(data):
            result.style = data
            return True
    return False


def _safe_json(payload: str) -> Any:
    try:
        return json.loads(payload)
    except (ValueError, TypeError):
        return None


def _join_script(existing: str | None, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n\n{addition}"


def _append_note(existing: str, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n\n{addition}"


def _script_from_body(body: str) -> str | None:
    """Recover a script from an unfenced reply."""
    text = body.strip()
    if not text:
        return None
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    heading = re.search(
        r"^#{1,6}\s*(script|narration)\s*$", text, re.IGNORECASE | re.MULTILINE
    )
    candidate = text[heading.end() :] if heading else text
    candidate = candidate.strip()
    if not candidate:
        return None
    if _SECTION_MARKER_RE.search(candidate):
        return candidate
    return None


def render_brief(
    project: Project,
    *,
    style: ScriptStyle,
    analysis: ScriptAnalysis | None = None,
    agent: str | None = None,
) -> str:
    """Render a complete Markdown brief for an external AI agent or editor."""
    research = project.research
    lines: list[str] = [
        "---",
        f"project_id: {project.id}",
        f"name: {project.name}",
        f"topic: {project.topic}",
        f"target_language: {project.target_language}",
        f"duration_target_seconds: {project.duration_target_seconds}",
        f"status: {project.status.value}",
        f"style: {style.name}",
        f"agent_hint: {agent or 'any'}",
        f"generated_at: {utcnow().isoformat()}",
        "---",
        "",
        f"# Agent brief — {project.name}",
        "",
        "You are editing one asset of an AI-assisted short-form video pipeline.",
        "Return only the blocks described in **How to reply** at the bottom.",
        "",
        "## 1. Mission",
        f"- Produce an original narration script about: **{project.topic}**.",
        f"- Spoken language: **{project.target_language}**.",
        f"- Target runtime: **{project.duration_target_seconds} seconds**.",
        "- Learn facts, structure, and pacing from the references below, but",
        "  never reuse their sentences. Transform, do not copy.",
        "",
        "## 2. Style contract",
        "",
        style_to_markdown(style).strip(),
        "",
        "## 3. Reference material",
        "",
    ]
    if research is not None and research.sources:
        for source in research.sources:
            lines.append(f"- **{source.title}** ({source.source_type})")
            if source.summary:
                lines.append(f"  - {source.summary.strip()}")
            for highlight in source.highlights[:2]:
                lines.append(f"  - {highlight.strip()}")
        if research.key_facts:
            lines.extend(["", "**Key facts**", ""])
            lines.extend(f"- {fact}" for fact in research.key_facts)
    else:
        lines.append("- No research gathered yet. Run `/research` first if you need")
        lines.append("  grounding, or rely on general knowledge and mark it as such.")

    lines.extend(["", "## 4. Current script", ""])
    lines.append("```script")
    lines.append((project.script or "").strip() or "(empty — write a new one)")
    lines.append("```")

    if analysis is not None:
        lines.extend(["", "## 5. Automatic analysis", ""])
        lines.append(
            f"- Estimated narration: **{analysis.plan.estimated_seconds}s** "
            f"(target {analysis.plan.target_seconds}s, "
            f"fits={analysis.plan.fits_target})."
        )
        lines.append(f"- Readiness score: **{analysis.score}/100**.")
        for issue in analysis.issues:
            hint = f" — {issue.hint}" if issue.hint else ""
            lines.append(
                f"- `{issue.severity.value}` {issue.code}: {issue.message}{hint}"
            )
        if not analysis.issues:
            lines.append("- No findings. Nice.")

    if project.video_project is not None and project.video_project.scenes:
        lines.extend(
            [
                "",
                "## 6. Scene timeline",
                "",
                "| # | label | seconds | text |",
                "| - | ----- | ------- | ---- |",
            ]
        )
        for index, scene in enumerate(project.video_project.scenes):
            text = (scene.text or "").replace("|", "\\|")
            lines.append(
                f"| {index} | {scene.label} | {scene.duration_seconds} | {text} |"
            )

    lines.extend(
        [
            "",
            "## How to reply",
            "",
            "Return the assets you changed as fenced blocks. Omit what you did",
            "not touch. Keep the narration block first.",
            "",
            "```script",
            "[Hook]",
            "your opening line",
            "[Turn]",
            "...",
            "```",
            "",
            "```json scenes",
            '[{"label": "Hook", "text": "on-screen text", "narration": "spoken line"}]',
            "```",
            "",
            "```json style",
            '{"name": "my-style", "tone": "...", "sentence_max_units": 12}',
            "```",
            "",
        ]
    )
    return "\n".join(lines)
