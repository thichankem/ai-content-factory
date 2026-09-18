from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ._helpers import (
    _PLACEBO_HASHTAGS,
    _band,
    _clamp,
    _fold,
    _front_load,
    _mentions,
    _ratio,
    _sentences,
    _words,
)
from .contracts import Pack
from .profiles import PlatformProfile

_SigOut = tuple[float | None, str, str | None]


@dataclass(frozen=True)
class _Spec:
    id: str
    label: str
    dimension: str
    weight: float
    fn: Callable[[Pack, PlatformProfile], _SigOut]
    blocking: bool = False
    #: Extra condition for a blocking spec: it only caps the score when the pack
    #: is genuinely unusable (empty or truncated title), not merely sub-optimal.
    #: A short title or a 4-minute runtime are recommendations, not publish
    #: blockers, so they must never freeze the score at the cap.
    blocking_when: Callable[[Pack, PlatformProfile], bool] | None = None


def _title_unusable(pack: Pack, prof: PlatformProfile) -> bool:
    """True only when the title cannot be published as written."""
    if prof.key == "tiktok":
        return False
    title = pack.title.strip()
    return not title or len(title) > prof.title_hard_max


def _fmt_seconds(value: float) -> str:
    if value >= 60:
        return f"{value / 60:.1f} min"
    return f"{value:.0f}s"


def _title_length(pack: Pack, prof: PlatformProfile) -> _SigOut:
    length = len(pack.title.strip())
    hard = prof.title_hard_max
    if prof.key == "tiktok":
        return None, "TikTok has no separate title field.", None
    if length == 0:
        return 0.0, "No title.", "Write a title that front-loads the search phrase."
    score = _band(length, *prof.title_ideal) or 0.0
    detail = f"Title is {length} characters."
    fix = None
    if length > hard:
        detail = f"Title is {length} characters; YouTube truncates at {hard}."
        fix = f"Cut the title below {prof.title_ideal[1]} characters."
    elif score < 1.0:
        fix = f"Aim for {prof.title_ideal[0]}-{prof.title_ideal[1]} characters."
    return score, detail, fix


