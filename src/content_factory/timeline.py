"""The video editing engine: normalize, validate, edit, and compile.

Everything a non-linear editor does to a timeline lives here as pure,
synchronous functions, so the API, the worker, the renderer, an external AI
agent, and the browser all mutate a project through exactly one code path.

Four responsibilities:

* :func:`normalize` — repair a document: unique ids, sorted keyframes, clamped
  numbers, no transitions on the opening scene, sane marker times. Every save
  goes through it, so a malformed document can never be persisted.
* :func:`report` — measure the cut and validate it against professional rules
  (reading speed, text fit, transition length, contrast, pacing).
* Structural edits — :func:`split_scene`, :func:`merge_scene`, :func:`duplicate_scene`,
  :func:`delete_scene`, :func:`move_scene`, :func:`bulk_update`, and markers.
* :func:`compile_render_plan` — resolve the timeline into absolute slots,
  caption cues, and audio layers for a renderer to execute.

Motion is a real keyframe track: :func:`evaluate_motion` interpolates a scene's
motion track at any point in its runtime, falling back to the single-segment
:class:`~content_factory.models.SceneMotion` when no track exists.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterable

from .models import (
    AudioTrackPlan,
    ColorGrade,
    IssueSeverity,
    Keyframe,
    RenderPlan,
    RenderStep,
    SceneEffect,
    SceneMotion,
    SubtitleCue,
    TimelineIssue,
    TimelineMarker,
    TimelineReport,
    TimelineStats,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
    utcnow,
)

#: Output size per aspect-ratio preset.
ASPECT_PRESETS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "3:4": (1080, 1440),
}
DEFAULT_ASPECT = "9:16"

#: How long each transition type blends, in seconds (0 for a hard cut).
TRANSITION_SECONDS: dict[VideoTransition, float] = {
    VideoTransition.CUT: 0.0,
    VideoTransition.FADE: 0.5,
    VideoTransition.SLIDE: 0.4,
    VideoTransition.ZOOM: 0.5,
    VideoTransition.WIPE: 0.4,
    VideoTransition.CIRCLE: 0.5,
    VideoTransition.DISSOLVE: 0.6,
}

#: A transition may never eat more than this share of either neighbour.
MAX_TRANSITION_SHARE = 0.4

#: Natural narration rate used when estimating speech from a word count.
NARRATION_WORDS_PER_SECOND = 2.6

#: Reading-speed limits used by the validator (characters per second).
MAX_CAPTION_CHARS_PER_SECOND = 20.0
#: Comfortable caption length before a cue is split.
MAX_CUE_CHARS = 42
MAX_CUE_WORDS = 9
#: Minimum scene length before a cut feels like a flash frame.
MIN_SCENE_SECONDS = 0.8
#: Faster than this and the cut feels frantic for a talking-head script.
MAX_CUTS_PER_MINUTE = 42.0
#: WCAG AA contrast ratio for text on its background.
MIN_TEXT_CONTRAST = 4.5

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_WORD_RE = re.compile(r"\S+")


# --- Normalization -----------------------------------------------------------


def _coerce_hex(value: str | None, fallback: str) -> str:
    """Return a valid ``#rgb``/``#rrggbb`` colour, or ``fallback``."""
    if isinstance(value, str) and _HEX_RE.match(value.strip()):
        return value.strip()
    return fallback


def _unique_id(existing: set[str], preferred: str | None = None) -> str:
    candidate = (preferred or "").strip()
    if not candidate or candidate in existing:
        candidate = uuid.uuid4().hex[:8]
        while candidate in existing:
            candidate = uuid.uuid4().hex[:8]
    existing.add(candidate)
    return candidate


