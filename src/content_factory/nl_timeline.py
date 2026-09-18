"""Conversational timeline assistant — edit a video by natural language.

Turns a plain-English (or Vietnamese) instruction into a concrete timeline
operation, so the operator can say things like:

  * "speed up the intro to 1.5x"
  * "cắt bớt đoạn thừa" (trim dead air)
  * "delete scene 3" / "xoá cảnh 3"
  * "merge the hook into the next scene"
  * "add a marker at 2 minutes"
  * "turn up the volume of the payoff to 2x"

This is a rule-based parser + executor over :mod:`content_factory.timeline`
operations — deterministic, offline, and safe. It never bypasses the two human
gates; it only edits the timeline the same way the NLE UI would.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from . import timeline
from .models import VideoProject
from .smart import auto_fit_durations, beat_sync


class TimelineIntent(StrEnum):
    """The recognized editing actions."""

    SPEED_UP = "speed_up"
    SLOW_DOWN = "slow_down"
    TRIM = "trim"
    DELETE_SCENE = "delete_scene"
    MERGE_SCENE = "merge_scene"
    SPLIT_SCENE = "split_scene"
    MOVE_SCENE = "move_scene"
    SET_VOLUME = "set_volume"
    ADD_MARKER = "add_marker"
    REMOVE_MARKER = "remove_marker"
    DUPLICATE_SCENE = "duplicate_scene"
    AUTO_FIT = "auto_fit"
    BEAT_SYNC = "beat_sync"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ParsedCommand:
    """A natural-language instruction reduced to a structured action."""

    intent: TimelineIntent
    target: str | None = None
    params: dict[str, float | str] = field(default_factory=dict)
    matched: str = ""
    description: str = ""


_NUMBER = r"(\d+(?:\.\d+)?)"

# Intent -> (regex, params extractor). Ordered: more specific first.
_INTENTS: tuple[tuple[TimelineIntent, str], ...] = (
    (
        TimelineIntent.MOVE_SCENE,
        rf"\b(move|di chuyển|đưa)\b.*?\b(scene|cảnh)?\s*(.+?)\s*\b(to|before|after|lên|xuống|trước|sau|tới)\b\s*{_NUMBER}",  # noqa: E501
    ),
    (
        TimelineIntent.SPEED_UP,
        rf"\b(speed up|accelerate|faster|tăng tốc|nhanh hơn|tăng tốc độ)\b.*?{_NUMBER}\s*x",  # noqa: E501
    ),
    (
        TimelineIntent.SLOW_DOWN,
        rf"\b(slow down|decelerate|slower|giảm tốc|chậm lại|giảm tốc độ)\b.*?{_NUMBER}\s*x",  # noqa: E501
    ),
    (
        TimelineIntent.SET_VOLUME,
        rf"\b(volume|âm lượng|tiếng)\b.*?{_NUMBER}\s*x",
    ),
    (
        TimelineIntent.ADD_MARKER,
        rf"\b(add|thêm)\b.*?\b(marker|mốc)\b.*?\b(at|lúc|ở)?\s*{_NUMBER}\s*(min|minutes|phút|sec|seconds|giây)?",
    ),
    (
        TimelineIntent.REMOVE_MARKER,
        r"\b(remove|delete|xoá|bỏ)\b.*?\b(marker|mốc)\b",
    ),
    (
        TimelineIntent.MERGE_SCENE,
        r"\b(merge|ghép|nối)\b.*?\b(scene|cảnh)?\s*(.+)$",
    ),
    (
        TimelineIntent.SPLIT_SCENE,
        r"\b(split|tách)\b.*?\b(scene|cảnh)?\s*(.+)$",
    ),
    (
        TimelineIntent.DUPLICATE_SCENE,
        r"\b(duplicate|copy|nhân đôi|sao chép)\b.*?\b(scene|cảnh)?\s*(.+)$",
    ),
    (
        TimelineIntent.DELETE_SCENE,
        r"\b(delete|remove|xoá|bỏ)\b.*?\b(scene|cảnh)?\s*(.+)$",
    ),
    (
        TimelineIntent.TRIM,
        r"\b(trim|cut|bỏ đoạn thừa|cắt bớt|remove dead air)\b",
    ),
    (
        TimelineIntent.AUTO_FIT,
        r"\b(auto.?fit|fit durations|tự căn|cân chỉnh thời lượng)\b",
    ),
    (
        TimelineIntent.BEAT_SYNC,
        r"\b(beat.?sync|snap to beat|khớp nhịp)\b",
    ),
)


def _extract_number(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def parse_command(text: str) -> ParsedCommand:
    """Reduce a natural-language instruction to a :class:`ParsedCommand`."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return ParsedCommand(TimelineIntent.UNKNOWN, description="empty instruction")

    for intent, pattern in _INTENTS:
        match = re.search(pattern, lowered)
        if not match:
            continue
        params: dict[str, float | str] = {}

        if intent in (TimelineIntent.SPEED_UP, TimelineIntent.SLOW_DOWN):
            number = _extract_number(match.group(0))
            speed = (
                float(number)
                if number
                else (1.5 if intent == TimelineIntent.SPEED_UP else 0.5)
            )
            params["speed"] = speed
            target = _scene_token(text)
            return ParsedCommand(
                intent,
                target=target,
                params=params,
                matched=match.group(0),
                description=f"{intent.value} {target or 'timeline'}",
            )

        if intent == TimelineIntent.SET_VOLUME:
            number = _extract_number(match.group(0))
            params["volume"] = float(number) if number else 1.5
            target = _scene_token(text)
            return ParsedCommand(
                intent,
                target=target,
                params=params,
                matched=match.group(0),
                description=f"volume {target or ''}".strip(),
            )

        if intent == TimelineIntent.ADD_MARKER:
            number = _extract_number(match.group(0))
            seconds = float(number) if number else 0.0
            if "min" in match.group(0) or "phút" in match.group(0):
                seconds *= 60.0
            params["time"] = seconds
            return ParsedCommand(
                intent,
                params=params,
                matched=match.group(0),
                description=f"marker at {seconds:.0f}s",
            )

        if intent == TimelineIntent.REMOVE_MARKER:
            return ParsedCommand(
                intent, matched=match.group(0), description="remove marker"
            )

        if intent == TimelineIntent.MOVE_SCENE:
            target = match.group(3) if len(match.groups()) >= 3 else None
            number = _extract_number(match.group(0))
            params["to_index"] = max(0, int(float(number)) - 1) if number else 0
            return ParsedCommand(
                intent,
                target=target,
                params=params,
                matched=match.group(0),
                description=f"move {target}",
            )

        if intent in (
            TimelineIntent.DELETE_SCENE,
            TimelineIntent.MERGE_SCENE,
            TimelineIntent.SPLIT_SCENE,
            TimelineIntent.DUPLICATE_SCENE,
        ):
            target = match.group(len(match.groups())) if match.groups() else None
            return ParsedCommand(
                intent,
                target=target,
                matched=match.group(0),
                description=f"{intent.value} {target or ''}".strip(),
            )

        if intent == TimelineIntent.TRIM:
            return ParsedCommand(
                intent, matched=match.group(0), description="trim dead air"
            )

        if intent == TimelineIntent.AUTO_FIT:
            return ParsedCommand(
                intent, matched=match.group(0), description="auto-fit durations"
            )

        if intent == TimelineIntent.BEAT_SYNC:
            number = _extract_number(match.group(0))
            params["bpm"] = float(number) if number else 120.0
            return ParsedCommand(
                intent, params=params, matched=match.group(0), description="beat-sync"
            )

    return ParsedCommand(TimelineIntent.UNKNOWN, description="unrecognized instruction")


