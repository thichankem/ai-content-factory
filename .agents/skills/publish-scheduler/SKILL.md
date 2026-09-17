---
name: publish-scheduler
description: Multi-format cross-platform publishing and syndication skill. Packages master projects into YouTube 16:9 long-form and TikTok/Reels/Shorts 9:16 vertical shorts, with series episode tracking and SEO metadata.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Publish Scheduler Skill — Multi-Format Syndication & Series Management

Publishing historical documentaries requires coordinated scheduling across landscape (16:9 for YouTube) and vertical (9:16 for TikTok/Shorts), along with series episode numbering ("Tập 1/3") and platform-tailored metadata.

## 1. Multi-Format Campaign Generation

```bash
# Generate 1 YouTube Long (8-12m) + 5-10 Vertical Shorts from master project
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/campaign/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "num_shorts": 5,
    "target_duration_long": 600,
    "include_prompts": true
  }'
```

## 2. Platform Packaging Standards

| Platform | Aspect Ratio | Hook Window | SEO / Meta Requirements |
| :--- | :---: | :---: | :--- |
| **YouTube Long** | 16:9 | 15–30s Cold Open | Timestamps / Chapter markers, source bibliography in description |
| **YouTube Shorts** | 9:16 | 2–3s Visual Impact | Loopable ending, #Shorts #History #Documentary |
| **TikTok** | 9:16 | 1–2s Audio Hook | Trending sound cue, 3-5 niche tags (#kienthuc #lichsu #thamhoa) |

## 3. Series Tracking & Publishing

For extended multi-episode investigations (e.g., Chornobyl 3-part series):
```bash
# Final publish with target platform attribution
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["youtube", "tiktok"]
  }'
```
