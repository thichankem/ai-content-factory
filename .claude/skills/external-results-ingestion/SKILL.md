---
name: external-results-ingestion
description: AI Agent Skill for ingesting and binding external AI generations (Kling video, Veo footage, Midjourney photos, ElevenLabs voiceover, Suno music, Perplexity research) directly into the pipeline timeline and scene assets.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# External AI Asset Ingestion Skill — Kling, Veo, Midjourney, Suno, ElevenLabs & Perplexity

This skill guides human operators and autonomous external AI agents in connecting high-fidelity generative assets produced across best-in-class external creative tools into the AI Content Factory timeline and scene graph.

---

## 1. Supported Tool Ecosystem & Asset Mappings

| Creative Tool | Modality | Target Asset Type | Pipeline Binding Destination |
| :--- | :--- | :--- | :--- |
| **Kling AI / Google Veo / Wan 2.1** | Generative AI Video | `scene_video` | `VideoScene.video_url`, `asset_type="ai_reconstruction"` |
| **Midjourney v6 / Flux / DALL-E** | Historical Art & Photos | `scene_image` | `VideoScene.image_url`, `asset_type="historical_photo"` |
| **ElevenLabs / Edge-TTS** | Voiceover Narration | `voiceover_audio` | Project Narration Master Track |
| **Suno AI / Udio** | Cinematic Soundtrack | `bgm_audio` | `VideoProject.background_music_url` |
| **Perplexity Pro / DeepResearch** | Grounded Investigation | `research_dossier` | `Project.research.key_facts` & Grounding Cache |

---

## 2. Ingestion Methods

### A. Online URL Import (Zero-Storage Linking)
Link media hosted on CDN, S3, or tool cloud storage without downloading locally:

```bash
curl -X POST http://localhost:8000/projects/{project_id}/external/import \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "scene_video",
    "source_tool": "Kling AI 1.5 Pro",
    "url": "https://assets.klingai.com/generations/titanic_bow_underwater.mp4",
    "target_scene_id": "scene_3",
    "title": "Scene 3 Underwater Bow Reconstruction"
  }'
```

### B. Direct File Upload (Local Disk Storage)
Upload rendered files directly into the project's local asset directory (`storage/uploads/{project_id}/`):

```bash
curl -X POST http://localhost:8000/projects/{project_id}/external/upload \
  -F "file=@titanic_bgm_cinematic.mp3" \
  -F "asset_type=bgm_audio" \
  -F "source_tool=Suno AI v3.5" \
  -F "title=Epic Orchestral Tragedy Soundtrack"
```

### C. Smart Batch Dropzone Ingestion
Drop an entire production folder of rendered assets into the UI or submit via batch API. Files are automatically classified by regex filename patterns:

- `scene_1.mp4`, `sc2_underwater.webm` ➔ Binds to **Scene 1**, **Scene 2** as `scene_video`.
- `sc1_restored_photo.png` ➔ Binds to **Scene 1** as `scene_image`.
- `voiceover_master.mp3`, `narration.wav` ➔ Binds to **Master Voiceover Track**.
- `bgm_tragic_strings.mp3`, `suno_soundtrack.mp3` ➔ Binds to **Background Music**.

---

## 3. Human Gate & Compliance Safeguards

Per `AGENTS.md` and repository design rules:
1. **Source Rights Are Never Auto-Confirmed**: Ingesting an external image or audio track does *not* bypass Gate 1 or Gate 2. The operator must manually review and confirm intellectual property and historical accuracy before publishing.
2. **Deterministic State Machine**: Even when assets are fully ingested, projects must transition through:
   - `DRAFT` ➔ `SCRIPT_APPROVED` (Gate 1)
   - `SCRIPT_APPROVED` ➔ `VIDEO_REVIEW` (Generation / Ingestion)
   - `VIDEO_REVIEW` ➔ `VIDEO_APPROVED` (Gate 2) ➔ `PUBLISHED`