def normalize(project: VideoProject) -> VideoProject:
    """Repair a video project in place and return it.

    Idempotent: running it twice changes nothing. Every persisted edit passes
    through here, which is what makes the rest of the engine safe to write.
    """
    if project.aspect_ratio not in ASPECT_PRESETS:
        project.aspect_ratio = DEFAULT_ASPECT
    if not project.scenes:
        project.scenes = [_placeholder_scene()]
    project.markers = sorted(project.markers, key=lambda marker: marker.time_seconds)

    seen: set[str] = set()
    for index, scene in enumerate(project.scenes):
        scene.id = _unique_id(seen, scene.id)
        scene.duration_seconds = round(min(60.0, max(0.5, scene.duration_seconds)), 2)
        scene.speed = round(min(2.0, max(0.5, scene.speed)), 2)
        scene.volume = round(min(2.0, max(0.0, scene.volume)), 2)
        scene.pitch = round(min(2.0, max(0.5, scene.pitch)), 2)
        scene.font_size = int(min(140, max(16, scene.font_size)))
        scene.overlay_size = int(min(140, max(16, scene.overlay_size)))
        scene.background = _coerce_hex(scene.background, "#1a1d27")
        scene.text_color = _coerce_hex(scene.text_color, "#ffffff")
        scene.trim_start = round(max(0.0, min(600.0, scene.trim_start)), 2)
        scene.trim_end = round(max(0.0, min(600.0, scene.trim_end)), 2)
        scene.label = (scene.label or f"Scene {index + 1}").strip()[:120]
        if scene.motion is not None:
            scene.motion.easing = scene.motion.easing or "ease-in-out"
        scene.keyframes = _normalize_keyframes(scene.keyframes)
        # A transition into the opening scene has nothing to blend from.
        if index == 0 and scene.transition != VideoTransition.CUT:
            scene.transition = VideoTransition.CUT

    project.voiceover_volume = round(min(2.0, max(0.0, project.voiceover_volume)), 2)
    project.music_volume = round(min(1.0, max(0.0, project.music_volume)), 2)
    project.bpm = int(min(180, max(60, project.bpm)))
    project.fps = int(min(60, max(24, project.fps)))
    return project


def _normalize_keyframes(keyframes: Iterable[Keyframe]) -> list[Keyframe]:
    """Sort, de-duplicate by position, and clamp a keyframe track."""
    cleaned: list[Keyframe] = []
    for frame in sorted(keyframes, key=lambda item: item.at):
        frame.at = round(min(1.0, max(0.0, frame.at)), 4)
        frame.opacity = round(min(1.0, max(0.0, frame.opacity)), 3)
        frame.scale = round(min(2.0, max(0.5, frame.scale)), 3)
        frame.pos_x = round(min(100.0, max(-100.0, frame.pos_x)), 2)
        frame.pos_y = round(min(100.0, max(-100.0, frame.pos_y)), 2)
        frame.rotation = round(min(180.0, max(-180.0, frame.rotation)), 2)
        frame.easing = frame.easing or "linear"
        if cleaned and abs(cleaned[-1].at - frame.at) < 1e-6:
            cleaned[-1] = frame  # last one wins on a tie
        else:
            cleaned.append(frame)
    return cleaned


def _placeholder_scene() -> VideoScene:
    return VideoScene(
        id=uuid.uuid4().hex[:8],
        label="Scene 1",
        text="Scene 1",
        narration="",
        duration_seconds=3.0,
    )


# --- Measurement -------------------------------------------------------------


def scene_seconds(scene: VideoScene) -> float:
    """Effective contribution of a scene to the timeline, honouring speed."""
    return round(max(0.5, scene.duration_seconds / max(0.5, scene.speed)), 2)


def transition_seconds(scene: VideoScene, previous: VideoScene | None) -> float:
    """Length of the blend at the head of ``scene``, bounded by both neighbours."""
    if previous is None or scene.transition == VideoTransition.CUT:
        return 0.0
    budget = min(scene_seconds(scene), scene_seconds(previous))
    return round(min(TRANSITION_SECONDS.get(scene.transition, 0.5), budget), 3)


def total_seconds(project: VideoProject) -> float:
    """Total timeline duration. Transitions blend *inside* a scene's slot."""
    return round(sum(scene_seconds(scene) for scene in project.scenes), 2)


def scene_characters(scene: VideoScene) -> int:
    """Characters of on-screen text plus narration for this scene."""
    on_screen = scene.text or ""
    spoken = scene.narration or scene.text or ""
    return len(on_screen) + len(spoken)


def measure(project: VideoProject) -> TimelineStats:
    """Compute the measurable properties of a timeline."""
    scenes = project.scenes
    durations = [scene_seconds(scene) for scene in scenes]
    total = round(sum(durations), 2)
    narration = 0.0
    transitions = 0.0
    words = 0
    for scene in scenes:
        source = scene.narration or scene.text or ""
        words += len(_WORD_RE.findall(source))
        narration += _narration_seconds(scene)
    for index, scene in enumerate(scenes):
        previous = scenes[index - 1] if index else None
        transitions += transition_seconds(scene, previous)
    minutes = total / 60 if total else 0.0
    return TimelineStats(
        scene_count=len(scenes),
        total_seconds=total,
        narration_seconds=round(narration, 2),
        transition_seconds=round(transitions, 2),
        marker_count=len(project.markers),
        shortest_scene_seconds=round(min(durations), 2) if durations else 0.0,
        longest_scene_seconds=round(max(durations), 2) if durations else 0.0,
        average_scene_seconds=round(total / len(durations), 2) if durations else 0.0,
        words=words,
        words_per_minute=round(words / minutes, 1) if minutes else 0.0,
        cuts_per_minute=round(len(scenes) / minutes, 1) if minutes else 0.0,
    )


