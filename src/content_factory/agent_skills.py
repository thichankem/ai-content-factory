"""Skills: the multi-step recipes an agent follows, checked against the registry.

A tool answers *"what can I do?"*.  A skill answers *"how is this job actually
done?"* — the order, the arguments that come from earlier results, what to read
back, and which steps only a human may sign off.  110 tools without recipes is a
parts bin; an agent that has to rediscover the pipeline on every turn spends its
context guessing instead of working.

Two design rules keep this honest:

* **Progressive disclosure.**  ``GET /skills`` returns one line per skill (name,
  description, tools, step count).  ``GET /skills/{name}`` returns the full
  recipe.  An agent loads the body only for the job in front of it.
* **The recipes are executable claims.**  Every step names a real tool and fills
  that tool's required arguments, and ``tests/test_agent_skills.py`` verifies it
  against ``TOOL_REGISTRY``: rename a tool or change its schema and the suite
  fails here instead of failing in an agent's transcript at 2am.

The same catalog backs the ``list_skills`` / ``read_skill`` tools and the
``/skills`` endpoints, so an HTTP agent, an MCP agent and a Claude Code agent all
read one source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "SKILLS",
    "Skill",
    "SkillStep",
    "read_skill",
    "skill_index",
    "skill_names",
]


@dataclass(frozen=True)
class SkillStep:
    """One call in a recipe: which tool, which arguments, what to read back."""

    tool: str
    #: Argument name -> where its value comes from.  Values are instructions for
    #: the agent ("from create_project.id"), because a skill describes a job, it
    #: does not carry a fixture.
    args: dict[str, str] = field(default_factory=dict)
    #: Fields the agent should actually look at in the result before moving on.
    read: str = ""
    note: str = ""


@dataclass(frozen=True)
class Skill:
    """A named recipe: when to use it, the ordered steps, and the hard rules."""

    name: str
    description: str
    when_to_use: str
    steps: tuple[SkillStep, ...]
    guardrails: tuple[str, ...] = ()
    human_gates: tuple[str, ...] = ()

    def tools(self) -> list[str]:
        """Every tool the recipe calls, in order (repeats included)."""
        return [step.tool for step in self.steps]

    def index_entry(self) -> dict[str, Any]:
        """Level 1: what an agent needs to decide whether to read the body."""
        return {
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "steps": len(self.steps),
            "tools": self.tools(),
            "requires_human": bool(self.human_gates),
        }

    def manifest_entry(self) -> dict[str, Any]:
        """Level 2: the full recipe."""
        return {
            **self.index_entry(),
            "human_gates": list(self.human_gates),
            "guardrails": list(self.guardrails),
            "recipe": [
                {
                    "tool": step.tool,
                    "args": dict(step.args),
                    "read": step.read,
                    "note": step.note,
                }
                for step in self.steps
            ],
        }


_PIPELINE = Skill(
    name="topic-to-published-video",
    description=(
        "Run a topic end to end: research, script, timeline, voiceover, render, "
        "publish — stopping at both human approval gates."
    ),
    when_to_use=(
        "The user asks for a finished video from an idea or a topic, or asks to "
        "continue a project that is still in draft/review."
    ),
    steps=(
        SkillStep(
            "create_project",
            {
                "name": "short project name",
                "topic": "the story angle to explore",
                "target_language": "language code, defaults to 'vi'",
                "duration_target_seconds": "target length, defaults to 45",
            },
            read="id — every later step needs it",
        ),
        SkillStep(
            "research_project",
            {"project_id": "from create_project.id"},
            read="sources and key facts; the script must not invent facts",
        ),
        SkillStep(
            "attach_kb",
            {"project_id": "from create_project.id", "kb_id": "from list_kbs"},
            read="whether the knowledge base is attached",
            note="Optional. Use when the user has sources that must be honoured.",
        ),
        SkillStep(
            "ground_project",
            {"project_id": "from create_project.id", "query": "what to ground"},
            read="which claims are backed and which are disputed",
        ),
        SkillStep(
            "update_script",
            {"project_id": "from create_project.id", "script": "the narration"},
            read="status; the script is stored, not accepted yet",
        ),
        SkillStep(
            "analyze_script",
            {"project_id": "from create_project.id"},
            read="score and issues — fix them before asking for approval",
        ),
        SkillStep(
            "approve_stage",
            {"project_id": "from create_project.id", "stage": "'script'"},
            read="status going to script_approved",
            note="HUMAN GATE: only after a person actually read the script.",
        ),
        SkillStep(
            "build_video_project",
            {"project_id": "from create_project.id"},
            read="video_project.scenes[].id — scene ids come from here",
        ),
        SkillStep(
            "bulk_update_scenes",
            {
                "project_id": "from create_project.id",
                "scene_ids": "from video_project.scenes[].id",
                "patch": "look to apply, e.g. {grade, filter, transition}",
            },
            read="the updated timeline",
            note="One call for a consistent look instead of N per-scene calls.",
        ),
        SkillStep(
            "generate_voiceover",
            {"project_id": "from create_project.id"},
            read="the per-scene voice files; needs network (Edge-TTS/gTTS)",
        ),
        SkillStep(
            "start_generation",
            {"project_id": "from create_project.id"},
            read="status=generating — this is what render_video accepts",
        ),
        SkillStep(
            "render_video",
            {"project_id": "from create_project.id", "export_format": "'mp4'"},
            read="the rendered file; mp4 is H.264/AAC with faststart",
        ),
        SkillStep(
            "timeline_report",
            {"project_id": "from create_project.id"},
            read="score 0-100 and the issue list",
        ),
        SkillStep(
            "approve_stage",
            {"project_id": "from create_project.id", "stage": "'video'"},
            read="status going to video_approved",
            note="HUMAN GATE: a person must have watched the export.",
        ),
        SkillStep(
            "publish_project",
            {"project_id": "from create_project.id"},
            read="status=published and the platform list",
        ),
    ),
    guardrails=(
        "Never set source_rights_confirmed yourself; only a human confirms rights.",
        "Both approval gates are human decisions. Ask, then record the answer — "
        "never approve on your own judgement.",
        "Fix every issue timeline_report names before asking for the next gate.",
        "render_video only runs in generating/video_review; it never publishes.",
    ),
    human_gates=("approve_stage(script)", "approve_stage(video)"),
)


_READ_MEDIA = Skill(
    name="read-a-clip-without-eyes",
    description=(
        "Turn a clip or image into text an agent can reason on: duration, "
        "loudness, silence, shot cuts, palette — no vision model required."
    ),
    when_to_use=(
        "Before any cut, mix or grade, and whenever the user asks what a file "
        "contains and you cannot look at it."
    ),
    steps=(
        SkillStep(
            "inspect_media",
            {"ref": "media-library id, edited asset id, or a path"},
            read="duration, size, codecs, fps — the shape of the file",
        ),
        SkillStep(
            "describe_media",
            {"ref": "the same ref, or a media id"},
            read=(
                "loudness (LUFS), silence ranges, shot-change times, palette, "
                "tempo, and OCR text when tesseract is installed"
            ),
            note="One call beats five: this is the survey before the edit.",
        ),
        SkillStep(
            "media_scene_cuts",
            {"ref": "the same ref"},
            read="cut timestamps, measured from histograms (no model needed)",
        ),
        SkillStep(
            "media_palette",
            {"ref": "the same ref"},
            read="dominant hex colours — use them to pick a grade that matches",
        ),
        SkillStep(
            "media_silence",
            {"ref": "an audio ref"},
            read="silence windows with timestamps; feed them to cut_media to "
            "tighten a take",
        ),
        SkillStep(
            "media_contact_sheet",
            {"ref": "the same ref"},
            read="one image of N frames — hand this to a human when a decision "
            "needs eyes",
        ),
    ),
    guardrails=(
        "Read before you cut: every edit decision should trace back to a number "
        "or a timestamp you actually read.",
        "When the answer needs eyes, return the contact sheet to the user instead "
        "of guessing.",
    ),
)


_BEAT_CUT = Skill(
    name="cut-on-the-beat",
    description=(
        "Cut picture to the music: read the tempo, split at beats, duck the "
        "narration under the track."
    ),
    when_to_use=(
        "The user wants a montage, a shorts-style edit, or any cut that should "
        "land on the music."
    ),
    steps=(
        SkillStep(
            "music_beat_grid",
            {"ref": "the music track"},
            read="bpm, beat and downbeat timestamps",
        ),
        SkillStep(
            "split_media",
            {"ref": "the video/audio to cut", "timestamps": "beats from the grid"},
            read="one asset_id per segment, in order",
        ),
        SkillStep(
            "auto_cut_to_beat",
            {"project_id": "the project to retime", "music_ref": "the same track"},
            read="the scene count after beat matching",
            note="Timeline-level alternative to hand splitting; gives bpm and "
            "beat_count back.",
        ),
        SkillStep(
            "audio_mix",
            {"tracks": "[{ref: voice, role: 'voice'}, {ref: music, gain_db: -14}]"},
            read="the mixed asset_id; role='voice' makes the music duck itself",
        ),
        SkillStep(
            "media_loudness",
            {"ref": "the mixed asset_id"},
            read="integrated LUFS, true peak and whether it clips",
        ),
        SkillStep(
            "timeline_report",
            {"project_id": "the project"},
            read="score and issues after the retime",
        ),
    ),
    guardrails=(
        "Keep the grid's timestamps; do not re-derive beats by ear or by guesswork.",
        "If the measured loudness misses the target, fix the gain and measure "
        "again rather than trusting the intent.",
    ),
)


_NARRATION_MUSIC = Skill(
    name="narration-over-music",
    description=(
        "Mix narration and music to a measured loudness target, with the music "
        "ducking under the voice."
    ),
    when_to_use=(
        "Producing a voiceover bed, a podcast mix, or any file where speech must "
        "stay intelligible."
    ),
    steps=(
        SkillStep(
            "media_loudness",
            {"ref": "the voice track"},
            read="integrated LUFS and gain_to_target_db",
        ),
        SkillStep(
            "media_loudness",
            {"ref": "the music track"},
            read="integrated LUFS and true peak",
        ),
        SkillStep(
            "audio_normalize",
            {"ref": "the voice track", "target_lufs": "e.g. -16 for speech"},
            read="the normalized asset_id",
        ),
        SkillStep(
            "audio_mix",
            {
                "tracks": (
                    "[{ref: normalized voice, role: 'voice'}, "
                    "{ref: music, gain_db: -12}]"
                )
            },
            read="the mixed asset_id",
        ),
        SkillStep(
            "media_loudness",
            {"ref": "the mixed asset_id"},
            read="integrated LUFS, true peak, and gain_to_target_db for the last trim",
        ),
        SkillStep(
            "apply_audio_mastering",
            {"audio_b64": "the mixed file as base64"},
            read="the mastered asset plus the report",
            note="Optional final polish; measure after it as well.",
        ),
    ),
    guardrails=(
        "Gain is measured, never guessed: call media_loudness before and after.",
        "A clipping true peak is a failed mix, not a stylistic choice.",
    ),
)


_SEO_LAUNCH = Skill(
    name="seo-launch-pack",
    description=(
        "Package a finished video for launch: score it, rewrite what is weak, "
        "plan the A/B test, then measure it for real."
    ),
    when_to_use=(
        "A video is approved and the question is how to publish it, or after "
        "publishing to explain why it underperformed."
    ),
    steps=(
        SkillStep(
            "seo_score_project",
            {"project_id": "an approved project"},
            read="score, grade, and which signals came back 'unknown'",
        ),
        SkillStep(
            "seo_rules",
            {},
            read="the thresholds and weights behind every score",
            note="Read this before arguing with a grade.",
        ),
        SkillStep(
            "seo_optimize",
            {"pack": "the pack to rewrite, including engagement if known"},
            read="changes (only measured improvements) and the re-scored pack",
        ),
        SkillStep(
            "seo_ab_plan",
            {"baseline_rate": "the current rate, e.g. 0.04"},
            read="per_arm and total impressions needed for a real result",
        ),
        SkillStep(
            "seo_ab_evaluate",
            {"arms": "[{impressions, conversions}, ...]"},
            read="winner, lift and p-value — a null result is an answer too",
        ),
        SkillStep(
            "seo_calibrate",
            {"observations": "real per-video outcomes from the channel"},
            read="suggested weights learned from actual performance",
        ),
    ),
    guardrails=(
        "Never invent engagement numbers; a missing signal lowers confidence, it "
        "does not become a passing grade.",
        "Only report gains seo_optimize measured. Do not promise a lift.",
        "Publishing is still behind the human approval gates.",
    ),
)


_REPAIR_TIMELINE = Skill(
    name="repair-a-timeline",
    description=(
        "Fix what a timeline report flags: adjust the scenes that fail, then "
        "prove the score moved before rendering."
    ),
    when_to_use=("timeline_report returned issues, or a render failed its QC checks."),
    steps=(
        SkillStep(
            "timeline_report",
            {"project_id": "the project"},
            read="score and every issue, with the scene it belongs to",
        ),
        SkillStep(
            "trim_scene",
            {
                "project_id": "the project",
                "scene_id": "from video_project.scenes[]",
                "trim_start": "in-point in seconds on the source",
                "trim_end": "out-point in seconds on the source",
            },
            read="the updated scene",
            note="Also available: set_scene_speed (speed), reverse_scene, "
            "delete_scene, merge_scene, split_scene, duplicate_scene, move_scene.",
        ),
        SkillStep(
            "set_scene_audio",
            {
                "project_id": "the project",
                "scene_id": "the scene to fix",
                "volume": "0..2 gain for this scene",
                "fade_in": "seconds",
                "fade_out": "seconds",
            },
            read="the updated scene audio",
        ),
        SkillStep(
            "bulk_update_scenes",
            {
                "project_id": "the project",
                "scene_ids": "every scene that shares the problem",
                "patch": "the shared fix",
            },
            read="the updated timeline",
        ),
        SkillStep(
            "render_plan",
            {"project_id": "the project"},
            read="aspect ratio, resolution, fps, step count — the export shape",
        ),
        SkillStep(
            "timeline_report",
            {"project_id": "the project"},
            read="the score must rise; if it did not, the fix did not land",
        ),
    ),
    guardrails=(
        "Re-measure after every change; a plausible fix that does not move the "
        "score is not a fix.",
        "Render only after the report is clean, and never render over a "
        "published project.",
    ),
)


_QC_BEFORE_APPROVAL = Skill(
    name="qc-before-approval",
    description=(
        "Assemble the evidence a person needs before signing an approval gate: "
        "measured audio, measured timeline, packaging, and a contact sheet."
    ),
    when_to_use=(
        "A video is rendered and someone must decide whether it is good enough "
        "to approve or publish."
    ),
    steps=(
        SkillStep(
            "describe_media",
            {"ref": "the rendered file or its media id"},
            read="duration, loudness, silences, shot changes, palette",
        ),
        SkillStep(
            "media_loudness",
            {"ref": "the rendered file"},
            read="integrated LUFS and whether the true peak clips",
        ),
        SkillStep(
            "timeline_report",
            {"project_id": "the project that was rendered"},
            read="score and remaining issues",
        ),
        SkillStep(
            "seo_score_project",
            {"project_id": "the project"},
            read="packaging score and unknown signals",
        ),
        SkillStep(
            "media_contact_sheet",
            {"ref": "the rendered file"},
            read="frames for the human reviewer",
        ),
    ),
    guardrails=(
        "Sensitivity and fact checks live on the HTTP API "
        "(POST /projects/{id}/sensitivity/audit, "
        "POST /projects/{id}/facts/reconcile) — run them for factual or "
        "monetisation-sensitive topics and pass the findings to the reviewer.",
        "Present evidence, never a verdict: the gate belongs to a human.",
    ),
    human_gates=("the reviewer decides; no tool may approve on their behalf",),
)


#: The catalog, in the order an agent should read it.
SKILLS: tuple[Skill, ...] = (
    _PIPELINE,
    _READ_MEDIA,
    _BEAT_CUT,
    _NARRATION_MUSIC,
    _REPAIR_TIMELINE,
    _QC_BEFORE_APPROVAL,
    _SEO_LAUNCH,
)

_BY_NAME: dict[str, Skill] = {skill.name: skill for skill in SKILLS}


def skill_names() -> list[str]:
    """Every skill name, in catalog order."""
    return [skill.name for skill in SKILLS]


def skill_index() -> list[dict[str, Any]]:
    """Level 1: the index an agent loads before choosing a skill."""
    return [skill.index_entry() for skill in SKILLS]


def read_skill(name: str) -> Skill | None:
    """Level 2: one full recipe, or ``None`` when the name is unknown."""
    return _BY_NAME.get(str(name).strip())
