---
name: multi-format-campaign
description: AI Agent Skill for orchestrating Multi-Format Content Empires (1 Master Research Topic -> 1 YouTube Long 8-12m + 5-10 Independent TikTok/Shorts 30-60s + 15-Asset Production Package) with zero AI hallucination.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Multi-Format Content Empire Skill — 1 Topic to YouTube + TikTok Matrix

This skill enables external AI agents (Anthropic Claude, OpenAI ChatGPT, Google Gemini, Perplexity) to design and execute a unified multi-format content engine where a single deep research topic automatically branches into:
1. **1 YouTube Long Documentary (8–12 minutes, 16:9, 40–60 scenes)**
2. **5–10 Standalone TikTok / Shorts / Reels (30–60 seconds, 9:16)**
3. **Full 15-Asset Production Package** (Research Dossier, Fact-Check, Prompts for Kling/Veo/Midjourney/Suno/ElevenLabs, SEO Titles, Retention Hooks).

---

## 1. The Anti-Pattern to Avoid: "Don't Slice YouTube into Shorts"

- **Failure Mode**: Taking a 10-minute horizontal video and lazily cutting it into 60-second fragments destroys context, hook retention, and algorithmic engagement.
- **Empire Pattern**: One centralized research topic serves as the root of a divergent tree:
  - **YouTube Master**: Comprehensive, slow-burn 8-step chronological storytelling arc (*Hook -> Context -> Event -> Escalation -> Climax -> Consequence -> Twist -> Ending*).
  - **TikTok Cluster**: 5–10 distinct, self-contained videos each attacking a high-curiosity angle (Missed Warnings, 37s Collision Point, Lifeboat Scandals, 3 Fatal Human Errors, Final 2h40m Letters).

---

## 2. The 8-Step Dramatic Documentary Framework (YouTube Master)

When drafting long-form historical or disaster content (e.g., Titanic, Kursk, Chornobyl):

1. **[00:00 - 01:15] Hook & Curiosity Gap**: Unveil a shocking anomaly or hidden fact that overturns public assumptions.
2. **[01:15 - 03:00] Historical Context & Pride**: Introduce the human ambition, engineering majesty, or false sense of invulnerability.
3. **[03:00 - 04:30] The Fatal Spark (Point of No Return)**: The initial trigger event, unnoticed error, or fateful decision.
4. **[04:30 - 06:45] Rapid Escalation**: Relentless compounding crises, ignored telegrams, broken communications, rising panic.
5. **[06:45 - 08:30] Catastrophic Climax**: The moments of maximum destruction and extreme survival choices.
6. **[08:30 - 09:30] Grim Consequences**: Silence, aftermath, human cost, global shockwaves.
7. **[09:30 - 10:45] The Declassified Twist**: Archival secrets, cover-ups, or withheld telegrams revealed decades later.
8. **[10:45 - 12:00] Legacy & Memorial**: Lasting safety regulations, philosophical takeaway, reverent memorial.

---

## 3. The 5-Phase TikTok Hook Architecture (30–60s)

Every vertical short MUST follow the strict retention countdown:
- **0–3s (Visual + Auditory Hook)**: "Có một bức điện tín được gửi trước khi thảm họa xảy ra 2 giờ, nhưng chưa bao giờ được mở ra!"
- **3–10s (Rapid Context)**: Ground facts delivered in under 20 words.
- **10–35s (High-Tension AI Footage & Archival B-Roll)**: Rapid cut pacing (1.5–2.5s per shot) showing the drama unfold.
- **35–50s (The Shocking Revelation)**: Deliver the single hardest-hitting truth.
- **50–60s (Conversational CTA)**: "Bạn nghĩ đây là do sơ suất hay số mệnh? Bình luận bên dưới và xem full hồ sơ trên YouTube ở bio!"

---

## 4. REST API Integration

Trigger the automated campaign generator for any project:
```bash
# Generate full campaign (1 YouTube + 5 Shorts)
curl -X POST http://localhost:8000/projects/{project_id}/campaign/generate \
  -H "Content-Type: application/json" \
  -d '{"shorts_count": 5, "youtube_target_minutes": 10}'

# Fetch full 15-asset package
curl http://localhost:8000/projects/{project_id}/campaign/export-pack
```
