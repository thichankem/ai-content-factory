"""SEO service layer: score, optimise and test a publish pack.

The mixin is deliberately thin. All arithmetic lives in :mod:`content_factory.seo`
(pure functions over a frozen :class:`~content_factory.seo.Pack`), and this layer
does exactly two extra things:

* **build the pack from a real project** — title, hook, runtime, aspect, caption
  state, chapter markers, on-screen text, cut rate and sound all come from the
  stored script and timeline, so the score describes what would actually ship;
* **let an external agent pass a pack straight in** as JSON, validated field by
  field, so an agent that has not built a project yet can still test metadata.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .. import script_engine, seo
from ..models import AbArmInput, CompetitorVideoInput, SeoEngagementInput, SeoPackInput
from ..seo import Engagement, Pack
from .timeline import TimelineMixin

__all__ = [
    "SeoMixin",
    "arm_from_mapping",
    "competitor_from_mapping",
    "pack_from_mapping",
]


def _engagement_from_mapping(data: Mapping[str, Any]) -> Engagement:
    return SeoEngagementInput.model_validate(data).to_engine()


def arm_from_mapping(data: Mapping[str, Any]) -> seo.AbArm:
    return AbArmInput.model_validate({"name": "arm", **data}).to_engine()


def competitor_from_mapping(data: Mapping[str, Any]) -> seo.CompetitorVideo:
    return CompetitorVideoInput.model_validate({"title": "", **data}).to_engine()


def pack_from_mapping(data: Mapping[str, Any] | None) -> Pack:
    return SeoPackInput.model_validate({} if data is None else data).to_engine()


#: A dimension at or above this score is reported as passing to a UI.
_DIMENSION_PASS = 70.0


def _flat_platform_view(report: Mapping[str, Any]) -> dict[str, Any]:
    """Add the flat view a UI binds to, derived from the report itself.

    The scored report is nested because that is the honest shape: a score is made
    of four weighted dimensions, each made of signals, each with its own evidence.
    A dashboard does not want to walk that tree, so this projects it onto the
    handful of fields a card renders — ``score``/``grade`` plus a ``breakdown``
    keyed by dimension and a ``fixes`` list. Nothing is invented: ``breakdown``
    entries are the engine's own dimension scores, and ``fixes`` are its own
    ``quick_wins``, which already carry the points on the table.
    """
    flat: dict[str, Any] = dict(report)
    dimensions = report.get("dimensions") or []
    flat["passed"] = bool(report.get("score", 0) >= _DIMENSION_PASS) and not report.get(
        "capped"
    )
    flat["breakdown"] = {
        str(dimension.get("key", "")): {
            "score": float(dimension.get("score", 0.0)),
            "weight": float(dimension.get("weight", 0.0)),
            "label": str(dimension.get("label", "")),
            "passed": float(dimension.get("score", 0.0)) >= _DIMENSION_PASS,
        }
        for dimension in dimensions
    }
    flat["fixes"] = [
        {
            "signal": str(win.get("label", "")),
            "gain": float(win.get("points", 0.0)),
            "action": str(win.get("fix") or ""),
        }
        for win in report.get("quick_wins") or []
    ]
    return flat


def _optimize_view(result: Mapping[str, Any]) -> dict[str, Any]:
    """Add the names a UI reads to an optimiser result.

    The engine calls the rewritten pack ``pack`` and the list of edits
    ``changes``. Clients built against the earlier draft expect ``optimized_pack``
    and ``applied_fixes``; both spellings are returned so neither has to change.
    """
    flat: dict[str, Any] = dict(result)
    flat["optimized_pack"] = result.get("pack")
    flat["applied_fixes"] = list(result.get("changes") or [])
    return flat


def _int_or(value: Any, default: int = 0) -> int:
    """``int(value)``, with ``None`` and junk degrading to ``default``.

    :func:`~content_factory.seo.plan_ab_test` reports ``days=None`` whenever it
    had no ``daily_traffic`` to divide by. Coercing that honestly-unknown value
    straight to ``int`` raised inside the response view, so a caller that simply
    omitted traffic got a 500 instead of a plan.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ab_plan_view(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Add the sample-size aliases a UI reads, keeping the canonical names.

    ``minimum_detectable_effect`` is the absolute rate difference the plan is
    powered to see (``target_rate - baseline_rate``), not the relative lift — a
    client that renders one number next to a percentage wants the absolute one.

    ``estimated_days`` is ``0`` when the plan could not estimate a duration
    because no ``daily_traffic`` was supplied; that ``0`` means "not estimated",
    never "instant", and ``days`` still carries the honest ``None``.
    """
    flat: dict[str, Any] = dict(plan)
    baseline = float(plan.get("baseline_rate", 0.0) or 0.0)
    target = float(plan.get("target_rate", 0.0) or 0.0)
    flat["sample_size_per_arm"] = _int_or(plan.get("per_arm"))
    flat["total_sample_size"] = _int_or(plan.get("total"))
    flat["estimated_days"] = _int_or(plan.get("days"))
    flat["minimum_detectable_effect"] = round(abs(target - baseline), 6)
    return flat


class SeoMixin(TimelineMixin):
    """SEO scoring, optimisation and experiment design."""

    # --- pure engine surfaces -----------------------------------------------

    def seo_rules(self) -> list[dict[str, Any]]:
        """Every platform rule, threshold and signal weight the scorer uses."""
        return seo.platform_rules()

    def seo_score(
        self, platform: str, pack: Pack | Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Score a pack for one platform, or for every platform with 'all'."""
        resolved = self._coerce_pack(pack)
        key = (platform or "youtube").strip().lower()
        if key == "all":
            return {
                name: _flat_platform_view(report.to_dict())
                for name, report in seo.score_platforms(resolved).items()
            }
        return _flat_platform_view(seo.score_pack(resolved, key).to_dict())

    def seo_optimize(
        self, platform: str, pack: Pack | Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Rewrite the pack for maximum score and report the measured gain."""
        resolved = self._coerce_pack(pack)
        key = (platform or "youtube").strip().lower()
        if key == "all":
            return {
                name: _optimize_view(seo.optimize_pack(resolved, name).to_dict())
                for name in ("youtube", "tiktok")
            }
        return _optimize_view(seo.optimize_pack(resolved, key).to_dict())

    def seo_ab_plan(
        self,
        metric: str,
        baseline_rate: float,
        *,
        relative_lift: float = 0.15,
        daily_traffic: int | None = None,
        arms: int = 2,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> dict[str, Any]:
        """Size an A/B test so a decision is statistically valid."""
        return _ab_plan_view(
            seo.plan_ab_test(
                metric,
                baseline_rate,
                relative_lift=relative_lift,
                daily_traffic=daily_traffic,
                arms=arms,
                alpha=alpha,
                power=power,
            ).to_dict()
        )

    def seo_ab_evaluate(
        self,
        metric: str,
        arms: Sequence[seo.AbArm | Mapping[str, Any]],
        *,
        alpha: float = 0.05,
        relative_lift: float = 0.15,
    ) -> dict[str, Any]:
        """Decide whether one variant really beat another, with a p-value."""
        resolved = [
            arm if isinstance(arm, seo.AbArm) else arm_from_mapping(arm) for arm in arms
        ]
        return seo.evaluate_ab_test(
            resolved, metric, alpha=alpha, relative_lift=relative_lift
        ).to_dict()

    def seo_keywords(
        self,
        keywords: Sequence[str],
        competitors: Sequence[seo.CompetitorVideo | Mapping[str, Any]] = (),
        *,
        pack: Pack | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rank phrases by demand vs competition and mine winning phrasings."""
        resolved_pack = None if pack is None else self._coerce_pack(pack)
        rows = [
            row
            if isinstance(row, seo.CompetitorVideo)
            else competitor_from_mapping(row)
            for row in competitors
        ]
        return seo.keyword_opportunities(keywords, rows, pack=resolved_pack).to_dict()

    def seo_calibrate(
        self,
        observations: Sequence[tuple[Mapping[str, float], float]],
        platform: str = "youtube",
        *,
        outcome: str = "views_per_day",
    ) -> dict[str, Any]:
        """Learn which signals actually predict this channel's results."""
        rows = [(dict(signals), float(value)) for signals, value in observations]
        return seo.calibrate(rows, platform, outcome=outcome).to_dict()

    # --- scoring a real project ---------------------------------------------

    def seo_score_project(
        self,
        project_id: str,
        platform: str = "youtube",
        *,
        keywords: Sequence[str] | None = None,
        publish_hour: int | None = None,
        audience_hours: Sequence[int] = (),
        description: str | None = None,
        tags: Sequence[str] = (),
        hashtags: Sequence[str] = (),
        title: str | None = None,
        engagement: Engagement | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Score the pack this project would actually publish.

        Everything measurable is read from the stored project: the script's hook
        section, the timeline's runtime and cut rate, aspect ratio, caption and
        music settings, chapter markers, and the on-screen text of each scene.
        Values that simply are not recorded (intro length, loop friendliness)
        stay ``unknown`` and lower confidence instead of being invented.
        """
        project = self.get_project(project_id)
        video = project.video_project
        hook = self._script_hook(project.script)
        if video is not None and video.scenes:
            total_seconds = sum(scene.duration_seconds for scene in video.scenes)
            cuts_per_minute = (
                len(video.scenes) / (total_seconds / 60.0) if total_seconds else None
            )
            aspect_ratio = video.aspect_ratio
            has_captions: bool | None = video.captions
            on_screen = tuple(scene.text for scene in video.scenes if scene.text)
            markers = list(video.markers)
            chapters = [
                marker for marker in markers if "chapter" in marker.label.lower()
            ]
            beat_synced: bool | None = bool(
                [marker for marker in markers if "beat" in marker.label.lower()]
            )
            sound = "background music" if video.background_music else ""
        else:
            total_seconds = float(project.duration_target_seconds)
            cuts_per_minute = None
            aspect_ratio = ""
            has_captions = None
            on_screen = ()
            chapters = []
            beat_synced = None
            sound = ""

        measured = (
            engagement
            if isinstance(engagement, Engagement)
            else _engagement_from_mapping(engagement or {})
        )
        has_engagement = bool(measured and measured.views > 0)
        pack = Pack(
            title=title if title is not None else self._project_title(project),
            description=description
            if description is not None
            else (project.script or ""),
            tags=tuple(tags),
            hashtags=tuple(hashtags),
            keywords=tuple(keywords or (project.topic,)),
            script=project.script or "",
            hook=hook,
            duration_seconds=total_seconds or None,
            aspect_ratio=aspect_ratio,
            thumbnail_present=bool(project.video and project.video.thumbnail_url),
            on_screen_text=on_screen,
            has_captions=has_captions,
            has_chapters=bool(chapters),
            chapter_count=len(chapters),
            sound=sound,
            beat_synced=beat_synced,
            bpm=video.bpm if video is not None else None,
            cuts_per_minute=cuts_per_minute,
            publish_hour=publish_hour,
            audience_hours=tuple(audience_hours),
            # We render from our own master, so no third-party watermark.
            watermark=False,
            language=project.target_language,
            engagement=measured if has_engagement else None,
        )
        key = (platform or "youtube").strip().lower()
        if key == "all":
            reports = seo.score_platforms(pack)
        else:
            reports = {key: seo.score_pack(pack, key)}
        views = {
            name: _flat_platform_view(report.to_dict())
            for name, report in reports.items()
        }
        primary = views.get(key) or next(iter(views.values()))
        return {
            "project_id": project.id,
            "platforms": views,
            # The requested platform's score, flattened to the top level, so a
            # card can render `score`/`grade`/`breakdown`/`fixes` without knowing
            # which platform it asked for or walking the `platforms` map.
            "platform": primary.get("platform", key),
            "score": primary.get("score", 0),
            "grade": primary.get("grade", ""),
            "passed": primary.get("passed", False),
            "breakdown": primary.get("breakdown", {}),
            "fixes": primary.get("fixes", []),
            "verdict": primary.get("verdict", ""),
            "projected_score": primary.get("projected_score", 0),
            "pack_used": {
                "title": pack.title,
                "keywords": list(pack.keywords),
                "duration_seconds": pack.duration_seconds,
                "aspect_ratio": pack.aspect_ratio,
                "cuts_per_minute": pack.cuts_per_minute,
                "hook": pack.hook,
                "sound": pack.sound,
                "has_captions": pack.has_captions,
                "chapter_count": pack.chapter_count,
            },
        }

    # --- helpers -------------------------------------------------------------

    def _coerce_pack(self, pack: Pack | Mapping[str, Any] | None) -> Pack:
        if isinstance(pack, Pack):
            return pack
        return pack_from_mapping(pack)

    @staticmethod
    def _script_hook(script: str | None) -> str:
        """First section of the script, the line that has to stop the scroll."""
        if not script or not script.strip():
            return ""
        sections = script_engine.parse_script(script)
        for section in sections:
            text = (section.text or "").strip()
            if text:
                return text.split("\n", 1)[0].strip()
        return ""

    @staticmethod
    def _project_title(project: Any) -> str:
        return str(getattr(project, "name", "") or getattr(project, "topic", ""))