def _title_keyword(pack: Pack, prof: PlatformProfile) -> _SigOut:
    keyword = pack.primary_keyword
    if not keyword:
        return (
            None,
            "No target keyword supplied.",
            "Name the phrase you want to rank for.",
        )
    if prof.key == "tiktok":
        return None, "TikTok ranks on the caption, not a title.", None
    score = _front_load(pack.title, keyword, max(20, len(pack.title) // 2))
    hits = _mentions(pack.title, keyword)
    if hits == 0:
        return (
            0.0,
            f"Title never says the search phrase {keyword!r}.",
            f"Put {keyword!r} in the first half of the title.",
        )
    return (
        score or 0.0,
        f"{keyword!r} appears {hits}x in the title.",
        "Move the phrase closer to the start of the title."
        if (score or 0) < 1
        else None,
    )


def _title_style(pack: Pack, prof: PlatformProfile) -> _SigOut:
    title = pack.title.strip()
    if not title:
        return 0.0, "No title.", "Write a title."
    words = _words(title)
    score = 1.0
    notes: list[str] = []
    if len(words) > 14:
        score -= 0.25
        notes.append(f"{len(words)} words is long")
    letters = [ch for ch in title if ch.isalpha()]
    if letters and sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.5:
        score -= 0.3
        notes.append("mostly capitals reads as shouting")
    if any(ch.isdigit() for ch in title):
        score += 0.0
    if re.search(
        r"\b(best|tốt nhất|top|how|why|cách|bí mật|hướng dẫn)\b", _fold(title)
    ):
        notes.append("clear promise word")
    return (
        _clamp(score),
        ("Title style: " + ", ".join(notes))
        if notes
        else "Title length and casing are clean.",
        "Keep the title under 14 words and use sentence case."
        if score < 0.85
        else None,
    )


def _description_keyword_zone(pack: Pack, prof: PlatformProfile) -> _SigOut:
    keyword = pack.primary_keyword
    body = pack.description.strip()
    if not body:
        return (
            0.0,
            "No description or caption.",
            "Write an opening line with the keyword.",
        )
    if not keyword:
        return (
            None,
            "No target keyword supplied.",
            "Name the phrase you want to rank for.",
        )
    zone = prof.keyword_zone
    first = body[:zone]
    if _mentions(first, keyword) == 0:
        return (
            0.0,
            f"{keyword!r} is missing from the first {zone} characters.",
            f"Open the {'caption' if prof.key == 'tiktok' else 'description'} with "
            f"{keyword!r}.",
        )
    hits = _mentions(body, keyword)
    score = 1.0 if hits <= 4 else max(0.4, 1.0 - (hits - 4) * 0.15)
    return (
        score,
        f"{keyword!r} appears {hits}x, first inside the opening {zone} characters.",
        "Keyword appears unusually often; keep it natural." if hits > 4 else None,
    )


def _description_depth(pack: Pack, prof: PlatformProfile) -> _SigOut:
    body = pack.description.strip()
    if not body:
        return 0.0, "No description or caption.", "Write the description."
    length = len(body)
    words = len(_words(body))
    score = _band(length, *prof.description_ideal_chars) or 0.0
    word_score = _ratio(words, prof.description_ideal_words) or 0.0
    combined = _clamp(0.6 * score + 0.4 * min(1.0, word_score))
    fix = None
    if length > prof.description_hard_max:
        combined = 0.2
        fix = f"Trim to {prof.description_hard_max} characters."
    elif combined < 0.85:
        fix = (
            f"Expand to about {prof.description_ideal_words} words "
            f"({prof.description_ideal_chars[0]}-{prof.description_ideal_chars[1]} "
            f"characters)."
        )
    return combined, f"Description has {words} words / {length} characters.", fix


def _keyword_coverage(pack: Pack, prof: PlatformProfile) -> _SigOut:
    keywords = list(pack.keywords)
    if not keywords:
        return None, "No keyword list supplied.", "Supply the phrases to cover."
    haystack = " ".join(
        [
            pack.title,
            pack.description,
            " ".join(pack.tags),
            " ".join(pack.hashtags),
            " ".join(pack.on_screen_text),
            pack.script,
        ]
    )
    covered = [kw for kw in keywords if _mentions(haystack, kw) > 0]
    missing = [kw for kw in keywords if kw not in covered]
    score = _clamp(len(covered) / len(keywords))
    detail = f"{len(covered)}/{len(keywords)} target phrases appear somewhere."
    fix = f"Work in: {', '.join(missing)}." if missing else None
    return score, detail, fix


def _hashtag_count(pack: Pack, prof: PlatformProfile) -> _SigOut:
    tags = [tag.lstrip("#") for tag in pack.hashtags if tag.strip()]
    count = len(tags)
    low, high = prof.hashtag_ideal
    if prof.key == "youtube" and count > prof.hashtag_hard_max:
        return (
            0.0,
            f"{count} hashtags; YouTube ignores every hashtag above "
            f"{prof.hashtag_hard_max}.",
            f"Keep to {low}-{high} relevant hashtags.",
        )
    score = _band(count, low, high, falloff=max(4.0, high)) or 0.0
    placebo = [tag for tag in tags if _fold(tag).strip("#") in _PLACEBO_HASHTAGS]
    if placebo:
        score = max(0.3, score - 0.15)
    detail = f"{count} hashtags (target {low}-{high})."
    fix = None
    if count < low:
        fix = "Add hashtags that name the topic, not the algorithm."
    elif count > high:
        fix = "Fewer, more specific hashtags beat a wall of generic ones."
    if placebo and fix is None:
        fix = (
            f"{', '.join('#' + t for t in placebo)} carries no ranking value; "
            "replace with topic hashtags."
        )
    return score, detail, fix


def _tags(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.tags_ideal == (0, 0):
        return None, "TikTok has no tag field; hashtags carry this role.", None
    tags = [tag.strip() for tag in pack.tags if tag.strip()]
    count = len(tags)
    low, high = prof.tags_ideal
    score = _band(count, low, high, falloff=max(4.0, high)) or 0.0
    keyword = pack.primary_keyword
    detail = f"{count} tags (target {low}-{high})."
    fix = None
    if keyword and not any(_mentions(tag, keyword) for tag in tags):
        score = max(0.25, score - 0.4)
        fix = f"Add {keyword!r} itself as a tag."
    multiword = sum(1 for tag in tags if len(_words(tag)) >= 2)
    if tags and multiword / len(tags) < 0.5:
        score = max(0.4, score - 0.15)
        fix = fix or "Favour long-tail multi-word tags over single generic words."
    elif count < low:
        fix = fix or "Add more long-tail tags."
    return score, detail, fix


def _chapters(pack: Pack, prof: PlatformProfile) -> _SigOut:
    duration = pack.duration_seconds
    if prof.short_form:
        return None, "Chapters do not exist on short-form.", None
    if duration is None:
        return (
            None,
            "Runtime unknown, cannot judge chapter need.",
            "Report the duration.",
        )
    needs = duration > 300.0
    if not needs:
        return 1.0, f"{_fmt_seconds(duration)} does not need chapters.", None
    if pack.has_chapters and pack.chapter_count >= 3:
        return 1.0, f"{pack.chapter_count} chapters on a long video.", None
    return (
        0.25 if pack.has_chapters else 0.0,
        "Long video without (enough) chapters.",
        "Add timestamps starting at 00:00, at least three of them.",
    )


def _caption_keyword(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.key != "tiktok":
        return None, "Not a TikTok surface.", None
    keyword = pack.primary_keyword
    if not keyword:
        return None, "No target keyword supplied.", "Name the phrase to rank for."
    score = _front_load(pack.description, keyword, prof.keyword_zone)
    if score is None:
        return 0.0, "Empty caption.", "Open the caption with the keyword phrase."
    return (
        score,
        f"Caption keyword position scored {score:.2f}.",
        None if score >= 0.85 else f"Start the caption with {keyword!r}.",
    )


def _on_screen_text(pack: Pack, prof: PlatformProfile) -> _SigOut:
    overlays = [line for line in pack.on_screen_text if line.strip()]
    if not overlays:
        return (
            0.0,
            "No on-screen text reported.",
            "TikTok indexes on-screen text; label the video with the topic in frame.",
        )
    keyword = pack.primary_keyword
    hits = sum(1 for line in overlays if keyword and _mentions(line, keyword))
    score = 1.0 if keyword and hits else 0.6
    return (
        score,
        f"{len(overlays)} on-screen text lines, {hits} mention the target phrase.",
        None
        if hits
        else f"Put {keyword!r} on screen once; the ranked text index reads it.",
    )


def _spoken_keyword(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if not pack.script.strip():
        return None, "No script or transcript supplied.", "Supply the narration text."
    keyword = pack.primary_keyword
    if not keyword:
        return None, "No target keyword supplied.", "Name the phrase to rank for."
    hits = _mentions(pack.script, keyword)
    return (
        _clamp(hits / 2),
        f"The spoken script says {keyword!r} {hits}x.",
        None if hits else f"Say {keyword!r} out loud; TikTok transcribes audio.",
    )


def _thumbnail_present(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.key == "tiktok":
        return None, "TikTok opens on the video frame, not a cover file.", None
    if pack.thumbnail_present is None:
        return None, "No thumbnail information.", "Attach a thumbnail."
    if not pack.thumbnail_present:
        return (
            0.0,
            "No custom thumbnail.",
            "Upload a thumbnail; it drives the click more than the title.",
        )
    return 1.0, "Custom thumbnail attached.", None


def _thumbnail_text(pack: Pack, prof: PlatformProfile) -> _SigOut:
    text = pack.thumbnail_text.strip()
    if prof.key == "tiktok":
        text = text or " ".join(pack.on_screen_text[:1])
    if not text:
        return (
            0.5 if prof.key == "tiktok" else 0.4,
            "No text words reported for the cover frame.",
            "Three or four large words raise mobile click-through.",
        )
    words = _words(text)
    score = _band(float(len(words)), 1.0, 4.0, falloff=4.0) or 0.0
    return (
        score,
        f"Cover text has {len(words)} words.",
        None if score >= 0.85 else "Trim cover text to four words or fewer.",
    )


def _title_cover_complement(pack: Pack, prof: PlatformProfile) -> _SigOut:
    cover = pack.thumbnail_text.strip() or " ".join(pack.on_screen_text)
    if not cover or not pack.title.strip():
        return None, "Need both the title and the cover text to compare.", None
    title_words = set(_words(pack.title))
    cover_words = set(_words(cover))
    shared = title_words & cover_words
    score = 1.0 - min(0.7, len(shared) / max(1, len(cover_words) or 1))
    if not shared:
        score = 1.0
    return (
        score,
        f"{len(shared)} words repeated between title and cover.",
        None
        if score >= 0.85
        else "Let the cover add information instead of repeating the title.",
    )


def _aspect(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if not pack.aspect_ratio:
        return None, "No aspect ratio reported.", "Report the render aspect ratio."
    allowed = prof.aspect_required
    if pack.aspect_ratio in allowed:
        return 1.0, f"Aspect {pack.aspect_ratio} is allowed.", None
    return (
        0.0,
        f"{prof.label} expects {' or '.join(allowed)}, got {pack.aspect_ratio}.",
        f"Re-render in {' or '.join(allowed)}.",
    )


def _hook(pack: Pack, prof: PlatformProfile) -> _SigOut:
    hook = pack.hook.strip()
    if not hook and pack.script.strip():
        sentences = _sentences(pack.script)
        hook = sentences[0] if sentences else ""
    if not hook:
        return (
            0.0,
            "No hook text.",
            "Write the opening line; the hook decides most of the retention.",
        )
    words = _words(hook)
    score = 1.0
    if len(words) > 14:
        score -= 0.35
    if len(words) > 22:
        score -= 0.2
    if re.search(r"^(hi|hello|hey|xin chào|chào)", _fold(hook)):
        score -= 0.25
    if any(ch.isdigit() for ch in hook):
        score += 0.05
    score = _clamp(score)
    window = _fmt_seconds(prof.hook_window)
    return (
        score,
        f"Hook is {len(words)} words; the first {window} decide retention.",
        None
        if score >= 0.85
        else "Open with the payoff or the tension, not a greeting.",
    )


def _intro_delay(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.intro_seconds is None:
        return (
            None,
            "Intro length not reported.",
            "Report the time before the hook starts.",
        )
    limit = 0.5 if prof.short_form else 5.0
    if pack.intro_seconds <= limit:
        return 1.0, f"Hook starts at {pack.intro_seconds:.1f}s.", None
    return (
        _clamp(1.0 - (pack.intro_seconds - limit) / (limit * 4)),
        f"Nothing happens for the first {pack.intro_seconds:.1f}s.",
        "Cut the logo or ident; start on the first useful frame.",
    )


def _pacing(pack: Pack, prof: PlatformProfile) -> _SigOut:
    cuts = pack.cuts_per_minute
    if cuts is None:
        return None, "Cut rate not reported.", "Report cuts per minute (or shots)."
    return (
        _ratio(cuts, prof.cuts_per_minute_min),
        f"{cuts:.1f} cuts per minute (target {prof.cuts_per_minute_min:.0f}+).",
        None
        if cuts >= prof.cuts_per_minute_min
        else "Cut more often; a static shot loses the feed scroll.",
    )


def _loop(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if not prof.short_form:
        return None, "Loops only matter on short-form.", None
    if pack.loop_friendly is None:
        return (
            None,
            "Loop friendliness not reported.",
            "Report whether the end feeds the start.",
        )
    if pack.loop_friendly:
        return 1.0, "The ending feeds back into the opening.", None
    return (
        0.35,
        "The ending does not invite a second watch.",
        "End on a beat that makes the first frame make sense again.",
    )


def _cta_placement(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if not pack.script.strip():
        return None, "No script supplied.", None
    folded = _fold(pack.script)
    cue = re.search(
        r"\b(subscribe|like and|follow|đăng ký|theo dõi|bấm like)\b", folded
    )
    if cue is None:
        return (
            0.5,
            "No CTA in the script.",
            "Ask for the follow near the end, with a reason.",
        )
    position = cue.start() / max(1, len(folded))
    if position < 0.15:
        return (
            0.3,
            f"CTA appears at {position * 100:.0f}% of the script.",
            "Move the ask into the last third; an early ask costs retention.",
        )
    return 1.0, f"CTA sits at {position * 100:.0f}% of the script.", None


def _duration_fit(pack: Pack, prof: PlatformProfile) -> _SigOut:
    duration = pack.duration_seconds
    if duration is None:
        return None, "Runtime unknown.", "Report the duration."
    if duration > prof.duration_hard_max:
        return (
            0.0,
            f"{_fmt_seconds(duration)} exceeds the "
            f"{_fmt_seconds(prof.duration_hard_max)} upload limit.",
            "Cut the video below the platform limit.",
        )
    score = _band(duration, *prof.duration_ideal) or 0.0
    fix = None
    if score < 0.85:
        low, high = prof.duration_ideal
        fix = (
            f"{_fmt_seconds(low)}-{_fmt_seconds(high)} is where completion holds "
            "for this format."
        )
    return score, f"Runtime is {_fmt_seconds(duration)}.", fix


def _measured_retention(pack: Pack, prof: PlatformProfile) -> _SigOut:
    engagement = pack.engagement
    if engagement is None or engagement.views <= 0:
        return None, "Not published yet (or no analytics supplied).", None
    parts: list[float] = []
    detail: list[str] = []
    fix: list[str] = []
    completion = engagement.completion_rate
    if (
        completion is None
        and engagement.average_view_seconds is not None
        and pack.duration_seconds
    ):
        completion = engagement.average_view_seconds / pack.duration_seconds
    if completion is not None:
        parts.append(_ratio(completion, prof.completion_target) or 0.0)
        detail.append(
            f"completion {completion * 100:.0f}% "
            f"(target {prof.completion_target * 100:.0f}%)"
        )
        if completion < prof.completion_target:
            fix.append("Tighten the middle; completion is below the platform target.")
    ratio = engagement.avd_ratio(pack.duration_seconds)
    if ratio is not None:
        parts.append(_ratio(ratio, prof.avd_ratio_target) or 0.0)
        detail.append(
            f"watch ratio {ratio * 100:.0f}% "
            f"(target {prof.avd_ratio_target * 100:.0f}%)"
        )
    if not parts:
        return (
            None,
            "Analytics supplied but no watch-time fields.",
            "Send watch time or completion.",
        )
    return (
        sum(parts) / len(parts),
        "Measured: " + ", ".join(detail) + ".",
        fix[0] if fix else None,
    )


def _measured_distribution(pack: Pack, prof: PlatformProfile) -> _SigOut:
    engagement = pack.engagement
    if engagement is None or engagement.views <= 0:
        return None, "Not published yet (or no analytics supplied).", None
    views = engagement.views
    shares = engagement.shares / views
    saves = engagement.saves / views
    likes = engagement.likes / views
    ratio_scores = [_ratio(shares, 0.01) or 0.0, _ratio(likes, 0.04) or 0.0]
    if engagement.saves:
        ratio_scores.append(_ratio(saves, 0.02) or 0.0)
    detail = (
        f"share rate {shares * 100:.2f}%, like rate {likes * 100:.1f}%, "
        f"{engagement.comments} comments"
    )
    ctr = engagement.ctr_pct()
    fix = None
    if ctr is not None and ctr < prof.ctr_target and prof.ctr_target > 0:
        fix = f"Impressions CTR {ctr:.1f}% is under the {prof.ctr_target:.0f}% target."
    return sum(ratio_scores) / len(ratio_scores), "Measured: " + detail + ".", fix


def _sound_trend(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.key != "tiktok":
        return None, "Trend sounds are a TikTok surface.", None
    if not pack.sound:
        return (
            0.2,
            "No sound reported.",
            "Ride a trending sound or a strong original audio bed.",
        )
    if pack.sound_trending is None:
        return (
            None,
            f"Sound {pack.sound!r} has no trend flag.",
            "Report whether it trends.",
        )
    if pack.sound_trending:
        return 1.0, f"Using trending sound {pack.sound!r}.", None
    return (
        0.6,
        f"Sound {pack.sound!r} is not trending.",
        "A trending sound adds reach, but keep the audio original enough "
        "to stay yours.",
    )


def _beat_sync(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.beat_synced is None:
        return None, "Beat sync not reported.", "Report whether cuts land on the beat."
    if pack.beat_synced:
        return 1.0, "Cuts are beat-synced.", None
    return 0.4, "Cuts are not beat-synced.", "Align the cuts to the music's beat grid."


def _safe_zone(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if not prof.short_form:
        return None, "Safe zones are a short-form concern.", None
    if pack.text_in_safe_zone is None:
        return (
            None,
            "Safe-zone placement not reported.",
            "Report whether text stays clear of UI.",
        )
    if pack.text_in_safe_zone:
        return 1.0, "Overlay text stays inside the UI safe zone.", None
    return (
        0.2,
        "Overlay text collides with the like/comment UI.",
        "Keep text out of the bottom fifth and the right edge of the frame.",
    )


def _end_screen(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.has_end_screen is None:
        return None, "End screen not reported.", "Report whether one exists."
    if pack.has_end_screen:
        return 1.0, "End screen present (subscribe + next video).", None
    return (
        0.2,
        "No end screen.",
        "Add an end screen pointing at the next video in the series.",
    )


def _playlist(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.short_form:
        return None, "Playlists are a long-form surface.", None
    if pack.playlist:
        return 1.0, f"Filed under playlist {pack.playlist!r}.", None
    return (
        0.3,
        "Not in a playlist.",
        "Put the video in a topical playlist; it feeds session watch time.",
    )


def _publish_window(pack: Pack, prof: PlatformProfile) -> _SigOut:
    hour = pack.publish_hour
    if hour is None:
        return (
            None,
            "Publish hour not supplied.",
            "Report the intended local publish hour.",
        )
    if pack.audience_hours:
        if hour in pack.audience_hours:
            return (
                1.0,
                f"Publishing at {hour:02d}:00 hits the audience-active window.",
                None,
            )
        nearest = min(
            pack.audience_hours, key=lambda h: min(abs(h - hour), 24 - abs(h - hour))
        )
        return (
            0.4,
            f"{hour:02d}:00 is outside the active hours {sorted(pack.audience_hours)}.",
            f"Move the publish to about {nearest:02d}:00.",
        )
    fallback = (
        (6, 7, 8, 12, 13, 19, 20, 21, 22)
        if prof.key == "tiktok"
        else (14, 15, 16, 19, 20)
    )
    if hour in fallback:
        return 1.0, f"{hour:02d}:00 sits in a typical active window.", None
    return (
        0.5,
        f"{hour:02d}:00 is a guess without audience analytics.",
        f"Benchmark {prof.label} windows start around "
        f"{', '.join(f'{h:02d}:00' for h in fallback[:4])}.",
    )


def _comment_prompt(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.comment_prompt:
        return 1.0, "The video asks a question, inviting comments.", None
    return (
        0.35,
        "No question or comment prompt.",
        "Ask one specific question; comments lift both platforms.",
    )


def _series(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.series_part is None:
        return (
            None,
            "Not marked as part of a series.",
            "Number the series in the title or caption.",
        )
    if pack.series_part >= 2:
        return 1.0, f"Marked as part {pack.series_part} of a series.", None
    return (
        0.7,
        "First part of a series.",
        "Plan the next part before publishing this one.",
    )


def _repost_watermark(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.key != "tiktok":
        return None, "Watermark penalty is a TikTok concern.", None
    if pack.watermark is None:
        return (
            None,
            "Watermark status not reported.",
            "Report whether another app's mark is visible.",
        )
    if not pack.watermark:
        return 1.0, "No third-party watermark.", None
    return (
        0.0,
        "Another app's watermark is visible (repost signal).",
        "Re-export from the master; reposted watermarked clips are down-ranked.",
    )


def _duet_stitch(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if prof.key != "tiktok":
        return None, "Duet/stitch are TikTok settings.", None
    if pack.duet_stitch_enabled is None:
        return None, "Duet/stitch setting not reported.", "Report it."
    if pack.duet_stitch_enabled:
        return 1.0, "Duet and stitch are open.", None
    return (
        0.5,
        "Duet and stitch are closed.",
        "Leave them open unless rights forbid it; they create free distribution.",
    )


def _captions(pack: Pack, prof: PlatformProfile) -> _SigOut:
    if pack.has_captions is None:
        return (
            None,
            "Caption availability not reported.",
            "Report whether captions exist.",
        )
    if pack.has_captions:
        return 1.0, "Captions available (most short-form is watched muted).", None
    return (
        0.3,
        "No captions.",
        "Burn in or upload captions; muted viewing is the default.",
    )