def _narration_seconds(scene: VideoScene) -> float:
    """Narration length at a natural speaking rate."""
    source = scene.narration or scene.text or ""
    return len(_WORD_RE.findall(source)) / NARRATION_WORDS_PER_SECOND


# --- Validation --------------------------------------------------------------


def _relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a ``#rgb``/``#rrggbb`` colour."""
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    try:
        channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    except (ValueError, IndexError):
        return 0.0

    def linear(channel: float) -> float:
        return (
            channel / 12.92
            if channel <= 0.03928
            else ((channel + 0.055) / 1.055) ** 2.4
        )

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two colours (1.0 = invisible, 21.0 = max)."""
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def validate(project: VideoProject) -> list[TimelineIssue]:
    """Return every problem a professional editor would flag."""
    issues: list[TimelineIssue] = []
    scenes = project.scenes
    if not scenes:
        return [
            TimelineIssue(
                code="empty_timeline",
                severity=IssueSeverity.ERROR,
                message="The timeline has no scenes.",
                hint="Rebuild it from the script, or add a scene.",
            )
        ]

    stats = measure(project)
    if stats.shortest_scene_seconds < MIN_SCENE_SECONDS:
        short = min(scenes, key=scene_seconds)
        issues.append(
            TimelineIssue(
                code="scene_too_short",
                severity=IssueSeverity.WARNING,
                message=(
                    f"'{short.label}' lasts {scene_seconds(short)}s — shorter than "
                    f"the {MIN_SCENE_SECONDS}s floor."
                ),
                hint="Lengthen it or merge it with a neighbour.",
                scene_id=short.id,
            )
        )
    if stats.cuts_per_minute > MAX_CUTS_PER_MINUTE:
        issues.append(
            TimelineIssue(
                code="frantic_pacing",
                severity=IssueSeverity.WARNING,
                message=(
                    f"{stats.cuts_per_minute} cuts/minute vs a {MAX_CUTS_PER_MINUTE} "
                    "comfort ceiling."
                ),
                hint="Merge short scenes so the viewer can breathe.",
            )
        )

    for index, scene in enumerate(scenes):
        previous = scenes[index - 1] if index else None
        label = f"'{scene.label}'"
        if index == 0 and scene.transition != VideoTransition.CUT:
            issues.append(
                TimelineIssue(
                    code="opening_transition",
                    severity=IssueSeverity.INFO,
                    message=(
                        f"{label} opens the timeline but has a "
                        f"{scene.transition.value} transition."
                    ),
                    hint="A hard cut is standard for the first frame.",
                    scene_id=scene.id,
                )
            )
        if scene.speed != 1.0 and scene_seconds(scene) < MIN_SCENE_SECONDS:
            issues.append(
                TimelineIssue(
                    code="speed_extreme",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"{label} plays at {scene.speed}x, leaving only "
                        f"{scene_seconds(scene)}s on screen."
                    ),
                    hint="Keep speed between 0.75x and 1.5x for legible text.",
                    scene_id=scene.id,
                )
            )
        transition = transition_seconds(scene, previous)
        if previous is not None and transition >= MAX_TRANSITION_SHARE * min(
            scene_seconds(scene), scene_seconds(previous)
        ):
            issues.append(
                TimelineIssue(
                    code="transition_too_long",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"The blend into {label} eats {transition}s of a "
                        f"{scene_seconds(scene)}s scene."
                    ),
                    hint="Shorten the transition or lengthen the scene.",
                    scene_id=scene.id,
                )
            )
        text = (scene.text or "").strip()
        narration = (scene.narration or scene.text or "").strip()
        if not text and not narration:
            issues.append(
                TimelineIssue(
                    code="empty_scene",
                    severity=IssueSeverity.WARNING,
                    message=f"{label} has no text and no narration.",
                    hint="Give it a line or delete it.",
                    scene_id=scene.id,
                )
            )
            continue
        budget = scene_seconds(scene)
        reading = len(text) / budget if budget else 0.0
        if project.captions and reading > MAX_CAPTION_CHARS_PER_SECOND * 1.5:
            issues.append(
                TimelineIssue(
                    code="text_overflows_scene",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"{label} must be read in {budget}s but holds "
                        f"{len(text)} characters."
                    ),
                    hint="Shorten the on-screen text or extend the scene.",
                    scene_id=scene.id,
                )
            )
        narration_seconds = _narration_seconds(scene)
        if narration and narration_seconds > budget * 1.25:
            issues.append(
                TimelineIssue(
                    code="narration_overflows_scene",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"{label}'s narration needs about "
                        f"{round(narration_seconds, 1)}s but the scene lasts "
                        f"{budget}s."
                    ),
                    hint="Re-sync the voiceover or lengthen the scene.",
                    scene_id=scene.id,
                )
            )
        contrast = contrast_ratio(scene.text_color, scene.background)
        if contrast < MIN_TEXT_CONTRAST:
            issues.append(
                TimelineIssue(
                    code="low_text_contrast",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"{label} has {contrast}:1 contrast between text "
                        f"({scene.text_color}) and background ({scene.background})."
                    ),
                    hint=(
                        f"Aim for at least {MIN_TEXT_CONTRAST}:1, or add a text shadow."
                    ),
                    scene_id=scene.id,
                )
            )
    flat = [
        scene
        for scene in scenes
        if scene.image_url is None
        and scene.effect == SceneEffect.NONE
        and scene.grade == ColorGrade.NONE
        and scene.filter == VideoFilter.NONE
    ]
    if flat and len(flat) == len(scenes):
        issues.append(
            TimelineIssue(
                code="flat_look",
                severity=IssueSeverity.INFO,
                message=(
                    "Every scene is a plain colour card: no image, filter, or grade."
                ),
                hint="Assign images, or run the AI assist to pick a look per scene.",
            )
        )
    elif flat:
        issues.append(
            TimelineIssue(
                code="flat_look_partial",
                severity=IssueSeverity.INFO,
                message=(
                    f"{len(flat)} of {len(scenes)} scenes have no image, "
                    "filter, or grade."
                ),
                hint="Give them a look so the cut stays visually consistent.",
            )
        )

    if stats.narration_seconds and stats.total_seconds:
        fill = stats.narration_seconds / stats.total_seconds
        if fill < 0.5:
            issues.append(
                TimelineIssue(
                    code="narration_underfills",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"Narration covers only {round(fill * 100)}% of the "
                        f"{stats.total_seconds}s cut, leaving dead air."
                    ),
                    hint="Shorten scenes or expand the script to fill the runtime.",
                )
            )

    for marker in project.markers:
        if marker.time_seconds > stats.total_seconds:
            issues.append(
                TimelineIssue(
                    code="marker_out_of_range",
                    severity=IssueSeverity.INFO,
                    message=(
                        f"Marker '{marker.label or marker.id}' sits at "
                        f"{marker.time_seconds}s, past the {stats.total_seconds}s end."
                    ),
                    hint="Move or remove the marker.",
                )
            )
    if not project.markers:
        issues.append(
            TimelineIssue(
                code="no_markers",
                severity=IssueSeverity.INFO,
                message="The timeline has no markers.",
                hint="Mark beats or chapter points so long cuts stay navigable.",
            )
        )
    return issues


_SEVERITY_WEIGHTS = {
    IssueSeverity.ERROR: 25,
    IssueSeverity.WARNING: 8,
    IssueSeverity.INFO: 2,
}


def score(issues: Iterable[TimelineIssue]) -> int:
    """Turn findings into a 0–100 editing readiness score."""
    penalty = sum(_SEVERITY_WEIGHTS.get(issue.severity, 5) for issue in issues)
    return max(0, 100 - penalty)


def report(project: VideoProject, target_seconds: int | None = None) -> TimelineReport:
    """Measure and validate a timeline in one call."""
    issues = validate(project)
    stats = measure(project)
    if target_seconds:
        drift = abs(stats.total_seconds - target_seconds)
        if drift > max(2.0, target_seconds * 0.15):
            issues.append(
                TimelineIssue(
                    code="duration_drift",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"The cut runs {stats.total_seconds}s against a "
                        f"{target_seconds}s target."
                    ),
                    hint="Trim or extend scenes before approving the video.",
                )
            )
    return TimelineReport(
        stats=stats,
        issues=issues,
        score=score(issues),
        target_seconds=target_seconds,
        generated_at=utcnow(),
    )


# --- Structural edits --------------------------------------------------------


def find_scene(project: VideoProject, scene_id: str) -> VideoScene:
    """Return a scene by id, raising ``KeyError`` when it is absent."""
    for scene in project.scenes:
        if scene.id == scene_id:
            return scene
    raise KeyError(f"No scene '{scene_id}' in the video project.")


def index_of(project: VideoProject, scene_id: str) -> int:
    for index, scene in enumerate(project.scenes):
        if scene.id == scene_id:
            return index
    raise KeyError(f"No scene '{scene_id}' in the video project.")


def _split_text(text: str, at: float) -> tuple[str, str]:
    """Split text into two halves near ``at`` without breaking a word."""
    words = (text or "").split()
    if len(words) < 2:
        return text or "", ""
    cut = min(len(words) - 1, max(1, round(len(words) * min(1.0, max(0.0, at)))))
    return " ".join(words[:cut]), " ".join(words[cut:])


def split_scene(project: VideoProject, scene_id: str, at: float = 0.5) -> VideoProject:
    """Split a scene into two at a fraction of its runtime."""
    normalize(project)
    index = index_of(project, scene_id)
    scene = project.scenes[index]
    at = min(0.95, max(0.05, float(at)))
    head_text, tail_text = _split_text(scene.text, at)
    head_narration, tail_narration = _split_text(scene.narration or "", at)

    # Split the timeline slot (not the effective duration) so both halves keep
    # the original speed and the total running time is unchanged.
    head_slot = round(scene.duration_seconds * at, 2)
    tail_slot = round(scene.duration_seconds - head_slot, 2)
    head_seconds, tail_seconds = head_slot, tail_slot
    scene.duration_seconds = head_seconds
    tail = scene.model_copy(deep=True)
    tail.id = uuid.uuid4().hex[:8]
    tail.label = f"{scene.label} (b)"
    tail.text = tail_text or scene.text
    tail.narration = tail_narration or None
    tail.duration_seconds = tail_seconds
    tail.transition = VideoTransition.CUT
    scene.text = head_text or scene.text
    scene.narration = head_narration or scene.narration
    project.scenes.insert(index + 1, tail)
    return normalize(project)


def merge_scene(project: VideoProject, scene_id: str) -> VideoProject:
    """Merge a scene into the following one (the reverse of a split)."""
    normalize(project)
    index = index_of(project, scene_id)
    if index >= len(project.scenes) - 1:
        raise ValueError("The last scene has nothing to merge into.")
    current = project.scenes[index]
    following = project.scenes[index + 1]
    current.text = " ".join(
        part for part in (current.text, following.text) if part
    ).strip()
    merged_narration = " ".join(
        part for part in (current.narration or "", following.narration or "") if part
    ).strip()
    current.narration = merged_narration or None
    current.duration_seconds = round(
        current.duration_seconds + following.duration_seconds, 2
    )
    if current.transition == VideoTransition.CUT:
        current.transition = following.transition
    project.scenes.pop(index + 1)
    return normalize(project)


def duplicate_scene(project: VideoProject, scene_id: str) -> VideoProject:
    """Insert a copy of a scene directly after it."""
    normalize(project)
    index = index_of(project, scene_id)
    clone = project.scenes[index].model_copy(deep=True)
    clone.id = uuid.uuid4().hex[:8]
    clone.label = f"{clone.label} copy"
    project.scenes.insert(index + 1, clone)
    return normalize(project)


def delete_scene(project: VideoProject, scene_id: str) -> VideoProject:
    """Remove a scene. The last remaining scene is never deleted."""
    normalize(project)
    if len(project.scenes) <= 1:
        raise ValueError("A timeline must keep at least one scene.")
    project.scenes.pop(index_of(project, scene_id))
    return normalize(project)


def move_scene(project: VideoProject, scene_id: str, to_index: int) -> VideoProject:
    """Move a scene to a new index, sliding the others."""
    normalize(project)
    origin = index_of(project, scene_id)
    destination = max(0, min(len(project.scenes) - 1, int(to_index)))
    scene = project.scenes.pop(origin)
    project.scenes.insert(destination, scene)
    return normalize(project)


# --- NLE-grade retiming, trimming and audio -----------------------------------


def set_speed(project: VideoProject, scene_id: str, speed: float) -> VideoProject:
    """Retime a scene (0.5x slow-mo .. 2x fast-forward), keeping its slot.

    Like an NLE's "change clip speed": the timeline slot shrinks/grows by
    ``1/speed`` so the story gets faster without re-trimming every cut.
    """
    normalize(project)
    scene = find_scene(project, scene_id)
    speed = min(2.0, max(0.5, float(speed)))
    if abs(speed - scene.speed) < 1e-6:
        return normalize(project)
    base = scene.duration_seconds * (scene.speed / speed)
    scene.duration_seconds = round(min(60.0, max(0.5, base)), 2)
    scene.speed = speed
    return normalize(project)


def reverse_scene(
    project: VideoProject, scene_id: str, reverse: bool = True
) -> VideoProject:
    """Play the scene's source media backwards (boomerang effect)."""
    normalize(project)
    scene = find_scene(project, scene_id)
    scene.reverse = bool(reverse)
    return normalize(project)


