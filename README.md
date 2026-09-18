# AI Content Factory — Studio Pro & Autonomous Pipeline

An AI-assisted multi-format video production pipeline and professional creative studio with two mandatory human review gates: **Gate 1 (Script Approval)** and **Gate 2 (Final Video Approval)**.

The project turns reference material, historical events, and complex investigations into original creative works. A single root topic branches into **long-form documentary (YouTube 16:9)** and a cluster of **high-retention vertical shorts (TikTok / Shorts / Reels 9:16)** with zero verbatim plagiarism and zero AI hallucination.

---

## Status — measured, not asserted

Everything below was measured on this checkout. Where a gate is red, it says so.

| Surface | State | Evidence |
| :--- | :--- | :--- |
| **Backend pipeline** | Implemented and running | 51 modules in `src/content_factory`, 19 feature routers, 129 source files type-checked by mypy |
| **Vanilla studio (`frontend/*.js`)** | Implemented, served at `/` | 15,650 lines across `index.html`, `style.css`, `app.js`, `editor.js`, `flow.js` |
| **Next.js studio (`frontend/src/`)** | Builds clean, not served by the backend | 97 `.ts`/`.tsx` files, 17,726 lines. `npx tsc --noEmit` → 0 errors, `npx next build` → ✓ compiled, `/` = 259 kB first load |
| `pytest` | **11 of ~634 tests fail** | All 11 need `ffmpeg` on `PATH`; see *Known gaps* below |
| `ruff check src tests` | **242 findings** | 154 `E501` line-too-long, 20 `F821` undefined-name, 8 `E402`, 7 `BLE001`, … |
| `ruff format --check src tests` | **13 files would be reformatted** | |
| `mypy src` | **43 errors in 7 files** | `fusion_graph.py`, `photo_compositor.py`, `media_tools.py`, `hardware.py`, `models/{audio,captions,export_qc}.py` |
| End-to-end smoke test | ~64 assertions, counted at runtime | `python scripts/smoke.py` — needs a live server; the count is incremented per assertion, so the number it prints is authoritative |
| CI (`.github/workflows/ci.yml`) | Backend only | Ruff check, Ruff format, Mypy, Pytest, Smoke — **no frontend job** |

> The Python gates were green in an earlier revision. The regressions above arrived with the recent media/photo/fusion work (`fusion_graph.py` alone accounts for most of the mypy failures) and have not been cleared yet. Treat the table as the current truth, not the target.

---

## Two frontends — read this before touching the UI

The repository contains **two independent clients for the same product**. This is the single most important thing to know about the codebase.

| | Vanilla studio | Next.js studio |
| :--- | :--- | :--- |
| **Location** | `frontend/index.html`, `style.css`, `app.js`, `editor.js`, `flow.js` | `frontend/src/**` |
| **Size** | 15,650 lines | 17,726 lines across 97 files |
| **Served at** | `/` — `api/routers/index.py` returns `index.html` | Nowhere. FastAPI does not mount or proxy it |
| **Runs via** | No build step; plain `<script>` tags | `npm run dev` on `http://localhost:3000`, proxying `/api/*` to port 8000 |
| **In CI** | Smoke-tested indirectly (the `/` page must load) | No job at all |
| **State** | Hand-rolled DOM + `fetch` | TanStack Query for server state, Zustand for UI, shadcn/ui + Tailwind |

Practical consequences:

- **The vanilla studio is the product today.** It is what operators open, and it is the only UI the smoke test covers.
- **The Next.js studio is a rewrite in progress.** Its data layer was recently rebuilt around `lib/api/*` (one module per backend domain), typed contracts under `types/*`, and `lib/projectSync.ts` as the single writer of the project cache. It type-checks and builds, but parts of the UI still need checking against the real backend before they can be trusted — see `docs/frontend/`.

---

## The 7 Studio Pro Workspaces

