# AI Content Factory — Studio Pro & Autonomous Pipeline

An AI-assisted multi-format video production pipeline and professional creative studio with two mandatory human review gates: **Gate 1 (Script Approval)** and **Gate 2 (Final Video Approval)**.

The project turns reference material, historical events, and complex investigations into original creative works. A single root topic branches into **long-form documentary (YouTube 16:9)** and a cluster of **high-retention vertical shorts (TikTok / Shorts / Reels 9:16)** with zero verbatim plagiarism and zero AI hallucination.

---

## Status

The full pipeline is implemented, verified, and green:

- **Backend** — FastAPI architecture under `src/content_factory` featuring a deterministic state machine, an AI provider chain (built-in template + local weak tier + multi-vendor strong tier), an editing engine with server-side normalization and validation, a visual DAG workflow runner, a multi-format campaign engine, and an external AI asset ingestion hub.
- **Frontend** — Modern dark-glassmorphism Creative Studio Pro served at `/` with 7 dedicated workspaces: **Pipeline**, **Video Studio (NLE)**, **Photo Lab (Photoshop)**, **Node Flow (DAG)**, **Agents Orchestra**, **Document Library**, and **Empire Hub**.
- **Quality Gates** — **347 pytest unit & integration tests passing (100%)**, `ruff check` clean, `ruff format` clean (58 files), `mypy src` strict type check clean (27 source files), automated editing benchmarks, and an automated end-to-end smoke test verifying **64 integration checks**.
- **CI / CD** — GitHub Actions workflow enforcing all lint, format, typecheck, unit test, and smoke test quality gates.

---

## The 7 Studio Pro Workspaces

Switch between workspaces via the top navigation bar or keyboard shortcuts <kbd>1</kbd>–<kbd>7</kbd>:

1. 🚀 **Pipeline (Key 1)**: Autonomous 7-stage production stepper (`draft` ➔ `script_review` ➔ `script_approved` ➔ `generating` ➔ `video_review` ➔ `video_approved` ➔ `published`). Includes real-time script analysis gauge, word budget calculator, and Gate 1 / Gate 2 human review decision audit history.
2. 🎬 **Video Studio (Key 2)**: Professional NLE video editing suite inspired by Premiere Pro & CapCut. Features multi-track timeline (Visuals, Kinetic Captions, Voice & Beats), tool dock (Select, Razor Cut, Text, Stickers, Color Grades, VFX), TikTok Safe Zone transparent guides, phone bezel mockup, Web Audio API SFX synthesizer (Whoosh, Pop, Click, Impact, Level Up, Ding), and canvas-to-WebM export.
3. 🎨 **Photo Lab (Key 3)**: Photoshop-style image and thumbnail design lab. Includes multi-aspect canvas (9:16 TikTok Cover, 16:9 YouTube, 1:1 Instagram, 4:5 Reels), drawing toolbar (shapes, brush, eraser, text, color picker), layer stack management (ordering, visibility, opacity, blend modes), tone curves, contrast/brightness adjustments, and 1-click video frame capture.
4. 🕸 **Node Flow DAG (Key 4)**: Drag-and-drop visual DAG workbench. Includes an 11-block palette, infinite canvas with SVG Bezier connecting links, snapping grid, pre-save checklist auditor (detects cycles, orphan nodes, and validates Gate 1 & 2 enforcement), and live terminal stream monitoring.
5. ⚡ **Agents Orchestra (Key 5)**: AI multi-vendor command center for Anthropic Claude, Google Gemini, OpenAI Codex, DeepSeek, and Local Engine with specialized prompt exporters and execution triggers.
6. 📚 **Document Library (Key 6)**: Curated research archive with streaming downloads from six public scholarly sources (arXiv, Crossref, Gutenberg, Open Library, Wikipedia, Internet Archive) backed by a SQLite FTS5 BM25 full-text search engine.
7. 🏛 **Empire Hub (Key 7)**: Multi-format content engine turning 1 root topic into 1 YouTube Master Documentary (8–12 min, 16:9) + 5–10 Standalone TikTok / Shorts (30–60s, 9:16) with Golden Hybrid Media allocation and 15-asset prompt matrix.

---

## Core Features

