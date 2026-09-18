from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ._helpers import (
    _PLACEBO_HASHTAGS,
    _STOPWORDS,
    _fold,
    _mentions,
    _sentences,
    _words,
)
from ._specs import _SPECS
from .contracts import Pack, SeoReport
from .profiles import PLATFORM_PROFILES, PlatformProfile
from .scoring import score_pack


@dataclass(frozen=True)
class OptimizationPlan:
    platform: str
    title: str
    description: str
    hashtags: tuple[str, ...]
    tags: tuple[str, ...]
    hook: str
    comment_prompt: bool
    publish_hours: tuple[int, ...]
    changes: tuple[str, ...]
    before: SeoReport
    after: SeoReport

    @property
    def gain(self) -> int:
        return self.after.score - self.before.score

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "pack": {
                "title": self.title,
                "description": self.description,
                "hashtags": list(self.hashtags),
                "tags": list(self.tags),
                "hook": self.hook,
                "comment_prompt": self.comment_prompt,
            },
            "publish_hours": list(self.publish_hours),
            "changes": list(self.changes),
            "gain": self.gain,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "projected_score": self.after.score,
        }


def _title_case_phrase(phrase: str) -> str:
    words = phrase.split()
    return " ".join(word[:1].upper() + word[1:] if word else word for word in words)


def _build_title(pack: Pack, profile: PlatformProfile) -> tuple[str, list[str]]:
    changes: list[str] = []
    keyword = _title_case_phrase(pack.primary_keyword.strip())
    base = pack.title.strip()
    if not keyword:
        return base, changes
    folded = _fold(base)
    if _fold(keyword) not in folded:
        base = f"{keyword}: {base}" if base else keyword
        changes.append(
            f"Added the search phrase {keyword!r} to the front of the title."
        )
    elif folded.index(_fold(keyword)) > len(base) // 2:
        stripped = re.sub(re.escape(keyword), "", base, flags=re.IGNORECASE).strip(
            " -–—:|"
        )
        base = f"{keyword} — {stripped}" if stripped else keyword
        changes.append("Moved the search phrase to the front of the title.")
    if not re.search(r"[0-9]", base):
        hook_number = _first_number(pack.hook) or _first_number(pack.script)
        if hook_number:
            base = f"{base} ({hook_number})"
            changes.append(f"Added the concrete detail {hook_number!r} to the title.")
    low, high = profile.title_ideal
    lengthened = False
    if low and len(base) < low:
        # A title below the band wastes the strongest search surface, so fill it
        # with the pack's own material instead of telling the user to fix it.
        for detail in _title_details(pack, base):
            if len(base) >= low:
                break
            room = high - len(base) - 3
            if room < 12:
                break
            snippet = detail[:room].rstrip(" ,-–—")
            if len(snippet) < 12:
                continue
            base = f"{base} — {snippet}"
            lengthened = True
    limit = profile.title_hard_max if not low else high
    if len(base) > limit:
        base = base[: limit - 1].rstrip(" -–—:,") + "…"
        changes.append(f"Trimmed the title to {limit} characters.")
    if lengthened:
        changes.append(
            f"Grew the title to {len(base)} characters, inside the "
            f"{low}-{high} band for this platform."
        )
    return base, changes


def _title_details(pack: Pack, base: str) -> list[str]:
    """Real material from the pack that can lengthen a too-short title."""
    details: list[str] = []
    details.extend(text.strip() for text in pack.on_screen_text)
    if pack.hook.strip():
        sentences = _sentences(pack.hook)
        details.append(sentences[0].rstrip(".") if sentences else pack.hook.strip())
    if pack.chapter_count:
        details.append(f"{pack.chapter_count} phần")
    folded_base = _fold(base)
    return [
        detail
        for detail in details
        if detail and _fold(detail) not in folded_base and len(detail) >= 12
    ]


def _first_number(text: str) -> str:
    match = re.search(r"\d[\d.,]*\s?(%|k|tr|triệu|nghìn)?", text or "")
    return match.group(0).strip() if match else ""


def _phrases(language: str) -> dict[str, str]:
    if (language or "").lower().startswith("vi"):
        return {
            "tail": "dành cho người muốn đi thẳng vào việc",
            "question": (
                "Câu hỏi cho bạn: {topic} có đúng với trải nghiệm của bạn không?"
            ),
            "hook": "{topic} — điều ít ai nói tới.",
            "fallback_topic": "Chủ đề này",
        }
    return {
        "tail": "for people who want the short version",
        "question": "Question for you: does {topic} match your experience?",
        "hook": "{topic} — the part nobody mentions.",
        "fallback_topic": "This topic",
    }


def _tag_suffixes(language: str) -> tuple[str, ...]:
    if (language or "").lower().startswith("vi"):
        return ("hướng dẫn", "2026", "giải thích")
    return ("explained", "2026", "tutorial")