The original studio (`frontend/`) exposes seven workspaces. Switch with the top navigation bar or the keys <kbd>1</kbd>–<kbd>7</kbd>:

1. 🚀 **Pipeline (Key 1)**: Autonomous 7-stage production stepper (`draft` ➔ `script_review` ➔ `script_approved` ➔ `generating` ➔ `video_review` ➔ `video_approved` ➔ `published`). Includes a real-time script analysis gauge, word budget calculator, and the Gate 1 / Gate 2 decision audit history.
2. 🎬 **Video Studio (Key 2)**: NLE video editing suite. Multi-track timeline (Visuals, Kinetic Captions, Voice & Beats), tool dock (Select, Razor Cut, Text, Stickers, Color Grades, VFX), TikTok Safe Zone guides, phone bezel mockup, Web Audio API SFX synthesizer, and canvas-to-WebM export.
3. 🎨 **Photo Lab (Key 3)**: Photoshop-style image and thumbnail design lab. Multi-aspect canvas (9:16 TikTok Cover, 16:9 YouTube, 1:1 Instagram, 4:5 Reels), drawing toolbar, layer stack (ordering, visibility, opacity, blend modes), tone curves, and 1-click video frame capture.
4. 🕸 **Node Flow DAG (Key 4)**: Drag-and-drop visual DAG workbench. 11-block palette, infinite canvas with SVG Bezier links, snapping grid, the pre-save checklist auditor (cycles, orphan nodes, Gate 1 & 2 enforcement), and a live terminal stream.
5. ⚡ **Agents Orchestra (Key 5)**: Multi-vendor command centre for Anthropic Claude, Google Gemini, OpenAI Codex, DeepSeek, and the local engine, with specialised prompt exporters and execution triggers.
6. 📚 **Document Library (Key 6)**: Curated research archive with streaming downloads from six public scholarly sources (arXiv, Crossref, Gutenberg, Open Library, Wikipedia, Internet Archive) backed by a SQLite FTS5 BM25 full-text search index.
7. 🏛 **Empire Hub (Key 7)**: Multi-format content engine turning one root topic into one YouTube Master Documentary (8–12 min, 16:9) plus 5–10 standalone TikTok / Shorts (30–60 s, 9:16), with Golden Hybrid Media allocation and a 15-asset prompt matrix.

The Next.js studio covers the same seven stages as a single-page workspace with a permanent sidebar (`components/layout/SidebarWorkflowNav.tsx`): Script, Media, Timeline, Workflow (DAG + Fusion), Export/QC, Campaign, and Audio Lab.

---

## Core Features

### 1. Multi-Format Content Empire Engine
- **"Don't slice YouTube into Shorts" architecture**: a single research topic powers a divergent tree:
  - **YouTube Master**: 8-step dramatic arc (*Hook ➔ Historical Context ➔ Point of No Return ➔ Escalation ➔ Catastrophic Climax ➔ Grim Consequences ➔ Declassified Twist ➔ Memorial*).
  - **TikTok / Shorts series**: 5 to 10 independent angles (*Ignored Warnings, 37s Collision Point, Lifeboat Scandals, 3 Fatal Errors*) following strict 5-phase retention pacing (0–3 s Hook, 3–10 s Context, 10–35 s Escalation, 35–50 s Climax/Twist, 50–60 s CTA).
- **Golden Hybrid Media Ratio** — a curated documentary allocation that removes the "cheap AI" feel:
  - **30% AI Reconstruction Video** (Kling AI, Google Veo, Wan 2.1)
  - **20% Restored Historical Photos** (public-domain archival, colourised and enhanced)
  - **15% Dynamic 3D Maps** (radar trajectories, flight paths, nautical routes)
  - **15% Declassified Documents** (front pages, telegrams, court transcripts)
  - **10% Technical Diagrams** (blueprints, cross-sections, engineering drawings)
  - **10% Kinetic Motion Typography**
