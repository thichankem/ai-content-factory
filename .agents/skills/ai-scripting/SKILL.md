---
name: ai-scripting
description: AI Agent Skill for drafting and polishing viral short-form video scripts with emotional hooks, section cues ([Hook], [Turn], [Payoff], [CTA]), Vietnamese speech pacing estimation, and anti-plagiarism copy-risk protection.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Scripting Skill — Viral Hook & Narrative Engineering

This skill enables AI agents (Anthropic Claude, Google Gemini, OpenAI Codex, DeepSeek) to craft, analyze, and polish viral narration scripts for short-form video pipelines (TikTok, YouTube Shorts, Instagram Reels).

## 1. Structure Contract & Section Cues

A compliant narration script uses bracketed section markers that guide both the AI voiceover engine and video cut timings:

- `[Hook]`: The first 1-3 seconds. An irresistible question, counter-intuitive fact, or high-tension statement.
- `[Context]`: Background ground facts that set up the dilemma or curiosity gap.
- `[Turn]`: The twist, unexpected insight, or turning point.
- `[Payoff]`: The core revelation, practical value, or scientific answer.
- `[CTA]`: Final 2-4 seconds. High-conversion call-to-action (Subscribe, Share, Follow).
- `[Visual]`: Directives for visual scene framing or b-roll overlay.
- `[Sound]`: Sound design cues (e.g. `[Sound: Whoosh + Sub Boom]`).

### Example Script Format
```markdown
[Hook]
Bộ não của bạn đang xóa đi 80% ký ức mỗi ngày mà bạn không hề hay biết!

[Context]
Các nhà khoa học thần kinh tại Stanford vừa phát hiện cơ chế "dọn dẹp synap" xảy ra trong lúc ngủ sâu.

[Turn]
Nhưng đây không phải là lỗi — đây chính là siêu năng lực giúp bạn không bị quá tải thông tin.

[Payoff]
Bằng cách áp dụng quy tắc 3 lần lặp ngắt quãng, bạn có thể biến 20% còn lại thành trí nhớ vĩnh viễn.

[CTA]
Lưu lại video này và thử ngay tối nay!
```

## 2. Timing & Speech Pacing Standards

- **Vietnamese Language (`vi`)**:
  - Target speech rate: ~3.8 to 4.2 syllables/second (~230-250 syllables/minute).
  - Short sentences (<16 syllables per clause) for maximum retention.
- **English Language (`en`)**:
  - Target rate: ~140-160 words per minute.
  - Strong active verbs, minimal passive voice.

## 3. Anti-Plagiarism & Copy-Risk Rule ("Transform, Do Not Copy")

- **Principle**: Learn the facts, structure, and pacing from sources, but never clone verbatim text.
- Before committing a script, verify against the research bundle to ensure copy risk is below 15%.

## 4. API Endpoints

- **Analyze & Lint**: `POST /projects/{id}/script/analyze` with `{"script": "..."}`
- **Save Script**: `PUT /projects/{id}/script` with `{"script": "...", "source_rights_confirmed": false}`
- **Generate Draft**: `POST /projects/{id}/script/generate`
- **Apply Style Preset**: `PUT /projects/{id}/script/style` with `{"style": "viral-short"}`