def trim_scene(
    project: VideoProject,
    scene_id: str,
    trim_start: float | None = None,
    trim_end: float | None = None,
) -> VideoProject:
    """Set a scene's source in/out handles without touching the timeline slot."""
    normalize(project)
    scene = find_scene(project, scene_id)
    if trim_start is not None:
        scene.trim_start = round(min(600.0, max(0.0, float(trim_start))), 3)
    if trim_end is not None:
        scene.trim_end = round(min(600.0, max(0.0, float(trim_end))), 3)
    if scene.trim_start + scene.trim_end > 0 and scene.trim_start >= scene.trim_end:
        raise ValueError("trim_start must stay below trim_end.")
    return normalize(project)


def set_audio(
    project: VideoProject,
    scene_id: str,
    volume: float | None = None,
    fade_in: float | None = None,
    fade_out: float | None = None,
) -> VideoProject:
    """Adjust one scene's gain and audio ramps (the NLE audio panel)."""
    normalize(project)
    scene = find_scene(project, scene_id)
    if volume is not None:
        scene.volume = round(min(2.0, max(0.0, float(volume))), 3)
    if fade_in is not None:
        scene.audio_fade_in = round(min(10.0, max(0.0, float(fade_in))), 3)
    if fade_out is not None:
        scene.audio_fade_out = round(min(10.0, max(0.0, float(fade_out))), 3)
    if scene.audio_fade_in + scene.audio_fade_out > scene.duration_seconds:
        raise ValueError("Fades cannot exceed the scene's duration.")
    return normalize(project)