- **15-Asset Generative Resource Package**: 1-click copy matrices for Kling/Veo, Midjourney, Suno and ElevenLabs, plus 5× CTR titles, 10× retention hooks, YouTube chapters, and SEO descriptions.

### 2. External AI Asset Ingestion Hub (Key `I` in the vanilla studio)
Direct bridge from best-of-breed creative AI tools into project timelines:
- **Zero-storage URL linking**: link CDN/S3 assets from Kling AI, Veo, Midjourney, Suno, ElevenLabs.
- **Local disk upload**: `.mp4`, `.webm`, `.jpg`, `.png`, `.mp3`, `.wav` into `storage/uploads/{project_id}/`, served by the static `/uploads` mount.
- **Batch dropzone auto-routing** by filename pattern:
  - `scene_1.*`, `sc2.*` ➔ Scene 1, Scene 2 (`scene_video` or `scene_image`)
  - `voiceover.*`, `narration.*` ➔ Master Narration Track
  - `bgm.*`, `soundtrack.*`, `suno.*` ➔ Background Music Track
- **Perplexity & DeepResearch dossier**: paste structured investigation notes into the grounded knowledge cache.
- **Visual feedback**: `[🎬 Video Attached]` and `[🖼️ Photo Attached]` badges on scene cards with quick ingest buttons.

### 3. Visual Workflow DAG System
- 11 production block types: `research`, `script`, `lint`, `gate`, `voiceover`, `scenes`, `ai_assist`, `timeline_check`, `render_plan`, `publish`, `ingest_external`.
- Pre-save checklist enforcing cycle-free topologies, orphan prevention, and human review gates.
- Asynchronous DAG execution runner with real-time console streaming.

### 4. Professional Timeline & Video Editor
- Server-authoritative editing engine (`timeline.py`) guaranteeing normalised timelines (unique IDs, clamped ranges, sorted keyframes).
- 15-rule structural validator covering WCAG text contrast, reading-speed overflow, dead air, frantic pacing, and duration drift.
- Render-plan compiler (`GET /projects/{id}/render-plan`) emitting absolute time slots, keyframes, transitions and audio layers ready for ffmpeg.

### 5. Multi-Vendor AI Agent Orchestra
- Native adapters for Anthropic Claude (`/v1/messages`), Google Gemini (`generateContent`), OpenAI Codex, DeepSeek, Ollama, and local fallbacks.
- Structured Markdown contract (`docs/AGENT-BRIDGE.md`) with automated export (`/projects/{id}/brief.md`) and parsing (`/projects/{id}/agent-result`).
- Edge-TTS integration for zero-cost neural voice synthesis (100+ locales, Vietnamese `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`).
- **Self-describing tool registry**: `GET /tools` returns a machine-readable manifest and `POST /tools/call` executes one tool by name — the surface an external agent discovers instead of guessing endpoints (`docs/TOOLS-FOR-AGENTS.md`).

### 6. Commercial Video Editing Suite & Benchmark Engine
- **NLE timeline mechanics**: `split_scene`, `duplicate_scene`, `move_scene`, `merge_scene`, `bulk_update` — pure, deterministic, server-authoritative mutations.
- **Colour grading & shaders**: one-click LUT-style grades (`teal-orange`, `noir`, `vintage`, `cyberpunk`, `pastel`) and overlays (`film-grain`, `old-film`, `glitch`, `scanlines`, `dreamy`, `sharpen`, `mosaic`).
- **Keyframe motion math**: cubic-bezier spatial interpolation with easing curves (`linear`, `ease-in`, `ease-out`, `ease-in-out`), 2D rotation, scale, position, opacity.
- **Kinetic typography & aspect ratios**: neon and outline text presets, entrance/exit cues (`slide-up`, `bounce`, `blur-in`, `fade`), safe-zone guides, and multi-aspect rendering (`9:16`, `16:9`, `1:1`, `4:5`, `3:4`).
- **Script-driven editing**: bi-directional sync between script text and timeline scenes; changing dialogue recalculates durations, speech rates and subtitle cues.