def _build_description(pack: Pack, profile: PlatformProfile) -> tuple[str, list[str]]:
    changes: list[str] = []
    words = _phrases(pack.language)
    keyword = pack.primary_keyword.strip()
    hook = pack.hook.strip() or (_sentences(pack.script)[0] if pack.script else "")
    existing = pack.description.strip()
    opening_parts: list[str] = []
    if keyword:
        opening_parts.append(
            f"{_title_case_phrase(keyword)} — "
            f"{hook.rstrip('.') if hook else 'what this video explains'}."
        )
    elif hook:
        opening_parts.append(f"{hook.rstrip('.')}.")
    opening = " ".join(opening_parts)
    if keyword and _mentions(existing[: profile.keyword_zone], keyword) == 0:
        changes.append(
            f"Opened the {'caption' if profile.key == 'tiktok' else 'description'} "
            f"with {keyword!r} inside the first {profile.keyword_zone} characters."
        )
    body = existing if existing else " ".join(_sentences(pack.script)[:3])
    if existing and _mentions(existing, keyword) < 2 and keyword:
        body = f"{body}\n\n{keyword} — {words['tail']}."
        changes.append("Repeated the keyword once, naturally, deeper in the body.")
    if not pack.comment_prompt:
        topic = keyword or "chủ đề này"
        body = f"{body}\n\n{words['question'].format(topic=topic)}"
        changes.append("Added a specific question to pull comments.")
    description = "\n\n".join(part for part in (opening, body) if part.strip()).strip()
    limit = profile.description_ideal_chars[1]
    if len(description) > limit:
        description = description[: limit - 1].rstrip() + "…"
        changes.append(f"Trimmed the text to {limit} characters.")
    return description, changes


def _build_hashtags(
    pack: Pack, profile: PlatformProfile
) -> tuple[tuple[str, ...], list[str]]:
    changes: list[str] = []
    topics: list[str] = []
    for keyword in pack.keywords[:3]:
        words = [word for word in _words(keyword) if word not in _STOPWORDS]
        if words:
            topics.append("".join(words[:3]))
    existing = [
        tag.lstrip("#").strip()
        for tag in pack.hashtags
        if tag.strip() and _fold(tag).strip("#") not in _PLACEBO_HASHTAGS
    ]
    if len(existing) != len([tag for tag in pack.hashtags if tag.strip()]):
        changes.append(
            "Dropped #fyp/#foryou-style hashtags: they carry no ranking value."
        )
    ordered: list[str] = []
    for candidate in [*existing, *topics]:
        if candidate and candidate.lower() not in {tag.lower() for tag in ordered}:
            ordered.append(candidate)
    low, high = profile.hashtag_ideal
    derived: list[str] = []
    if len(ordered) < low:
        sources = [pack.title, *pack.on_screen_text]
        if pack.hook.strip():
            sources.append(pack.hook)
        for source in sources:
            for tag in _topic_variants(source):
                if len(ordered) >= low:
                    break
                if tag.lower() in {item.lower() for item in ordered}:
                    continue
                ordered.append(tag)
                derived.append(tag)
        if derived:
            changes.append(
                "Added "
                + ", ".join(f"#{tag}" for tag in derived)
                + " from the title and on-screen text so the set matches the "
                f"{low}-{high} band."
            )
    if profile.key == "youtube":
        keep = ordered[:high]
    else:
        keep = ordered[: max(high, low)]
    if len(keep) > len(existing) and not derived:
        changes.append(f"Filled the hashtag set out to {len(keep)} topic tags.")
    if len(keep) < low:
        changes.append(
            "Hashtag set is still short of a niche tag — add one that "
            "names the subtopic."
        )
    return tuple(f"#{tag}" for tag in keep), changes


def _topic_tag(text: str, limit: int = 3) -> str:
    """Compress a phrase into one hashtag-shaped token, e.g. 'tàu titanic'."""
    words = [word for word in _words(text) if word not in _STOPWORDS and len(word) > 2]
    return "".join(words[:limit])