def copy_scene(project: VideoProject, scene_id: str) -> VideoScene:
    """Copy a scene onto an internal clipboard (not yet inserted)."""
    normalize(project)
    return project.scenes[index_of(project, scene_id)].model_copy(deep=True)


def paste_scene(
    project: VideoProject, clip: VideoScene, after_scene_id: str | None = None
) -> VideoProject:
    """Paste a previously copied scene after the given scene (or at the end)."""
    normalize(project)
    clone = clip.model_copy(deep=True)
    clone.id = uuid.uuid4().hex[:8]
    clone.label = f"{clone.label} copy"
    if after_scene_id is None:
        project.scenes.append(clone)
    else:
        project.scenes.insert(index_of(project, after_scene_id) + 1, clone)
    return normalize(project)


def bulk_update(
    project: VideoProject, scene_ids: Iterable[str], patch: dict
) -> VideoProject:
    """Apply the same look to many scenes at once.

    Only fields that exist on :class:`VideoScene` are applied; unknown keys are
    ignored rather than raising, so a rough client cannot corrupt a project.
    ``id``, ``text`` and ``narration`` are never bulk-assigned (that would
    destroy content) unless the caller passes them explicitly per scene.
    """
    allowed = {
        key
        for key in VideoScene.model_fields
        if key not in {"id", "text", "narration", "keyframes"}
    }
    clean = {key: value for key, value in (patch or {}).items() if key in allowed}
    if not clean:
        raise ValueError("The patch contained no assignable scene fields.")
    wanted = set(scene_ids)
    if not any(scene.id in wanted for scene in project.scenes):
        raise KeyError("No matching scene ids.")
    # Validate through pydantic rather than setattr: a raw "noir" becomes
    # ColorGrade.NOIR, and a typo raises instead of poisoning the document.
    for index, scene in enumerate(project.scenes):
        if scene.id not in wanted:
            continue
        project.scenes[index] = VideoScene.model_validate(
            {**scene.model_dump(), **clean}
        )
    return normalize(project)