### 7. Specialized History, Disaster & Accident Pipeline
- **Federated research**: 9 providers including **Wikimedia Commons** (public-domain media), **Chronicling America** (historic newspapers), and **USGS Earthquakes** (seismic records).
- **Structured timeline extraction**: chronological milestones, turning points, casualty counts, climax markers.
- **Multi-source fact reconciliation**: cross-references sensitive statistics across independent sources (≥ 2 sources for `verified`).
- **Procedural vector graphics engine**: dark-glassmorphism animated SVG route maps (nautical, aviation, seismic) and comparative casualty infographics, zero external dependencies.
- **Policy & sensitivity audit guard**: 0–100 monetisation-safety scoring plus a regex linter for graphic violence, disrespectful disaster language, and unverified conspiracy theories, run before Gate 1 clearance.
- **Period-accurate procedural SFX**: pure Web Audio API synthesizers for Morse SOS (850 Hz), air-raid siren (450–850 Hz wail), submarine sonar ping (1550 Hz), radio static, and steam whistles.
- **"On This Day" (Ngày này năm xưa) engine**: a 12-month calendar database of maritime, aviation, seismic and industrial disasters, queryable by day or keyword.

### 8. Human-in-the-Loop Safeguards
- AI scripts and external imports **never** auto-confirm intellectual property rights.
- Video production is locked until a human operator passes **Gate 1 (Script Approval)**.
- Distribution to YouTube and TikTok is locked until a human operator passes **Gate 2 (Video Approval)**.
- The backend enforces both; a client that shows a gate as open is wrong, not authoritative.

---

## Repository Layout

```
.
├── .agents/skills/              # 35 agent skills (mirror of .claude/skills)
├── .claude/skills/              # 35 operational AI agent skills
├── .github/workflows/ci.yml     # GitHub Actions: ruff, mypy, pytest, smoke
├── .env.example                 # Configuration template (copy to .env)
├── AGENTS.md                    # Coding agent guidance & state machine rules
├── frontend/                    # Creative Studio Pro — TWO clients, see above
│   ├── index.html               # Vanilla studio: 7-workspace single page (served at /)
│   ├── style.css                # Glassmorphism design system & neon themes
│   ├── app.js                   # Pipeline controller, empire engine, ingest hub
│   ├── editor.js                # NLE timeline, Web Audio SFX, Photo Lab
│   ├── flow.js                  # Visual DAG canvas, bezier routing, checklist
│   └── src/                     # Next.js studio (port 3000, not served by FastAPI)
│       ├── app/                 # layout.tsx, page.tsx, globals.css
│       ├── components/          # ui/, layout/, script/, media/, timeline/, workflow/,
│       │                        # qa/, export/, campaign/, audio/, copilot/, thumbnails/,
│       │                        # inspector/, audit/, project/
│       ├── hooks/               # 13 TanStack Query hooks + index barrel
│       ├── lib/                 # api/ (one module per domain), client transport,
│       │                        # queryKeys, projectSync, scenes, utils
│       ├── stores/              # 7 Zustand stores
│       └── types/               # Typed contracts per backend domain
├── docs/                        # Architecture, specs & operator manuals
│   └── frontend/                # Frontend audit: architecture, bugs, security,
│                                # feature proposals, upgrade & testing roadmap
├── presets/                     # User-tunable script style presets (5 JSON overrides)
├── scripts/                     # 26 development, verification & benchmark scripts
├── storage/                     # Runtime artifacts: uploads/, cache/, audit/
├── library/                     # Document corpus + SQLite FTS5 index (created at runtime)
├── src/content_factory/         # Core application package (51 modules)
│   ├── api/                     # FastAPI app, guards, 19 feature routers
│   ├── models/                  # Pydantic contracts, one module per domain
│   ├── services/                # 16 domain mixins over a shared ServiceContext
│   ├── seo/                     # SEO engine: contracts, signals, scoring, experiments
│   ├── state.py                 # Authoritative lifecycle state machine
│   ├── timeline.py              # NLE editing engine, validator & render plan
│   ├── script_engine.py         # Section parsing, timing, copy-risk linter
│   ├── workflow.py              # DAG runner & pre-save checklist
│   └── …                        # research, rag, providers, campaign, recook,
│                                # perception, vision, audio, thumbnail, cost_guard, …
└── tests/                       # pytest suite — 49 modules, ~634 tests
```