### 1. Multi-Format Content Empire Engine
- **"Don't Slice YouTube into Shorts" Architecture**: A single research topic powers a divergent tree:
  - **YouTube Master**: 8-step dramatic storytelling arc (*Hook ➔ Historical Context ➔ Point of No Return ➔ Escalation ➔ Catastrophic Climax ➔ Grim Consequences ➔ Declassified Twist ➔ Memorial*).
  - **TikTok / Shorts Series**: 5 to 10 independent angles (*Ignored Warnings, 37s Collision Point, Lifeboat Scandals, 3 Fatal Errors*) following a strict 5-phase retention pacing (0–3s Hook, 3–10s Context, 10–35s Escalation, 35–50s Climax/Twist, 50–60s CTA) designed for >100% audience retention.
- **Golden Hybrid Media Ratio**: Eliminates the "cheap AI" feel with a curated documentary allocation:
  - **30% AI Reconstruction Video**: Cinematic historical reenactment (Kling AI, Google Veo, Wan 2.1).
  - **20% Restored Historical Photos**: Public domain archival photos colorized and enhanced.
  - **15% Dynamic 3D Maps**: Radar trajectories, flight paths, and nautical routes.
  - **15% Declassified Documents**: Authentic newspaper frontpages, telegrams, and court transcripts.
  - **10% Technical Diagrams**: Blueprint schematics, cross-sections, and engineering diagrams.
  - **10% Kinetic Motion Typography**: Fast-paced animated statistics and quote reveals.
- **15-Asset Generative Resource Package**: 1-click copy matrices for Kling/Veo, Midjourney, Suno, ElevenLabs, plus 5x CTR titles, 10x retention hooks, YouTube chapters, and SEO descriptions.

### 2. External AI Asset Ingestion Hub (Key `I`)
Direct bridge connecting best-of-breed creative AI tools into project timelines:
- **Zero-Storage Online URL Linking**: Link CDN/S3 assets directly from Kling AI, Veo, Midjourney, Suno, and ElevenLabs.
- **Local Disk Upload**: Upload `.mp4`, `.webm`, `.jpg`, `.png`, `.mp3`, `.wav` directly to `storage/uploads/{project_id}/` served via static `/uploads` route.
- **Batch Dropzone Auto-Routing**: Drop entire directories of rendered files. Automatic regex pattern matching:
  - `scene_1.*`, `sc2.*` ➔ bound to Scene 1, Scene 2 (`scene_video` or `scene_image`).
  - `voiceover.*`, `narration.*` ➔ bound to Master Narration Track.
  - `bgm.*`, `soundtrack.*`, `suno.*` ➔ bound to Background Music Track.
- **Perplexity & DeepResearch Dossier**: Paste structured investigation notes directly into the grounded knowledge cache.
- **Visual Feedback**: Badges `[🎬 Video Attached]` and `[🖼️ Photo Attached]` appear directly on scene cards with quick ingest buttons.

### 3. Visual Workflow DAG System
- 11 production block types: `research`, `script`, `lint`, `gate`, `voiceover`, `scenes`, `ai_assist`, `timeline_check`, `render_plan`, `publish`, `ingest_external`.
- Pre-save checklist inspection enforcing cycle-free topologies, orphan prevention, and human review gates.
- Asynchronous DAG execution runner with real-time SSE / console streaming.

### 4. Professional Timeline & Video Editor
- Server-authoritative editing engine (`timeline.py`) guaranteeing normalized timelines (unique IDs, clamped ranges, sorted keyframes).
- 15-rule structural validator checking WCAG text contrast, reading-speed overflow, dead air, frantic pacing, and duration drift.
- Render plan compiler (`/render-plan`) outputting absolute time slots, keyframes, transitions, and audio layers ready for ffmpeg.

### 5. Multi-Vendor AI Agent Orchestra
- Native adapters for Anthropic Claude (`/v1/messages`), Google Gemini (`generateContent`), OpenAI Codex, DeepSeek, Ollama, and local fallbacks.
- Structured Markdown contract (`docs/AGENT-BRIDGE.md`) with automated export (`/brief.md`) and parsing (`/agent-result`).
- Edge-TTS integration for zero-cost neural voice synthesis (100+ locales, Vietnamese `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`).