def _scene_token(text: str) -> str | None:
    """Best-effort scene reference from free text (label-like token)."""
    lowered = (text or "").lower()
    # "the <label> scene" -> capture the label that precedes "scene".
    match = re.search(r"\bthe\s+([a-z0-9\- ]+?)\s+scene\b", lowered)
    if match:
        return match.group(1).strip()
    # "scene <label>" / "cảnh <label>".
    match = re.search(r"\b(?:scene|cảnh)\s+([a-z0-9]+)", lowered)
    if match:
        return match.group(1).strip()
    # "the <label>" (e.g. "the intro", "the hook").
    match = re.search(r"\bthe\s+([a-z0-9\-]+)", lowered)
    if match:
        return match.group(1).strip()
    return None


def resolve_scene_index(project: VideoProject, target: str | None) -> int | None:
    """Resolve a scene reference (label, index, first/last) to an index."""
    if target is None or not project.scenes:
        return None
    token = target.strip().lower()
    if token in ("first", "đầu", "đầu tiên", "intro"):
        return 0
    if token in ("last", "cuối", "cuối cùng", "outro"):
        return len(project.scenes) - 1
    number = re.search(r"(\d+)\s*$", token)
    if number:
        index = int(number.group(1)) - 1
        if 0 <= index < len(project.scenes):
            return index
    # Match a scene whose label is contained in the token, or vice versa.
    for index, scene in enumerate(project.scenes):
        label = (scene.label or "").lower()
        if label and (label in token or token in label):
            return index
    for index, scene in enumerate(project.scenes):
        text = (scene.text or "").lower()
        if token and token in text:
            return index
    return None


