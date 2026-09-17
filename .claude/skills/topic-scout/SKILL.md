---
name: topic-scout
description: Automated historical and disaster topic ideation skill. Scans "On This Day" anniversaries, historical catastrophe milestones, and trending search anomalies to curate high-retention evergreen video briefs.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Topic Scout Skill — Historical Anniversaries & Disaster Trends

This skill discovers high-retention, evergreen video topics by scanning historical catastrophe milestones, aviation mysteries, naval disasters, and "On This Day" anniversaries.

## 1. Direct API Endpoints

The AI Content Factory exposes native endpoints for topic scouting:

```bash
# Get notable events for today
curl http://127.0.0.1:8000/history/on-this-day

# Query events for a specific calendar date (e.g. April 14 - Titanic sinking)
curl "http://127.0.0.1:8000/history/on-this-day?month=4&day=14"

# Search catastrophe database by keyword (aviation, titanic, chornobyl, sóng thần)
curl "http://127.0.0.1:8000/history/search?q=aviation"
```

## 2. Topic Scoring & Selection Criteria

When scouting topics for short-form (TikTok) and long-form (YouTube), evaluate against 4 pillars:

1. **Emotional Mystery Hook**: Is there an unanswered question, a fatal chain of mistakes, or a chilling final voice recording? (e.g., MH370, Tenerife, Kursk).
2. **Visual Archival Availability**: Are there authentic public domain photographs, maps, or declassified telegrams? (e.g., Titanic, Hindenburg, San Francisco 1906).
3. **Evergreen & Anniversary Appeal**: Can the video be published on the exact calendar anniversary ("Đúng ngày này năm xưa") for algorithmic boost?
4. **Educational & Safety Lesson**: Does the tragedy result in modern safety standards (e.g., FAA CRM training, SOLAS maritime regulations)?

## 3. Project Creation Workflow

Once a topic is selected:
```bash
curl -X POST http://127.0.0.1:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Thảm họa Titanic 1912",
    "topic": "Vụ chìm tàu Titanic: 6 bức điện tín cảnh báo băng trôi bị bỏ quên trong túi áo",
    "target_language": "vi",
    "duration_target_seconds": 60,
    "script_style": "disaster-retelling"
  }'
```