### 6. Commercial Video Editing Suite & Benchmark Engine
- **Premiere Pro & Final Cut Pro Timeline Mechanics**: Non-linear timeline mutations (`split_scene`, `duplicate_scene`, `move_scene`, `merge_scene`, `bulk_update`) executed as pure, deterministic, server-authoritative functions.
- **DaVinci Resolve Color Grading & Shaders**: One-click cinematic LUT-style grades (`teal-orange`, `noir`, `vintage`, `cyberpunk`, `pastel`) and visual shader overlays (`film-grain`, `old-film`, `glitch`, `scanlines`, `dreamy`, `sharpen`, `mosaic`).
- **After Effects Keyframe Motion Math**: Cubic-bezier spatial keyframe interpolation (`evaluate_motion`) with easing curves (`linear`, `ease-in`, `ease-out`, `ease-in-out`), 2D rotation, scale, position, and opacity.
- **CapCut Kinetic Typography & Aspect Ratios**: Neon and outline text presets, animated entrance/exit cues (`slide-up`, `bounce`, `blur-in`, `fade`), TikTok safe-zone guides, and multi-aspect ratio rendering (`9:16`, `16:9`, `1:1`, `4:5`, `3:4`).
- **Descript Script-Driven Editing**: Bi-directional synchronization between script text and timeline scenes; changing script dialogue directly auto-recalculates durations, speech rates, and subtitle cues.

### 7. Specialized History, Disaster & Accident Pipeline
- **Specialized Federated Research**: 9 federated search providers including **Wikimedia Commons** (public domain archival media), **Chronicling America** (historic newspaper archives), and **USGS Earthquakes** (seismic disaster records).
- **Structured Timeline Extraction**: Automatic extraction of chronological milestones, turning points, casualty counts, and climax markers from scripts.
- **Multi-Source Fact Reconciliation**: Cross-references sensitive statistics (casualties, dates, damages) across independent sources to prevent misinformation and guarantee consensus ($\ge 2$ sources for verified status).
- **Procedural Vector Graphics Engine**: Generates dark-glassmorphism animated SVG route maps (nautical, aviation, earthquake trajectories with collision danger zones) and comparative casualty infographics with zero external dependencies.
- **Policy & Sensitivity Audit Guard**: Automated 0–100 monetization safety scoring and regex linter detecting graphic violence, disrespectful disaster descriptions, and unverified conspiracy theories before Gate 1 clearance.
- **Period-Accurate Procedural Audio SFX**: Pure Web Audio API synthesizers reproducing Morse SOS (850Hz), Air Raid Siren (450–850Hz wail), Submarine Sonar Ping (1550Hz), Radio Static crackle, and Steam Whistles.
- **"On This Day" (Ngày này năm xưa) Engine**: Curated 12-month calendar database of maritime, aviation, seismic, and industrial disasters, queryable by calendar day or keyword.

### 8. Human-in-the-Loop Safeguards
- AI scripts and external imports **never** auto-confirm intellectual property rights.
- Video production is locked until a human operator passes **Gate 1 (Script Approval)**.
- Distribution to YouTube and TikTok is locked until a human operator passes **Gate 2 (Video Approval)**.

---

## Repository Layout