---

## Quickstart

### Backend

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

### Next.js studio (optional, separate)

The Next client is **not** wired into the FastAPI app and is **not** built by CI. It needs Node.js 18.17+ — note that Node is not installed by default on the development machine this was written on, so install it first.

```bash
cd frontend
npm install          # or: npm ci, to honour package-lock.json exactly
npm run dev          # http://localhost:3000, proxies /api/* to 127.0.0.1:8000
npm run type-check   # tsc --noEmit — currently 0 errors
npm run build        # next build — currently passes
```

`frontend/package.json` also defines a `lint` script (`next lint`), but **ESLint is not installed and no config exists**, so that script does not run yet. See `docs/frontend/05-LO-TRINH-VA-KIEM-THU.md`.

A dependency-free structural check does exist and is CI-ready:

```bash
python scripts/frontend_imports.py   # resolves every import/export in frontend/src; exit 1 on failure
```

---

## API Reference

### 1. Project Lifecycle & Gate Approvals
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects` | Create a new project (`draft` state) |
| `GET` | `/projects` | List all active production projects |
| `GET` | `/projects/{id}` | Full project metadata and pipeline state |
| `PUT` | `/projects/{id}/script` | Save the script **and** confirm source rights (`source_rights_confirmed`) |
| `POST` | `/projects/{id}/script/generate` | Generate a script via the AI provider chain |
| `POST` | `/projects/{id}/approvals` | Submit a Gate 1 (script) or Gate 2 (video) review decision |
| `POST` | `/projects/{id}/generate` | Start / retry / re-render video generation |
| `POST` | `/projects/{id}/publish` | Publish an approved video to YouTube / TikTok |

> `PUT /projects/{id}/script` is the **only** way to record a source-rights confirmation. There is no client-side equivalent, and Gate 1 rejects an approval that arrives before it.

### 2. Multi-Format Empire Engine
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/campaign/generate` | Generate 1 YouTube Master + 5–10 Shorts + the 15-asset package |
| `GET` | `/projects/{id}/campaign` | Retrieve the active multi-format campaign |
| `PUT` | `/projects/{id}/campaign/shorts/{sid}` | Update title, hook and script for one short |
| `GET` | `/projects/{id}/campaign/export-pack` | Export the full package as a structured JSON artifact |

### 3. External AI Asset Ingestion Hub
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/external/import` | Ingest a URL or research text (Kling/Veo/MJ/Suno/Perplexity) |
| `POST` | `/projects/{id}/external/upload` | Upload a local media file bound to a scene or audio track |
| `POST` | `/projects/{id}/external/batch-import` | Batch ingest multiple external assets |
| `GET` | `/projects/{id}/external/assets` | List ingested external media records |

### 4. Visual Workflow DAG
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/workflow/blocks` | Available DAG block definitions and port schemas |
| `GET` | `/projects/{id}/workflow` | The project's custom DAG document |
| `PUT` | `/projects/{id}/workflow` | Save the DAG (audited by the pre-save checklist) |
| `GET` | `/projects/{id}/workflow/checklist` | Audit the saved workflow for cycles, orphans and gates |
| `POST` | `/projects/{id}/workflow/checklist` | Audit an unsaved draft without persisting it |
| `POST` | `/projects/{id}/workflow/run` | Execute the DAG asynchronously |
| `GET` | `/projects/{id}/workflow/runs` | Run history and terminal logs |

