# QA & Traceability Layer — the "critic" before publish

A separate review layer that checks a video **before** it is allowed to
publish, modelled after the "critic" in coding agents: the agent that *creates*
content never also *approves* it. This layer is deterministic, rule-based, and
runs offline — no model, no cost.

Implemented in `src/content_factory/compliance.py`, `audit.py`, `cost_guard.py`.

## The four checks

| Concern | Module / function | What it catches |
| ------- | ----------------- | --------------- |
| Platform compliance | `compliance.check_platform(meta, platform)` | Too long/short, wrong aspect ratio, forbidden phrases, word-count overrun — per platform (YouTube, TikTok, IG Reels, Facebook, Shorts). |
| Brand consistency | `compliance.check_brand(meta, kit)` | Off-palette colours, missing logo, off-brand fonts vs a `BrandKit`. |
| Copyright / rights | `compliance.check_copyright(fp, protected)` + `fingerprint_music_audio(path)` | Exact fingerprint match against a protected set before publish. |
| Provenance / audit | `audit.AuditLog` | Append-only trail of every AI edit: which model, what prompt, when. |
| Cost guard | `cost_guard.CostGuard` | Estimates USD cost of an expensive plan (vision/audio-LLM/TTS/STT) and demands confirmation over a threshold. |

## Usage sketch

```python
from content_factory.compliance import (
    ComplianceMeta, BrandKit, BrandMeta, check_platform, check_brand,
)
from content_factory.audit import AuditLog
from content_factory.cost_guard import CostGuard, PlanBudget

issues = check_platform(
    ComplianceMeta(duration_seconds=120, aspect_ratio="9:16", words=800, text=script),
    "tiktok",
)
brand = check_brand(
    BrandMeta(dominant_colors=("#1a1d27",), fonts_used=("Inter",), has_logo=True),
    BrandKit(palette=("#1a1d27",), fonts=("Inter",), logo_fingerprints=("logo-a",)),
)

audit = AuditLog("./storage/audit")
audit.record("claude", "edit.scene.speed", project_id="abc", detail="intro 1.5x")

guard = CostGuard(PlanBudget(enabled=True, threshold_usd=5.0))
estimate, needs_confirm = guard.check({"vision": 600, "audio_llm": 20})
```

## Why this is separate from editing

The two human gates (script + final video) remain mandatory and are enforced
upstream in the service layer. This QA layer is an *automated early warning* —
it flags likely problems so a human (or the operator) can reject before wasting
a render, and it records *why* an AI made a change so questions like "why did
this scene change?" are answerable.

## Configuration

```ini
CONTENT_FACTORY_AUDIT_DIR=./storage/audit
CONTENT_FACTORY_COST_GUARD_ENABLED=false
CONTENT_FACTORY_COST_GUARD_THRESHOLD_USD=5.0
CONTENT_FACTORY_COST_UNIT_VISION_USD=0.010
CONTENT_FACTORY_COST_UNIT_AUDIO_LLM_USD=0.020
CONTENT_FACTORY_COST_UNIT_TTS_USD=0.002
CONTENT_FACTORY_COST_UNIT_STT_USD=0.003
CONTENT_FACTORY_COST_UNIT_EMBEDDING_USD=0.0001
```

## Guardrail

Nothing here auto-confirms source rights or auto-publishes. The copyright check
flags a match; the human still decides. The audit trail is append-only so it can
serve as evidence (C2PA-style provenance) without being tampered with.