def _topic_variants(text: str) -> list[str]:
    """Hashtag candidates for one phrase: broad, mid, and its key noun."""
    words = [word for word in _words(text) if word not in _STOPWORDS and len(word) > 2]
    candidates = [
        "".join(words[:3]),
        "".join(words[:2]),
        max(words, key=len) if words else "",
    ]
    ordered: list[str] = []
    for candidate in candidates:
        if len(candidate) > 3 and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _build_tags(
    pack: Pack, profile: PlatformProfile, extra_topics: Sequence[str] = ()
) -> tuple[tuple[str, ...], list[str]]:
    if profile.tags_ideal == (0, 0):
        return (), []
    changes: list[str] = []
    suffixes = _tag_suffixes(pack.language)
    candidates: list[str] = []
    for keyword in pack.keywords:
        candidates.append(keyword.strip())
        candidates.extend(
            f"{keyword.strip()} {suffix}" for suffix in suffixes if len(keyword) > 3
        )
    for topic in extra_topics:
        candidates.append(topic)
        candidates.extend(f"{topic} {suffix}" for suffix in suffixes)
    candidates.extend(tag.strip() for tag in pack.tags if tag.strip())
    for word in _words(pack.title)[:6]:
        if word not in _STOPWORDS and len(word) > 3:
            candidates.append(word)
    for tag in pack.hashtags:
        candidates.append(tag.lstrip("#").strip())
    for text in pack.on_screen_text:
        candidates.append(text.strip())
        candidates.append(_topic_tag(text))
    if pack.hook.strip():
        candidates.append(_topic_tag(pack.hook, limit=2))
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        key = _fold(candidate)
        if not candidate or key in seen or len(candidate) > 40:
            continue
        seen.add(key)
        ordered.append(candidate)
    low, high = profile.tags_ideal
    keep = ordered[:high]
    if len(keep) > len([tag for tag in pack.tags if tag.strip()]):
        changes.append(
            f"Built a {len(keep)}-tag long-tail set from the target phrases."
        )
    if len(keep) < low:
        changes.append("Tags are thin; add long-tail variants of the main phrase.")
    return tuple(keep), changes


def _rank(report: SeoReport) -> tuple[int, float]:
    """Order two reports by displayed score, then by the un-rounded number."""
    return (report.score, report.precision)


def _publish_hours(pack: Pack, profile: PlatformProfile) -> tuple[int, ...]:
    if pack.audience_hours:
        return tuple(sorted(pack.audience_hours))
    if profile.key == "tiktok":
        return (7, 12, 19, 21)
    return (15, 19, 20)


def optimize_pack(pack: Pack, platform: str) -> OptimizationPlan:
    key = platform.strip().lower()
    profile = PLATFORM_PROFILES.get(key)
    if profile is None:
        raise ValueError(f"Unknown platform {platform!r}; use one of {sorted(_SPECS)}.")
    before = score_pack(pack, key)
    title, title_changes = _build_title(pack, profile)
    description, description_changes = _build_description(pack, profile)
    hashtags, hashtag_changes = _build_hashtags(pack, profile)
    # The rebuilt hashtags are niche phrases in their own right, so the tag set
    # is grown from them rather than from the original pack alone.
    hashtags_clean = tuple(tag.lstrip("#") for tag in hashtags)
    tags, tag_changes = _build_tags(pack, profile, extra_topics=hashtags_clean)
    hook_changes: list[str] = []
    hook = pack.hook.strip()
    if not hook and pack.script.strip():
        sentences = _sentences(pack.script)
        hook = sentences[0] if sentences else ""
    if not hook:
        topic = (
            _title_case_phrase(pack.primary_keyword)
            or _phrases(pack.language)["fallback_topic"]
        )
        hook = _phrases(pack.language)["hook"].format(topic=topic)
        hook_changes.append("Wrote a hook because the pack had none.")

    proposals: list[tuple[dict[str, Any], list[str]]] = [
        ({"title": title}, title_changes),
        ({"description": description}, description_changes),
        ({"hashtags": hashtags}, hashtag_changes),
        ({"tags": tags}, tag_changes),
        ({"hook": hook}, hook_changes),
    ]
    if not pack.comment_prompt:
        proposals.append(
            (
                {"comment_prompt": True},
                ["Set the comment prompt flag the platform signal reads."],
            )
        )

    # Verification loop: a rewrite is kept only when re-scoring the trial pack
    # proves it moved the number. The plan therefore never claims a gain it did
    # not measure, and a second pass catches fields that only pay off together.
    proven = pack
    best = _rank(before)
    accepted: list[str] = []
    for _ in range(2):
        progressed = False
        for values, changes in proposals:
            trial = proven.with_changes(**values)
            measured = _rank(score_pack(trial, key))
            if measured > best:
                proven, best = trial, measured
                accepted.extend(changes)
                progressed = True
        if not progressed:
            break
    after = score_pack(proven, key)
    if _rank(after) < _rank(before):  # pragma: no cover - guard: never regress
        proven, after, accepted = pack, before, []
    return OptimizationPlan(
        platform=profile.key,
        title=proven.title,
        description=proven.description,
        hashtags=proven.hashtags,
        tags=proven.tags,
        hook=proven.hook,
        comment_prompt=proven.comment_prompt,
        publish_hours=_publish_hours(pack, profile),
        changes=tuple(dict.fromkeys(accepted)),
        before=before,
        after=after,
    )