### 5. Video Studio & Timeline NLE
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/projects/{id}/video-project` | The editable multi-track video project |
| `PUT` | `/projects/{id}/video-project` | Persist timeline edits (server-normalised) |
| `GET` | `/projects/{id}/timeline/report` | Cut quality: 15 rules, stats, readiness score |
| `GET` | `/projects/{id}/render-plan` | Compile the timeline into an absolute render plan |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/split` | Razor-split a scene at the playhead |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/merge` | Merge a scene into the next consecutive one |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/duplicate` | Duplicate a scene with offset timings |
| `DELETE` | `/projects/{id}/timeline/scenes/{sid}` | Delete a scene |
| `POST` | `/projects/{id}/video-project/ai-assist` | Auto-edit: duration fit, beat sync, captions |
| `POST` | `/projects/{id}/voiceover/generate` | Synthesize Edge-TTS narration for all scenes |

### 6. QA, SEO, Cost & Audit
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/qa/platform/verdict` | Platform format/retention verdict with findings |
| `POST` | `/qa/brand/verdict` | Brand-kit consistency verdict |
| `POST` | `/qa/copyright/verdict` | Compare asset fingerprints against a protected set |
| `GET` | `/audit` | Provenance entries, newest first (with a derived `sha256_hash`) |
| `POST` | `/cost/check` | Price a *proposed* plan of model calls against the budget |
| `POST` | `/seo/score`, `/seo/optimize` | Score and rewrite a publishable pack |
| `GET` | `/tools` / `POST` `/tools/call` | Discover and execute one agent tool by name |

Full endpoint inventory: `docs/` plus `/docs` (Swagger) on a running server.

---

## Agent Skills Index (`.claude/skills/`)

35 skills with YAML frontmatter, mirrored in `.agents/skills/`:

| Skill | Description |
| :--- | :--- |
| **`multi-format-campaign`** | Orchestrate 1 master topic ➔ 1 YouTube long + 5–10 shorts + 15-asset package |
| **`external-results-ingestion`** | Ingest Kling, Veo, Midjourney, Suno, ElevenLabs and Perplexity into the timeline |
| **`ai-scripting`** | High-retention viral scripting, section cues, Vietnamese pacing (3.8–4.2 syl/s) |
| **`ai-video-editing`** / **`edit-video`** / **`edit-video-tools`** | NLE timeline, keyframes, Ken Burns, LUTs, safe zones, tool-by-tool editing |
| **`ai-audio-editing`** | Neural TTS, Web Audio SFX engine, ducking, BPM sync |
| **`ai-thumbnail-photo`** | Multi-aspect photo design, layer stacks, curves, contrast balancing |
| **`ai-workflow-dag`** | Visual DAG construction, checklist audit, execution management |
| **`ai-agent-orchestrator`** | Multi-agent delegation (Claude, Gemini, Codex, DeepSeek, local) |
| **`hybrid-footage-director`** | Direct the 6-component hybrid media ratio |
| **`prompt-master-kling-veo-mj`** | High-CTR cinematic prompt engineering for Kling, Veo, Midjourney |
| **`create-project`** / **`generate-script`** / **`approve-script`** | Project creation, script drafting, Gate 1 review playbook |
| **`review-video`** / **`publish-scheduler`** | Gate 2 review playbook and distribution scheduling |
| **`search-documents`** / **`fact-checker`** / **`topic-scout`** / **`asset-hunter`** | Research, verification and sourcing |
| **`sensitivity-review`** / **`seo-packaging-audit`** | Monetisation-safety audit and SEO packaging |
| **`run-dev`** / **`test`** / **`lint`** / **`smoke-test`** | Development server, pytest, ruff+mypy, end-to-end smoke |
| **`agent-brief`** / **`universal-agent-bridge`** | Export Markdown briefs and import structured agent replies |
| **`media-studio`** / **`content-recook`** / **`commercial-editing-suite`** / **`antigravity-vision-director`** | Media bin, re-cook pipeline, commercial editing, vision direction |

Run `ls .claude/skills` for the authoritative list.

---

## Adobe Creative Cloud Professional Studio UI

The vanilla studio's editing workspace is modelled on the **Adobe Creative Cloud Suite**, so editors keep the muscle memory of industry-standard post-production software:

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

| Key | Operation | Action |
|---|---|---|
| `Space` | **Play / Pause** | Toggle realtime canvas playback |
| `◀` / `▶` | **Step 1s** | Nudge the playhead backward / forward one second |
| `I` / `O` | **Mark In / Out** | Set sequence in-point `{` / out-point `}` with SMPTE timecode |
| `Alt + X` | **Clear In/Out** | Reset range markers across the timeline |
| `V` / `C` / `A` / `B` / `Y` / `P` / `H` / `T` | **Tools** | Selection, Razor, Track Forward, Ripple, Slip, Pen, Hand, Type |
| `M` | **Add Marker** | Drop a colour-coded cue marker on the playhead |
| `Ctrl + S` | **Save Project** | Persist video state to the backend |
| `Ctrl + M` | **Export** | Queue a render job in the Media Encoder panel |
| `Ctrl + Z` / `Shift+Z` | **Undo / Redo** | Undo or redo nondestructive editing operations |
| `F` | **Cinema Mode** | Toggle borderless fullscreen monitoring |
| `?` | **Shortcuts Modal** | Open the full cheatsheet |
| `1` – `7` | **Workspaces** | Pipeline, Premiere, Photoshop, DAG, Agents, Library, Empire |

---

## Quality Gate Verification

```bash
# Formatting check
python -m ruff format --check src tests scripts