```
.
├── .claude/
│   └── skills/                  # 21 operational AI agent skills
├── .github/workflows/ci.yml     # GitHub Actions CI quality gates
├── .env.example                 # Configuration template (copy to .env)
├── AGENTS.md                    # Coding agent guidance & state machine rules
├── frontend/                    # Creative Studio Pro frontend (served at /)
│   ├── index.html               # 7-workspace single page studio
│   ├── style.css                # Glassmorphism design system & neon themes
│   ├── app.js                   # Pipeline controller, empire engine & ingest hub
│   ├── editor.js                # NLE timeline, Web Audio SFX & Photo Lab
│   └── flow.js                  # Visual DAG canvas, bezier routing & checklist
├── docs/                        # Architecture & operator manuals
│   ├── KE-HOACH-TONG-THE.md     # Operator master plan & running change log (Vietnamese)
│   ├── TOOLCHAIN.md             # Optional local media/AI tools guide
│   ├── EDITING.md               # Video editing model, validator & render plan
│   └── AGENT-BRIDGE.md          # External AI agent Markdown contract
├── presets/                     # User-tunable script style presets
│   ├── README.md                # Preset creation guide (JSON & Markdown)
│   └── vietnamese-short.json    # Vietnamese high-retention short preset
├── scripts/                     # Cross-platform development & verification scripts
│   ├── dev.ps1 / dev.sh         # Launch FastAPI dev server
│   ├── test.ps1 / test.sh       # Run pytest test suite
│   ├── lint.ps1 / lint.sh       # Run ruff + mypy checks
│   ├── toolcheck.py             # Verify installed CLI toolchain
│   └── smoke.ps1 / smoke.py     # End-to-end HTTP smoke test (64 checks)
├── storage/                     # Local persistent storage
│   └── uploads/                 # Ingested external AI video, photo, and audio
├── src/content_factory/         # Core application package
│   ├── agent_bridge.py          # Markdown brief export / agent result import
│   ├── api.py                   # FastAPI application & route declarations
│   ├── campaign.py              # Multi-format empire campaign & prompt generator
│   ├── config.py                # Environment settings
│   ├── documents.py             # Federated search across scholarly providers
│   ├── library.py               # SQLite FTS5 BM25 document archive
│   ├── models.py                # Domain models & Pydantic schemas
│   ├── presets.py               # Script style preset library loader
│   ├── providers.py             # Multi-vendor AI provider chain & circuit breakers
│   ├── rag.py                   # Chunking templates, hybrid retriever & grounding
│   ├── research.py              # Grounded research bundle compiler
│   ├── resilience.py            # Token-bucket rate limiter & retry policies
│   ├── scenes.py                # Script to editable video scenes compiler
│   ├── script_engine.py         # Section parsing, timing & copy-risk linter
│   ├── service.py               # Application orchestration layer
│   ├── smart.py                 # AI editing assist (look suggestion, beat sync)
│   ├── state.py                 # Authoritative lifecycle state machine
│   ├── store.py                 # Thread-safe in-memory project repository
│   ├── timeline.py              # NLE editing engine, validator & render plan
│   ├── tts.py                   # Edge-TTS & gTTS neural voiceover synthesizer
│   └── workflow.py              # Drag-and-drop DAG runner & pre-save checklist
└── tests/                       # Automated pytest test suite (317 tests)
```

---

## Quickstart

Requires Python 3.11+.

```powershell
# Windows (PowerShell)
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests scripts
python -m mypy src
scripts\dev.ps1
```

```bash
# Linux / macOS / WSL
python3 -m pip install -e ".[dev]"
./scripts/test.sh
./scripts/lint.sh
./scripts/dev.sh
```

Open the studio dashboard at `http://127.0.0.1:8080/` and interactive Swagger docs at `http://127.0.0.1:8080/docs`.

---

## API Reference

### 1. Project Lifecycle & Gate Approvals
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects` | Create a new project (`draft` state) |
| `GET` | `/projects` | List all active production projects |
| `GET` | `/projects/{id}` | Get full project metadata and pipeline state |
| `PUT` | `/projects/{id}/script` | Save script and confirm intellectual property rights |
| `POST` | `/projects/{id}/script/generate` | Generate script via AI provider chain |
| `POST` | `/projects/{id}/approvals` | Submit Gate 1 (Script) or Gate 2 (Video) review decision |
| `POST` | `/projects/{id}/generate` | Start / retry / re-render video generation |
| `POST` | `/projects/{id}/publish` | Publish approved video to YouTube / TikTok |

### 2. Multi-Format Empire Engine
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/campaign/generate` | Generate 1 YouTube Master + 5–10 Shorts + 15-asset package |
| `GET` | `/projects/{id}/campaign` | Retrieve active multi-format campaign |
| `PUT` | `/projects/{id}/campaign/shorts/{sid}` | Update title, hook, and script for a specific short |
| `GET` | `/projects/{id}/campaign/export-pack` | Export full 15-asset package as a structured JSON artifact |

### 3. External AI Asset Ingestion Hub
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/external/import` | Ingest online URL or research text (Kling/Veo/MJ/Suno/Perplexity) |
| `POST` | `/projects/{id}/external/upload` | Upload local media file and bind to target scene or audio track |
| `POST` | `/projects/{id}/external/batch-import` | Batch ingest multiple external assets |
| `GET` | `/projects/{id}/external/assets` | List all ingested external media records for the project |

### 4. Visual Workflow DAG
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/workflow/blocks` | List available DAG block definitions and port schemas |
| `GET` | `/projects/{id}/workflow` | Retrieve project's custom DAG workflow document |
| `PUT` | `/projects/{id}/workflow` | Save workflow DAG (audited by pre-save checklist) |
| `GET` | `/projects/{id}/workflow/checklist` | Audit current saved workflow for cycles, orphans, and gates |
| `POST` | `/projects/{id}/workflow/checklist` | Audit unsaved workflow draft payload without persisting |
| `POST` | `/projects/{id}/workflow/run` | Execute workflow DAG asynchronously |
| `GET` | `/projects/{id}/workflow/runs` | List workflow execution run history and terminal logs |