def set_keyframes(
    project: VideoProject, scene_id: str, keyframes: Iterable[Keyframe]
) -> VideoProject:
    """Replace a scene's motion track."""
    scene = find_scene(project, scene_id)
    scene.keyframes = list(keyframes)
    return normalize(project)


def add_marker(
    project: VideoProject, time_seconds: float, label: str = "", color: str = "#f59e0b"
) -> VideoProject:
    """Add a labelled marker to the timeline."""
    normalize(project)
    total = total_seconds(project)
    project.markers.append(
        TimelineMarker(
            id=uuid.uuid4().hex[:8],
            time_seconds=round(min(max(0.0, float(time_seconds)), total), 3),
            label=(label or "")[:80],
            color=_coerce_hex(color, "#f59e0b"),
        )
    )
    return normalize(project)


def remove_marker(project: VideoProject, marker_id: str) -> VideoProject:
    """Remove a marker by id."""
    remaining = [marker for marker in project.markers if marker.id != marker_id]
    if len(remaining) == len(project.markers):
        raise KeyError(f"No marker '{marker_id}' on the timeline.")
    project.markers = remaining
    return normalize(project)


# --- Motion ------------------------------------------------------------------


_EASINGS: dict[str, Callable[[float], float]] = {
    "linear": lambda t: t,
    "ease-in": lambda t: t * t,
    "ease-out": lambda t: 1 - (1 - t) * (1 - t),
    "ease-in-out": lambda t: 3 * t * t - 2 * t * t * t,
}