# Linter
python -m ruff check src tests scripts

# Static types
python -m mypy src

# Unit + integration tests (~634 across 49 modules)
python -m pytest

# End-to-end smoke test — needs a live server
python scripts/smoke.py --port 8016

# Frontend: structural import/export check, CI-ready, no dependencies
python scripts/frontend_imports.py

# Frontend: real type check and build (requires Node.js and `npm install`)
cd frontend && npm run type-check && npm run build
```

CI (`.github/workflows/ci.yml`) runs the first five. The two frontend steps are **not** in CI yet.

---

## Known gaps

Recorded here so they are not mistaken for working features.

1. **`ffmpeg` is required but not resolvable.** `content_factory/audio.py::ffmpeg_binary()` only calls `shutil.which("ffmpeg")` and raises when it is absent — yet the venv already ships a bundled binary via `imageio_ffmpeg` (`imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`). The 11 failing tests in `test_production.py`, `test_qa_api.py`, `test_render.py` and `test_voice_engine.py` all fail on this. Either put `ffmpeg` on `PATH` or make `ffmpeg_binary()` fall back to the bundled copy.
2. **Project storage is in-memory.** `content_factory/store.py` is a thread-safe `dict`; there is no `projects.json`. Projects disappear on restart. The "vertical-slice storage" docstring is accurate; the persistence described in older docs was not built.
3. **The Python quality gates are red** (see the table at the top): 242 ruff findings, 13 unformatted files, 43 mypy errors in 7 files.
4. **The Next.js studio cannot pass Gate 1 on its own.** Only the vanilla studio is verified end-to-end; the Next client's gate wiring is newer and less exercised.
5. **Some audio capabilities have engine code but no route.** `perception.py` (silence/pace, mood, loudness) and the `audio.py` ducking mixers are implemented and tested but unpublished, so no client can call them. The Next audio lab says so on-screen instead of showing invented numbers.
6. The docs reference `docs/KE-HOACH-TONG-THE.md` as the running change log; keep appending there after non-trivial work (`docs/README.md` documents the template).

---

## License & Compliance

Source rights are never automatically confirmed. All external assets, research citations and generative footage must be verified by a human operator before Gate 1 and Gate 2 clearance.