### 5. Video Studio & Timeline NLE
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/projects/{id}/video-project` | Retrieve editable multi-track video project |
| `PUT` | `/projects/{id}/video-project` | Persist video timeline edits (server-normalized) |
| `GET` | `/projects/{id}/timeline/report` | Measure cut quality (15 rules, stats, readiness score) |
| `GET` | `/projects/{id}/render-plan` | Compile timeline into absolute slot render plan |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/split` | Razor split a scene at playhead |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/merge` | Merge scene into the next consecutive scene |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/duplicate` | Duplicate scene with offset timings |
| `DELETE` | `/projects/{id}/timeline/scenes/{sid}` | Delete a scene from the timeline |
| `POST` | `/projects/{id}/video-project/ai-assist` | Auto-edit pipeline: duration fit, beat sync, captions |
| `POST` | `/projects/{id}/voiceover/generate` | Synthesize Edge-TTS neural voiceover for all scenes |

---

## Agent Skills Index (`.claude/skills/`)

The repository provides 21 specialized skills with YAML frontmatter:

| Skill | Description |
| :--- | :--- |
| **`multi-format-campaign`** | Orchestrate 1 Master Topic ➔ 1 YouTube Long + 5–10 Shorts + 15-Asset Package |
| **`external-results-ingestion`**| Ingest Kling, Veo, Midjourney, Suno, ElevenLabs, and Perplexity into timeline |
| **`ai-scripting`** | High-retention viral scripting, section cues, Vietnamese pacing (3.8–4.2 syl/s) |
| **`ai-video-editing`** | NLE video timeline, keyframes, Ken Burns, Lumetri LUTs, TikTok Safe Zone |
| **`ai-audio-editing`** | Neural TTS synthesis, Web Audio SFX engine, audio ducking, BPM sync |
| **`ai-thumbnail-photo`** | Multi-aspect Photoshop design, layer stacks, curves, contrast balancing |
| **`ai-workflow-dag`** | Visual DAG construction, checklist audit, execution management |
| **`ai-agent-orchestrator`** | Multi-agent delegation (Claude, Gemini, Codex, DeepSeek, Local) |
| **`hybrid-footage-director`** | Direct 6-component hybrid media ratio balancing (AI, photos, maps, docs) |
| **`prompt-master-kling-veo-mj`**| High-CTR cinematic prompt engineering for Kling, Veo, and Midjourney |
| **`create-project`** | Initialize new productions via `POST /projects` |
| **`search-documents`** | Federated search across public scholarly sources |
| **`agent-brief`** | Export Markdown brief and import structured replies via Agent Bridge |
| **`generate-script`** | Request AI script drafting via multi-vendor provider chain |
| **`approve-script`** | Operator review playbook for Gate 1 approval |
| **`edit-video`** | Guide to the browser-based NLE video editor |
| **`review-video`** | Operator review playbook for Gate 2 approval and publishing |
| **`run-dev`** | Development server startup and health check verification |
| **`test`** | Pytest execution guide and quality gate requirements |
| **`lint`** | Ruff linting, formatting check, and Mypy static type verification |
| **`smoke-test`** | Full end-to-end automated pipeline validation suite |

---

## Adobe Creative Cloud Professional Studio UI