def _ease(name: str, t: float) -> float:
    easing = _EASINGS.get(name or "ease-in-out") or _EASINGS["ease-in-out"]
    return easing(max(0.0, min(1.0, t)))


def evaluate_motion(scene: VideoScene, progress: float) -> dict[str, float]:
    """Motion values for a scene at ``progress`` (0.0 → 1.0 of its runtime).

    Interpolates the keyframe track when one exists, otherwise animates the
    single-segment :class:`SceneMotion` from neutral, otherwise returns the
    static resting pose.
    """
    progress = max(0.0, min(1.0, float(progress)))
    track = scene.keyframes
    if track:
        if progress <= track[0].at:
            return _frame_values(track[0])
        if progress >= track[-1].at:
            return _frame_values(track[-1])
        for start, end in zip(track, track[1:], strict=False):
            if start.at <= progress <= end.at:
                span = max(1e-6, end.at - start.at)
                local = _ease(end.easing, (progress - start.at) / span)
                return {
                    field: round(
                        _lerp(
                            _frame_values(start)[field],
                            _frame_values(end)[field],
                            local,
                        ),
                        4,
                    )
                    for field in ("scale", "rotation", "opacity", "pos_x", "pos_y")
                }
    motion: SceneMotion | None = scene.motion
    if motion is None:
        return {
            "scale": 1.0,
            "rotation": 0.0,
            "opacity": 1.0,
            "pos_x": 0.0,
            "pos_y": 0.0,
        }
    eased = _ease(motion.easing, progress)
    return {
        "scale": round(_lerp(1.0, motion.scale, eased), 4),
        "rotation": round(_lerp(0.0, motion.rotation, eased), 4),
        "opacity": round(_lerp(1.0, motion.opacity, eased), 4),
        "pos_x": round(_lerp(0.0, motion.pos_x, eased), 4),
        "pos_y": round(_lerp(0.0, motion.pos_y, eased), 4),
    }


def _frame_values(frame: Keyframe) -> dict[str, float]:
    return {
        "scale": frame.scale,
        "rotation": frame.rotation,
        "opacity": frame.opacity,
        "pos_x": frame.pos_x,
        "pos_y": frame.pos_y,
    }


def _lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


# --- Render plan -------------------------------------------------------------


def resolution(project: VideoProject) -> tuple[int, int]:
    """Output width/height for the project's aspect ratio."""
    return ASPECT_PRESETS.get(project.aspect_ratio, ASPECT_PRESETS[DEFAULT_ASPECT])


def caption_cues(project: VideoProject, steps: list[RenderStep]) -> list[SubtitleCue]:
    """Break narration into readable cues with resolved start/end times."""
    cues: list[SubtitleCue] = []
    for step in steps:
        source = (project_scene_text(project, step.scene_id) or "").strip()
        if not source:
            continue
        chunks = _chunk_caption(source, project.captions)
        if not chunks:
            continue
        weights = [max(1, len(chunk)) for chunk in chunks]
        total_weight = sum(weights)
        cursor = step.start_seconds
        for chunk, weight in zip(chunks, weights, strict=True):
            share = step.duration_seconds * weight / total_weight
            cues.append(
                SubtitleCue(
                    index=len(cues),
                    scene_id=step.scene_id,
                    start_seconds=round(cursor, 2),
                    end_seconds=round(min(step.end_seconds, cursor + share), 2),
                    text=chunk,
                )
            )
            cursor += share
    return cues


