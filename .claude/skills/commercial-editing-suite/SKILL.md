---
name: commercial-editing-suite
description: Comprehensive commercial video editing skill synthesizing the full power of Adobe Premiere Pro, DaVinci Resolve Studio, Apple Final Cut Pro, CapCut Pro, and Descript into an autonomous AI-driven pipeline.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Commercial Video Editing Suite — Unified Industry Master Guide

This skill equips AI agents to orchestrate video editing at the level of top-tier commercial paid software suites:
- **Adobe Premiere Pro & After Effects**: Multi-track non-linear timeline, keyframe spatial transforms, cubic-bezier easing, Lumetri color grading LUTs.
- **DaVinci Resolve Studio (Fairlight & Fusion)**: Node-based graphics (procedural SVG route maps & comparison infographics), precise audio synthesis, color spaces (Teal-Orange, Noir, Vintage, Cyberpunk).
- **CapCut Pro**: High-retention vertical 9:16 formatting, kinetic typography presets (Neon Cyber Glow, Outline, Caption Chip), instant viral sound effect pads, speed-ramping.
- **Descript**: Script-driven video editing where modifying narrative blocks automatically retimes and reconstructs timeline scenes.

---

## 1. Feature Mapping: Commercial Software vs. AI Content Factory

| Commercial Tool | Flagship Feature | Content Factory Architecture | API / Service Mapping |
| :--- | :--- | :--- | :--- |
| **Premiere Pro** | Multi-track Timeline & Split/Merge | `src/content_factory/timeline.py` | `POST /projects/{id}/timeline/scenes/{scene_id}/split` |
| **After Effects** | Kinetic Keyframes & Motion Curves | `Keyframe` & `SceneMotion` models | Scale, rotation, opacity, cubic bezier easing |
| **DaVinci Resolve** | Fusion Node Graphics (Route Maps) | `map_generator.py` | `POST /projects/{id}/graphics/map` |
| **DaVinci Resolve** | Lumetri / Color Grading LUTs | Canvas 2D WebGL Shaders | `teal-orange`, `noir`, `vintage`, `cyberpunk` |
| **Fairlight DAW** | Sound Design & Period Audio | Web Audio Synthesizer | `sos` (Morse), `siren`, `sonar`, `static`, `whistle` |
| **CapCut Pro** | Kinetic Subtitles & Captions | `VideoScene` text render engine | `neon`, `outline`, `caption`, `shadow` |
| **CapCut Pro** | Aspect Ratio & Safe-Zone Overlay | `ed.aspect`, `tiktok-safe-zone` | `9:16`, `16:9`, `1:1`, `4:5` |
| **Descript** | Script-First Editing & Linter | `script_engine.py` | `POST /projects/{id}/script`, `analyze_script` |
| **Descript** | Multi-Source Fact Check & Safety | `sensitivity.py`, `research.py` | `POST /projects/{id}/sensitivity/audit` |

---

## 2. API Quick Reference for Autonomous Agents

### A. Timeline Structure Editing (Premiere / Final Cut Pro)
```bash
# Split scene at midpoint
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/timeline/scenes/{scene_id}/split" \
  -H "Content-Type: application/json" -d '{"at": 0.5}'

# Duplicate scene
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/timeline/scenes/{scene_id}/duplicate"

# Move scene order on timeline
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/timeline/scenes/{scene_id}/move" \
  -H "Content-Type: application/json" -d '{"to_index": 2}'

# Merge adjacent scenes
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/timeline/scenes/{scene_id}/merge"
```

### B. Procedural Graphics (DaVinci Fusion Engine)
```bash
# Generate vector navigational route map
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/graphics/map" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Chuyến bay định mệnh MH370",
    "map_type": "aviation",
    "points": [
      {"label": "Kuala Lumpur", "x": 15.0, "y": 70.0, "timestamp": "00:41"},
      {"label": "IGARI (Mất radar)", "x": 42.0, "y": 45.0, "timestamp": "01:21"},
      {"label": "Cú bẻ lái Eo biển Malacca", "x": 30.0, "y": 55.0, "timestamp": "01:52"},
      {"label": "Vòng cung số 7 (Ấn Độ Dương)", "x": 80.0, "y": 85.0, "timestamp": "08:19"}
    ],
    "show_danger_zone": true,
    "danger_label": "Khu vực tìm kiếm Vòng cung số 7",
    "danger_x": 80.0,
    "danger_y": 85.0
  }'

# Generate comparison infographic
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/graphics/infographic" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Thang độ chấn động địa chấn lịch sử",
    "subtitle": "Độ lớn Richter (Mw)",
    "chart_type": "bar",
    "labels": ["San Francisco 1906", "Kanto 1923", "Chili 1960", "Sumatra 2004", "Tohoku 2011"],
    "values": [7.9, 7.9, 9.5, 9.1, 9.1],
    "unit": "Richter"
  }'
```

### C. Multi-Source Fact Check & Sensitivity Guard
```bash
# Reconcile facts against >=2 sources
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/facts/reconcile"

# Audit ethical tone & monetization safety (0-100 score)
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/sensitivity/audit"
```

---

## 3. Benchmarking & Quality Assurance

Run the automated commercial editing suite benchmark at any time:
```bash
python scripts/benchmark_editing_suite.py
```
This tests operation latency, FPS throughput, and API compliance across all commercial features.