def apply_command(
    project: VideoProject, text: str
) -> tuple[VideoProject, ParsedCommand]:
    """Parse ``text`` and apply the resulting edit to ``project``.

    Returns ``(updated_project, command)``. On an unrecognized instruction or a
    scene that cannot be resolved, the project is returned unchanged and the
    command carries an explanatory description.
    """
    command = parse_command(text)
    if command.intent == TimelineIntent.UNKNOWN:
        return project, command

    index = resolve_scene_index(project, command.target)
    if command.intent in (
        TimelineIntent.SPEED_UP,
        TimelineIntent.SLOW_DOWN,
        TimelineIntent.DELETE_SCENE,
        TimelineIntent.MERGE_SCENE,
        TimelineIntent.SPLIT_SCENE,
        TimelineIntent.MOVE_SCENE,
        TimelineIntent.SET_VOLUME,
        TimelineIntent.DUPLICATE_SCENE,
    ):
        if index is None:
            return project, ParsedCommand(
                command.intent,
                target=command.target,
                params=command.params,
                matched=command.matched,
                description="could not identify the target scene",
            )
        scene_id = project.scenes[index].id

    try:
        if command.intent in (TimelineIntent.SPEED_UP, TimelineIntent.SLOW_DOWN):
            project = timeline.set_speed(
                project, scene_id, float(command.params["speed"])
            )
        elif command.intent == TimelineIntent.DELETE_SCENE:
            project = timeline.delete_scene(project, scene_id)
        elif command.intent == TimelineIntent.MERGE_SCENE:
            project = timeline.merge_scene(project, scene_id)
        elif command.intent == TimelineIntent.SPLIT_SCENE:
            project = timeline.split_scene(project, scene_id)
        elif command.intent == TimelineIntent.MOVE_SCENE:
            project = timeline.move_scene(
                project, scene_id, int(command.params.get("to_index", 0))
            )
        elif command.intent == TimelineIntent.SET_VOLUME:
            project = timeline.set_audio(
                project, scene_id, volume=float(command.params.get("volume", 1.5))
            )
        elif command.intent == TimelineIntent.DUPLICATE_SCENE:
            project = timeline.duplicate_scene(project, scene_id)
        elif command.intent in (TimelineIntent.TRIM, TimelineIntent.AUTO_FIT):
            project = auto_fit_durations(project)
        elif command.intent == TimelineIntent.BEAT_SYNC:
            project = beat_sync(project, int(command.params.get("bpm", 120)))
        elif command.intent == TimelineIntent.ADD_MARKER:
            project = timeline.add_marker(
                project, float(command.params.get("time", 0.0)), label="command"
            )
        elif command.intent == TimelineIntent.REMOVE_MARKER:
            if project.markers:
                project = timeline.remove_marker(project, project.markers[0].id)
    except ValueError as exc:
        return project, ParsedCommand(
            command.intent,
            target=command.target,
            params=command.params,
            matched=command.matched,
            description=str(exc),
        )
    return project, command