def project_scene_text(project: VideoProject, scene_id: str) -> str:
    """Narration for a scene, falling back to its on-screen text."""
    for scene in project.scenes:
        if scene.id == scene_id:
            return scene.narration or scene.text or ""
    return ""


def _chunk_caption(text: str, enabled: bool) -> list[str]:
    """Split narration into caption-sized pieces at sentence/word boundaries."""
    if not enabled:
        return [text]
    pieces: list[str] = []
    buffer = ""
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        words = _WORD_RE.findall(sentence)
        for start in range(0, len(words), MAX_CUE_WORDS):
            chunk = " ".join(words[start : start + MAX_CUE_WORDS])
            if len(chunk) > MAX_CUE_CHARS and buffer:
                pieces.append(buffer)
                buffer = chunk
            elif buffer and len(buffer) + len(chunk) + 1 > MAX_CUE_CHARS:
                pieces.append(buffer)
                buffer = chunk
            else:
                buffer = f"{buffer} {chunk}".strip()
    if buffer:
        pieces.append(buffer)
    return pieces


def compile_render_plan(
    project: VideoProject,
    project_id: str = "",
    narration_urls: dict[str, str] | None = None,
) -> RenderPlan:
    """Resolve a timeline into absolute slots, captions, and audio layers.

    ``narration_urls`` maps a scene id to its synthesized audio, so a renderer
    knows which clip belongs in which slot.
    """
    project = project.model_copy(deep=True)
    narration_urls = narration_urls or {}
    requested_aspect = project.aspect_ratio
    normalize(project)
    width, height = resolution(project)
    warnings: list[str] = []

    steps: list[RenderStep] = []
    cursor = 0.0
    for index, scene in enumerate(project.scenes):
        previous = project.scenes[index - 1] if index else None
        duration = scene_seconds(scene)
        blend = transition_seconds(scene, previous)
        steps.append(
            RenderStep(
                index=index,
                scene_id=scene.id,
                label=scene.label,
                start_seconds=round(cursor, 2),
                end_seconds=round(cursor + duration, 2),
                duration_seconds=duration,
                transition_in=scene.transition if index else VideoTransition.CUT,
                transition_seconds=blend,
                filter=scene.filter,
                effect=scene.effect,
                grade=scene.grade,
                ken_burns=scene.ken_burns,
                background=scene.background,
                image_url=scene.video_url or scene.image_url,
                text=scene.text,
                text_position=scene.text_position,
                text_style=scene.text_style,
                text_color=scene.text_color,
                font_size=scene.font_size,
                entrance=scene.entrance,
                exit=scene.exit,
                keyframes=list(scene.keyframes),
                source_in_seconds=round(scene.trim_start, 2),
                speed=scene.speed,
                narration_url=narration_urls.get(scene.id),
                volume=scene.volume,
            )
        )
        cursor += duration
        if scene.trim_end or scene.reverse:
            warnings.append(
                f"{scene.label}: local export does not support trim_end or reverse."
            )

    audio = [
        AudioTrackPlan(
            kind="voiceover",
            enabled=bool(narration_urls),
            volume=project.voiceover_volume,
        ),
        AudioTrackPlan(
            kind="music",
            enabled=project.background_music,
            volume=project.music_volume,
            url=project.background_music_url,
            bpm=project.bpm if project.background_music else None,
        ),
    ]

    if requested_aspect not in ASPECT_PRESETS:
        warnings.append(
            f"Unknown aspect ratio '{requested_aspect}'; using {DEFAULT_ASPECT}."
        )
    plain = [step.label for step in steps if step.image_url is None]
    if plain and len(plain) == len(steps):
        warnings.append(
            "No scene has a source image; the render will be colour cards only."
        )
    return RenderPlan(
        project_id=project_id,
        aspect_ratio=project.aspect_ratio,
        width=width,
        height=height,
        fps=project.fps,
        total_seconds=round(cursor, 2),
        steps=steps,
        subtitles=caption_cues(project, steps),
        audio=audio,
        warnings=warnings,
        generated_at=utcnow(),
    )