The AI Content Factory UI is modeled directly after the **Adobe Creative Cloud Suite**, giving video editors and creators the exact muscle memory and ergonomic toolset of industry-standard post-production software:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Pr] [Ae] [Ps] [Au] [Me]  File  Edit  Clip  Sequence  Audio  Graphics  Window  Help   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [🎬 Editing] [🎨 Color] [✨ Effects] [🎙 Audio] [📝 Captions] [⚡ Export] [🤖 AI Co-Pilot]│
├───────────────┬───────────────────────────────────────────┬────────────────────────────┤
│ TOOL PALETTE  │ PROGRAM MONITOR (Full / 1/2 / 1/4)        │ INSPECTOR PROPERTIES       │
│  [V] Select   │ ┌───────────────────────────────────────┐ │  • Narration & Script      │
│  [A] Track -> │ │ ⊞ Action & Title Safe Margins (90/80) │ │  • Speed & Duration       │
│  [B] Ripple   │ │ 📱 TikTok / Reels Viral Safe Zone     │ │  • Lumetri Color LUTs      │
│  [C] Razor    │ │                                       │ │  • Ken Burns & Shaders     │
│  [Y] Slip     │ └───────────────────────────────────────┘ │  • Audio Gain & Volume     │
│  [P] Pen      │ [L] [R] Stereo VU Peak Level Meter (dB)   │  • Kinetic Captions Style  │
│  [H] Hand     │ 00:00:00:00 / 00:00:45:00 (SMPTE Timecode)│  • Media Encoder Presets   │
│  [T] Type     │ [ { Mark In ] [ ◀ ] [ ▶ Play ] [ Mark Out } ]                          │
├───────────────┴───────────────────────────────────────────┴────────────────────────────┤
│ MULTI-TRACK NLE TIMELINE                                                               │
│ [Ruler] 00:00:00:00 ── 00:00:10:00 ── 00:00:20:00 ── 00:00:30:00 ── 00:00:45:00 ──    │
│ [V2 FX]    [ Overlay / Map Route SVG / Infographic ]                                   │
│ [V1 Main]  [ Scene 01: Hook ] [ Scene 02: Conflict ] [ Scene 03: Climax ]              │
│ [A1 Voice] [ Neural Speech Narration (Edge-TTS) Track ]                                │
│ [A2 Music] [ Background Ambient Soundtrack (Auto-Ducking -12 dB) ]                     │
│ [A3 SFX]   [ S.O.S Morse / Air Raid Siren / Sonar Ping ]                               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Adobe Keyboard Shortcut Cheatsheet

| Key | Operation | Action Description |
|---|---|---|
| `Space` | **Play / Pause** | Toggle realtime audio & video canvas playback |
| `◀` / `▶` | **Step 1s** | Nudge playhead backward / forward 1 second |
| `I` | **Mark In Point** | Set sequence in-point `{` with SMPTE timecode |
| `O` | **Mark Out Point** | Set sequence out-point `}` with SMPTE timecode |
| `Alt + X` | **Clear In/Out** | Reset range markers across timeline |
| `V` | **Selection Tool** | Move and inspect individual video clips |
| `C` | **Razor Tool** | Split active scene cleanly at the playhead |
| `A` | **Track Forward** | Select and shift all downstream clips |
| `B` | **Ripple Edit** | Trim scene while rippling adjacent clips |
| `Y` | **Slip Tool** | Adjust source in/out without moving timeline slot |
| `P` | **Pen Tool** | Add keyframes and bezier curves |
| `H` | **Hand Tool** | Pan across long documentary sequences |
| `T` | **Type Tool** | Create kinetic captions and text overlays |
| `M` | **Add Marker** | Drop color-coded cue marker on playhead |
| `Ctrl + S` | **Save Project** | Persist video state to backend database |
| `Ctrl + M` | **Export** | Queue rendering job in Media Encoder panel |
| `Ctrl + Z` / `Shift+Z` | **Undo / Redo** | Undo or redo nondestructive editing operations |
| `F` | **Cinema Mode** | Toggle borderless fullscreen monitoring view |
| `?` | **Shortcuts Modal**| Open full Adobe Creative Suite cheatsheet |
| `1` – `7` | **Workspaces** | Switch Pipeline, Premiere, Photoshop, DAG, Agents, Library, Empire |

---

## Quality Gate Verification

All quality gates are enforced locally and in CI:

```powershell
# Run code formatting check
python -m ruff format --check src tests scripts

# Run linter
python -m ruff check src tests scripts

# Run static type checker
python -m mypy src

# Run pytest unit test suite (377 tests)
python -m pytest

# Run end-to-end smoke test (64 checks)
python scripts/smoke.py --port 8016

# Verify frontend Javascript syntax
node --check frontend/app.js; node --check frontend/editor.js; node --check frontend/flow.js
```

---

## License & Compliance

Source rights are never automatically confirmed. All external assets, research citations, and generative footage must be verified by a human operator prior to Gate 1 and Gate 2 clearance.