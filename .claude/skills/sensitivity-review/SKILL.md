---
name: sensitivity-review
description: Ethical sensitivity and platform policy compliance review skill for real-world historical catastrophes and accidents. Guards monetization safety (YouTube advertiser-friendly, TikTok community guidelines) and ensures victim dignity.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Sensitivity Review Skill — Ethical & Monetization Safety Guard

Tragedy and catastrophe documentaries carry significant demonetization risks on YouTube (Yellow Dollar) and reach restrictions on TikTok if they contain graphic violence descriptions, disrespect toward victims, or ungrounded conspiracy theories.

This skill audits narration and visual plans before human Gate 1 (Script Approval) and Gate 2 (Video Approval).

## 1. Direct Audit Endpoint

```bash
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/sensitivity/audit"
```

Response payload includes:
- `safety_score` (0–100): Calculated monetization health index.
- `is_safe_for_monetization`: Boolean flag for platform policy compliance.
- `findings`: Granular violations (`graphic_violence`, `victim_respect`, `unverified_conspiracy`).
- `disclaimer_required`: Whether a viewer warning/memorial tribute must be prepended.
- `recommended_disclaimer`: Pre-formulated solemn text.

## 2. Platform Compliance Rules

### YouTube Advertiser-Friendly Guidelines
- **No Graphic Violence in the First 15 Seconds**: The Cold-Open must rely on tension, sound effects, and radar screens—never graphic descriptions of death.
- **Tone must be educational/documentary**: Sensationalist words (*"kinh hoàng đẫm máu"*, *"xác người la liệt"*) trigger automated content strikes.

### TikTok Community Guidelines
- Avoid disturbing close-ups in thumbnail or video frames.
- Flag suicide or mental health speculations immediately with advisory tags.

## 3. Human Gate Integration

A script cannot be approved if `safety_score < 60` without manual operator override. Ensure any flagged issues are resolved or acknowledged before confirming Gate 1 approval.
