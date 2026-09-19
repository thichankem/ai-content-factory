# AI Content Factory — Studio Pro & Autonomous Pipeline

An AI-assisted multi-format video production pipeline and professional creative studio with two mandatory human review gates: **Gate 1 (Script Approval)** and **Gate 2 (Final Video Approval)**.

The project turns reference material, historical events, and complex investigations into original creative works. A single root topic branches into **long-form documentary (YouTube 16:9)** and a cluster of **high-retention vertical shorts (TikTok / Shorts / Reels 9:16)** with zero verbatim plagiarism and zero AI hallucination.

---

## Status — measured on this checkout, not asserted

Every number below came from a command run in this workspace. The command is named next to the number so it can be re-run rather than believed.

| Surface | State | Evidence |
| :--- | :--- | :--- |
| **Backend** | Running | 149 Python files under `src/content_factory` (72 top-level engine modules), **≈39 400 lines** |
| **HTTP API** | 19 routers, **185 endpoints** | `grep -c '@router\.\(get\|post\|put\|delete\|patch\)(' src/content_factory/api/routers/*.py` |
| **Agent tool surface** | **110 tools** | `len(agent_tools.TOOL_SPECS)`; JSON manifest at `GET /tools` |
| `ruff check src tests` | **Clean** | 0 findings |
| `ruff format --check src tests` | **Clean** | 220 files already formatted |
| `mypy src` | **Clean** | 0 issues in 149 source files |
| `pytest` | **All pass** | 1 087 tests across 66 modules; full run exits 0 |
| `ruff check scripts` | **253 findings** | Mostly `E501`; `scripts/` is **not** in the CI job |
| `scripts/smoke.py` | **64 / 64 checks** | Measured against a fresh server on a free port |
| Vanilla studio (`frontend/*.js`) | Served at `/` | 17 209 lines across `index.html`, `style.css`, `app.js`, `editor.js`, `flow.js` |
| Next.js studio (`frontend/src/`) | Builds, not served by the backend | 98 `.ts`/`.tsx` files, 18 255 lines; `npm run type-check` → 0 errors; `scripts/frontend_imports.py` → clean (98 files) |
| CI (`.github/workflows/ci.yml`) | Backend only | Ruff check, Ruff format, Mypy, Pytest, Smoke — no frontend job |

```bash
# Reproduce the table.
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest
python scripts/smoke.py --port 8016        # needs a live server on that port
python scripts/frontend_imports.py
cd frontend && npm run type-check
```

> The suite is heavy: it loads OCR (easyocr/torch) and speech models, and a few tests touch the network through `yt-dlp`. A run typically takes a couple of minutes; on a loaded machine it can take much longer. The gates that CI enforces are the first four rows.

---

## Fixed in the current pass — the edit / image / video / audio review

A full sweep of the media backend found the audio DSP filters were **not filtering**. Every "keep this band" stage in the codebase was built from coefficients that were wrong, and the tests that should have caught it only compared near-zero numbers to each other.

| # | Defect | Symptom | Fix |
| :--- | :--- | :--- | :--- |
| 1 | `audio_effects._rbj_coeffs` built the **high-pass** numerator from the shelf gain factor `a` and dropped the `z^-2` term | The filter was a bare differentiator: response rose to **≈57× near the cutoff** instead of rolling off. Every high-pass, and every band effect built on it, was wrong | Proper RBJ high-pass numerator from `cos(w0)` |
| 2 | `_rbj_coeffs` had **no `lowpass` case** — it fell through to the high-shelf branch | The `lowpass` effect used high-pass coefficients and did the **opposite** of its name; its catalogue entry still promised "removes harsh highs" | Added the RBJ low-pass branch and wired `_fx_lowpass` to it |
| 3 | Band effects used a **high-pass for their upper edge** — `telephone` (3 400 Hz), `radio` (4 000 Hz), `megaphone` (3 000 Hz), `underwater` (600 Hz) | Each kept *everything above* the upper cutoff rather than the band; `underwater` was the reverse of "muffled, low-passed" | Upper edge is now a low-pass |
| 4 | `audio_separation._band` used a high-pass for the upper edge; the 3-stem `low` band used a high-pass at 250 Hz | "Voice isolation" returned everything **above 4 kHz**; the "low" stem (bass/kick) returned everything above 250 Hz | Band = high-pass(low) + low-pass(high); `low` = low-pass(250) |
| 5 | `audio_analysis.rms` **hard-coded 44 100 Hz** for its window hop | Frame timing — and therefore the noise-floor and SNR numbers — was wrong for any other sample rate | `rms(samples, frame_seconds, sr)`, threaded through `noise_floor` |
| 6 | `audio_assist.execute_mastering_chain` reached into `voice_engine._spectral_gate` / `_normalize_loudness` | Sibling modules coupled to each other's private functions | New public `voice_engine.denoise_pcm` / `normalize_loudness_pcm`; `denoise_audio` now reuses `denoise_pcm` |
| 7 | `hardware.require_ffmpeg` stopped at `shutil.which("ffmpeg")` | A venv that ships `imageio-ffmpeg` still had every ffmpeg-backed feature refuse to run — the gap recorded in `tests/README.md` | Falls back to the bundled build; `resolve_ffmpeg` stays honest and still reports only what is on `PATH` |
| 8 | `api/routers/media.py::media_remove_tag` had an unreachable `return service.media_list()` | Dead code calling a method that no longer exists (`AttributeError` if ever reached) | Removed |
| 9 | `services/production.py::apply_video_effect` re-encoded its output through `edit_image_bytes` | Decode → effect → PNG → decode PNG → encode PNG for nothing, and the report never said which effect ran | New `persist_image_bytes`; the result now carries `effect` and `params` |
| 10 | `Image.fromarray(..., mode="RGB")` at 9 sites (`photo_ops`, `video_effects`, `production`) | Deprecated; removed in Pillow 13 | Dropped the argument (shapes already imply `RGB`) |
| 11 | `services/media_tools.py::resolve_media_ref` ended with `del edited_dir` | Noise left over from an earlier edit | Removed |

### Refactored in the same pass

The rest of the backend was reviewed for duplication and cohesion. Four modules came out of it:

| New module | Why it exists | Replaces |
| :--- | :--- | :--- |
| `params.py` | One implementation of reading a number, a flag or an RNG seed out of an untyped parameter mapping | private `_num`/`_seed`/`_clamp01` copies in `audio_effects`, `sfx`, `video_effects`, `photo_ops` |
| `pixels.py` | One implementation each of `as_rgb`/`rgb_array`/`to_image`/`to_uint8`/`luminance`/`remap` | byte-identical copies in `photo_ops` and `video_effects`; the Rec.709 coefficients were spelled out in three modules |
| `catalog.py` | The `{name, description, params}` entry shape and the grouped catalogue envelope | the same ~12-line grouping loop written three times in `photo_assist`, `video_assist`, `audio_assist` |
| `services/studio.py` | The image / voice / audio studio facade (`StudioMixin`) | the studio half of `services/production.py`, which used to be the file you opened to find a photo operation |

Also cleaned up:

- **`services/production.py`** is now only the video pipeline (`ProductionMixin(StudioMixin)`), 452 → 137 lines.
- **`services/media_tools.py::resolve_media_ref`** resolved an asset through one long branch; it is now three named lookups (`_library_path` → `_edited_asset_path` → `_sandboxed_path`) with the precedence documented.
- **`photo_ops._flag`** was dead code (the ops call `op.flag(...)`, the `ImageOp` method) — removed by the extraction rather than carried along.
- **`photo_compositor._clamp01`** renamed to `_clamp01_array`: it clamps an array, and now sits next to a scalar `params.clamp01` that would otherwise read as the same helper.

Each engine may still bind a shared helper to its own exception type, but only by delegating — `tests/test_architecture.py` now fails if a module defines `_num`/`_seed`/`_clamp01`/`_luminance`/`_remap`/`_to_uint8` again without importing the shared implementation.

**Regression lock.** The old tests could not tell a correct filter from a broken one, so new assertions measure the *frequency response* rather than comparing two near-zero correlations:

- `tests/test_audio_effects.py` — `lowpass` must pass 200 Hz and reject 12 kHz (and the mirror case for `highpass`); `telephone` must reject 12 kHz.
- `tests/test_audio_separation.py` — the voice stem must **keep** the 440 Hz tone inside 200–4 000 Hz and reject both 60 Hz and 12 kHz; the three-stem split is checked band by band.
- `tests/test_production.py` — `require_ffmpeg` prefers `PATH`, falls back to a bundled build, and still raises when neither exists.

Verified end to end: with `PATH` emptied, `resolve_ffmpeg()` returns `None` while `require_ffmpeg()` returns the bundled `imageio-ffmpeg` binary and a real MP3 encode/decode round-trip succeeds. Over HTTP, `POST /studio/audio/effect`, `/studio/audio/stems` and `/studio/audio/analyze` all return 200 and persist an asset.

---

## Two frontends — read this before touching the UI

The repository contains **two independent clients for the same product**. This is the single most important thing to know about the codebase.

| | Vanilla studio | Next.js studio |
| :--- | :--- | :--- |
| **Location** | `frontend/index.html`, `style.css`, `app.js`, `editor.js`, `flow.js` | `frontend/src/**` |
| **Size** | 17 209 lines | 18 255 lines across 98 files |
| **Served at** | `/` — `api/routers/index.py` returns `index.html` | Nowhere. FastAPI does not mount or proxy it |
| **Runs via** | No build step; plain `<script>` tags | `npm run dev` on `http://localhost:3000`, proxying `/api/*` to port 8000 |
| **In CI** | Smoke-tested indirectly (the `/` page must load) | No job at all |
| **State** | Hand-rolled DOM + `fetch` | TanStack Query for server state, Zustand for UI, shadcn/ui + Tailwind |

Practical consequences:

- **The vanilla studio is the product today.** It is what operators open, and it is the only UI the smoke test covers.
- **The Next.js studio is a rewrite in progress.** Its data layer was rebuilt around `lib/api/*` (one module per backend domain), typed contracts under `types/*`, and `lib/projectSync.ts` as the single writer of the project cache. It type-checks and builds, but parts of the UI still need checking against the real backend before they can be trusted — see `docs/frontend/`.

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
- Structural validator with **16 issue codes** (`timeline.validate`) covering WCAG text contrast, narration overflow/underfill, empty scenes and timelines, frantic pacing, extreme speed, transition length, out-of-range markers, flat looks, and duration drift.
- Render-plan compiler (`GET /projects/{id}/render-plan`) emitting absolute time slots, keyframes, transitions and audio layers ready for ffmpeg.

### 5. Multi-Vendor AI Agent Orchestra
- Native adapters for Anthropic Claude (`/v1/messages`), Google Gemini (`generateContent`), OpenAI Codex, DeepSeek, Ollama, and local fallbacks.
- Structured Markdown contract (`docs/AGENT-BRIDGE.md`) with automated export (`/projects/{id}/brief.md`) and parsing (`/projects/{id}/agent-result`).
- Edge-TTS integration for zero-cost neural voice synthesis (100+ locales, Vietnamese `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`).
- **Self-describing tool registry**: `GET /tools` returns a machine-readable manifest of **110 tools** and `POST /tools/call` executes one by name — the surface an external agent discovers instead of guessing endpoints (`docs/TOOLS-FOR-AGENTS.md`).

### 6. Commercial Video Editing Suite & Benchmark Engine
- **NLE timeline mechanics**: `split_scene`, `duplicate_scene`, `move_scene`, `merge_scene`, `bulk_update` — pure, deterministic, server-authoritative mutations.
- **Colour grading & shaders**: one-click LUT-style grades (`teal-orange`, `noir`, `vintage`, `cyberpunk`, `pastel`) and overlays (`film-grain`, `old-film`, `glitch`, `scanlines`, `dreamy`, `sharpen`, `mosaic`).
- **Keyframe motion math**: cubic-bezier spatial interpolation with easing curves (`linear`, `ease-in`, `ease-out`, `ease-in-out`), 2D rotation, scale, position, opacity.
- **Kinetic typography & aspect ratios**: neon and outline text presets, entrance/exit cues (`slide-up`, `bounce`, `blur-in`, `fade`), safe-zone guides, and multi-aspect rendering (`9:16`, `16:9`, `1:1`, `4:5`, `3:4`).
- **Script-driven editing**: bi-directional sync between script text and timeline scenes; changing dialogue recalculates durations, speech rates and subtitle cues.

### 7. Audio Engineering Suite
- **32 DSP effects** (`audio_effects.py`), pure NumPy, no model: 3-band EQ, compressor, limiter, expander, de-esser, noise gate, clipper, saturation, biquad filter set (high/low/band/notch, shelves), and creative processors (reverb, delay, echo, chorus, flanger, phaser, distortion, bitcrusher, tremolo, vibrato, ring modulation, telephone, radio, megaphone, underwater, robot, reverse).
- **Analysis & accessibility** (`audio_analysis.py`, `audio_assist.py`): waveform envelope, spectrogram, octave-band spectrum, RMS/crest factor, clipping, noise floor and SNR, phase correlation — plus a plain-language description of any clip and an auto-suggested mastering chain that actually executes.
- **Sound synthesis** (`sfx.py`): whoosh, impact, explosion, footstep, ambience, transition swell, UI click — generated from scratch, no sample library.
- **Stem separation & voice isolation** (`audio_separation.py`): deterministic DSP band split (voice/instrumental, or low/mid/high) with a pluggable ML adapter hook for Demucs/Spleeter/UVR.
- **Pluggable AI audio** (`ai_audio.py`): dubbing and voice cloning delegate to a registered adapter and **fail loudly** when none is configured rather than fabricating a result.
- **Spectral denoise** (`voice_engine.py`): 50%-overlap STFT with a Wiener-style per-bin gate, learning the noise spectrum from a profile sample or the quietest frames.

### 8. Specialized History, Disaster & Accident Pipeline
- **Federated research**: 9 providers including **Wikimedia Commons** (public-domain media), **Chronicling America** (historic newspapers), and **USGS Earthquakes** (seismic records).
- **Structured timeline extraction**: chronological milestones, turning points, casualty counts, climax markers.
- **Multi-source fact reconciliation**: cross-references sensitive statistics across independent sources (≥ 2 sources for `verified`).
- **Procedural vector graphics engine**: dark-glassmorphism animated SVG route maps (nautical, aviation, seismic) and comparative casualty infographics, zero external dependencies.
- **Policy & sensitivity audit guard**: 0–100 monetisation-safety scoring plus a regex linter for graphic violence, disrespectful disaster language, and unverified conspiracy theories, run before Gate 1 clearance.
- **Period-accurate procedural SFX**: pure Web Audio API synthesizers for Morse SOS (850 Hz), air-raid siren (450–850 Hz wail), submarine sonar ping (1550 Hz), radio static, and steam whistles.
- **"On This Day" (Ngày này năm xưa) engine**: a 12-month calendar database of maritime, aviation, seismic and industrial disasters, queryable by day or keyword.

### 9. Human-in-the-Loop Safeguards
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
│       ├── hooks/               # TanStack Query hooks + index barrel
│       ├── lib/                 # api/ (one module per domain), client transport,
│       │                        # queryKeys, projectSync, scenes, utils
│       ├── stores/              # Zustand stores
│       └── types/               # Typed contracts per backend domain
├── docs/                        # 19 architecture docs, specs & operator manuals
│   └── frontend/                # 6 frontend audit reports (architecture, bugs,
│                                # security, proposals, roadmap)
├── presets/                     # 5 user-tunable script style presets (JSON)
├── scripts/                     # 34 development, verification & benchmark scripts
├── storage/                     # Runtime artifacts: uploads/, cache/, audit/
├── library/                     # Media library, edited assets, renders, music
├── src/content_factory/         # Core application package (149 files, 72 modules)
│   ├── api/                     # FastAPI app, guards, 19 routers, 185 endpoints
│   ├── models/                  # 22 Pydantic contract modules, one per domain
│   ├── services/                # 21 domain mixins over a shared ServiceContext
│   │                            # studio.py = image/voice/audio facade,
│   │                            # production.py = video pipeline + ffmpeg export
│   ├── params.py                # shared parameter coercion (number/flag/seed)
│   ├── pixels.py                # shared pixel maths (RGB, luminance, remap)
│   ├── catalog.py               # shared accessibility-catalogue shape
│   ├── text.py                  # shared tokenizers, slugs, title keys
│   ├── seo/                     # SEO engine: contracts, signals, scoring, experiments
│   ├── state.py                 # Authoritative lifecycle state machine
│   ├── timeline.py              # NLE editing engine, validator & render plan
│   ├── script_engine.py         # Section parsing, timing, copy-risk linter
│   ├── audio_effects.py         # 32 pure-NumPy DSP effects (see "Fixed" above)
│   ├── audio_analysis.py        # Waveform / spectrogram / meters / SNR
│   ├── audio_assist.py          # Plain-language audio description + mastering chain
│   ├── audio_separation.py      # Stem split & voice isolation
│   ├── sfx.py                   # Procedural sound-effect synthesis
│   ├── ai_audio.py              # Dubbing / voice-clone adapter registry
│   ├── voice_engine.py          # Voice chain, spectral denoise, ducking
│   ├── image_engine.py          # Image op pipeline & export
│   ├── photo_ops.py             # 878 lines of photo operations
│   ├── photo_assist.py          # Image accessibility layer
│   ├── video_effects.py         # Frame effects + video accessibility layer
│   ├── media_tools.py           # ffmpeg harness: probe/cut/mix/compose
│   ├── workflow.py              # DAG runner & pre-save checklist
│   └── …                        # research, rag, providers, campaign, recook,
│                                # perception, vision, hardware, cost_guard, …
└── tests/                       # pytest suite — 66 modules, 1 087 tests
```

---

## Quickstart

### Backend

Requires Python 3.11+.

```powershell
# Windows (PowerShell)
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
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

`ffmpeg` is resolved in this order: the `CONTENT_FACTORY_FFMPEG_BINARY` setting, then `PATH`, then a build bundled inside an installed package (`imageio-ffmpeg`). Installing `imageio-ffmpeg` is therefore enough to make every ffmpeg-backed feature work; no system install is strictly required.

### Next.js studio (optional, separate)

The Next client is **not** wired into the FastAPI app and is **not** built by CI. It needs Node.js 18.17+ (Node 22 verified here).

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

**185 endpoints across 19 routers.** The table below is the operator's map; the authoritative list is `/docs` (Swagger) on a running server.

### 1. Project Lifecycle & Gate Approvals — `projects.py` (18)
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
| `GET` | `/projects/{id}/brief.md` | Export the structured agent brief (Markdown) |
| `POST` | `/projects/{id}/agent-result` | Import a structured agent reply |

> `PUT /projects/{id}/script` is the **only** way to record a source-rights confirmation. There is no client-side equivalent, and Gate 1 rejects an approval that arrives before it.

### 2. Multi-Format Empire Engine — `campaign.py` (4)
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/campaign/generate` | Generate 1 YouTube Master + 5–10 Shorts + the 15-asset package |
| `GET` | `/projects/{id}/campaign` | Retrieve the active multi-format campaign |
| `PUT` | `/projects/{id}/campaign/shorts/{sid}` | Update title, hook and script for one short |
| `GET` | `/projects/{id}/campaign/export-pack` | Export the full package as a structured JSON artifact |

### 3. External AI Asset Ingestion Hub — `external.py` (4)
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/{id}/external/import` | Ingest a URL or research text (Kling/Veo/MJ/Suno/Perplexity) |
| `POST` | `/projects/{id}/external/upload` | Upload a local media file bound to a scene or audio track |
| `POST` | `/projects/{id}/external/batch-import` | Batch ingest multiple external assets |
| `GET` | `/projects/{id}/external/assets` | List ingested external media records |

### 4. Visual Workflow DAG — `workflow.py` (8)
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/workflow/blocks` | Available DAG block definitions and port schemas |
| `GET` | `/projects/{id}/workflow` | The project's custom DAG document |
| `PUT` | `/projects/{id}/workflow` | Save the DAG (audited by the pre-save checklist) |
| `GET` | `/projects/{id}/workflow/checklist` | Audit the saved workflow for cycles, orphans and gates |
| `POST` | `/projects/{id}/workflow/checklist` | Audit an unsaved draft without persisting it |
| `POST` | `/projects/{id}/workflow/run` | Execute the DAG asynchronously |
| `GET` | `/projects/{id}/workflow/runs` | Run history and terminal logs |

### 5. Video Studio & Timeline NLE — `timeline.py` (29)
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` / `PUT` | `/projects/{id}/video-project` | Read / persist the editable multi-track video project (server-normalised) |
| `GET` | `/projects/{id}/timeline/report` | Cut quality: 16 validator rules, stats, readiness score |
| `GET` | `/projects/{id}/timeline/describe` | Plain-language summary of the timeline (accessibility) |
| `GET` | `/projects/{id}/timeline/suggest` | Concrete edit suggestions from the validator's findings |
| `GET` | `/projects/{id}/render-plan` | Compile the timeline into an absolute render plan |
| `POST` | `/projects/{id}/render` | Render the timeline to a real video file (webm / mp4) |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/split` | Razor-split a scene at the playhead |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/merge` | Merge a scene into the next consecutive one |
| `POST` | `/projects/{id}/timeline/scenes/{sid}/duplicate` | Duplicate a scene with offset timings |
| `DELETE` | `/projects/{id}/timeline/scenes/{sid}` | Delete a scene |
| `POST` | `/projects/{id}/video-project/ai-assist` | Auto-edit: duration fit, beat sync, captions |
| `POST` | `/projects/{id}/voiceover/generate` | Synthesize Edge-TTS narration for all scenes |

### 6. Studio — Image / Voice / Audio / Video — `studio_media.py` (36)
The largest router: the Photoshop / Audition / Premiere-style surface.

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/studio/image/presets` | Named one-click photo looks + the raw op vocabulary |
| `GET` | `/studio/image/ops` | Full op catalogue grouped by category, with plain-language docs |
| `POST` | `/studio/image/edit` | Edit an image with an ops pipeline (JSON) or a named preset |
| `POST` | `/studio/image/batch` | Apply the same pipeline to several images |
| `POST` | `/studio/image/analyze` | Describe an image from its pixel statistics (vision-free) |
| `POST` | `/studio/image/suggest` | Histogram-based auto-suggestions |
| `POST` | `/studio/image/session/begin` | Start a non-destructive edit session |
| `POST` | `/studio/image/session/{sid}/edit` \| `/undo` \| `/redo` | Step / undo / redo a session |
| `GET` | `/studio/audio/effects` \| `/ops` \| `/sfx` \| `/stems` \| `/ai` | Catalogues: DSP effects, grouped ops, synthesised SFX, stems, AI capabilities |
| `POST` | `/studio/audio/effect` | Apply a DSP effect to audio bytes |
| `POST` | `/studio/audio/analyze` | Waveform, spectrogram, spectrum, meters |
| `POST` | `/studio/audio/describe` | Plain-language description from the measurements |
| `POST` | `/studio/audio/mastering` \| `/mastering/apply` | Auto-suggest, then run, a mastering chain |
| `POST` | `/studio/audio/sfx` | Generate a sound effect from scratch |
| `POST` | `/studio/audio/stems` | Separate a clip into stems |
| `POST` | `/studio/audio/dub` \| `/voice-clone` | Delegate to a registered ML adapter (422 if none) |
| `GET` | `/studio/video/effects` \| `/ops` | Frame-effect catalogue and grouped video/audio operations |
| `POST` | `/studio/video/effect` | Apply a frame effect to an image or video frame |
| `GET` | `/studio/voice/presets` | Named voice chains and every tunable chain parameter |
| `POST` | `/studio/voice/enhance` | Enhance voice audio through the Audition-style chain |
| `GET` | `/edited/{name}` | Download a persisted edited asset (image, audio or video) |

### 7. Media Library & AI Video Editor — `media.py` (21)
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/media/upload` \| `/media/from-url` \| `/media/audio-clip` | Ingest a file, a URL, or a trimmed audio clip |
| `GET` | `/media` | Query the media database (kind, tag, free text, source, duration, date, sort) |
| `GET` | `/media/stats` \| `/media/tags` | Aggregate counts/sizes and every distinct tag |
| `POST` | `/media/{id}/tags`, `/tags/{tag}` · `DELETE` `/tags/{tag}` | Tag CRUD |
| `POST` | `/media/{id}/transcribe` \| `/extract-text` \| `/convert` \| `/recook` | Transcribe, extract text, convert format, re-cook into a new project |
| `GET` | `/youtube/search` · `POST` `/youtube/download` \| `/youtube/transcript` | Search, download and transcribe reference video |
| `POST` | `/ai-editor/edit` | Analyse a video, composite an image naturally, trim dead air, export |
| `GET` | `/ai-editor/output/{filename}` | Serve an edited video produced by the AI editor |

### 8. Knowledge Q&A, QA, SEO, Cost & Audit
| Router | Endpoints | Headline paths |
| :--- | :--- | :--- |
| `knowledge.py` | 17 | `POST /kb/{id}/ask` (grounded Q&A with `[n]` citations), `POST /kb/{id}/ingest-url`, chunk CRUD |
| `qa.py` | 18 | `POST /qa/platform/verdict`, `/qa/brand/verdict`, `/qa/copyright/verdict`, `GET /audit`, `POST /audit/record`, `GET /cost/estimate`, `POST /cost/check` |
| `seo.py` | 8 | `POST /seo/score`, `/seo/optimize`, `GET /seo/rules` |
| `tools.py` | 2 | `GET /tools` (110-tool manifest), `POST /tools/call` |
| `library.py` | 3 | `GET /library` (paginated archive), `GET /library/search` |
| `resources.py` | 3 | `GET /resources`, `/resources/kinds`, `/resources/explain` |
| `styles.py` | 5 | Script style preset CRUD (`GET/PUT/DELETE /script/styles…`) |
| `agents.py` | 3 | `GET /agents` — the multi-vendor agent catalogue |
| `history.py` | 2 | `GET /history/search`, `GET /history/on-this-day` |
| `graphics.py` | 2 | `POST /projects/{id}/graphics/map`, `/graphics/infographic` |
| `index.py` / `health.py` | 1 each | `GET /` (the studio) and `GET /health` |

---

## Agent Tools — 110 by name

`GET /tools` returns the whole manifest; `POST /tools/call` runs one. Registration is split so no single module grows unbounded: `agent_tools.py` holds the core registry and the per-domain handlers live in `agent_audio.py`, `agent_video.py`, `agent_photo.py`, `agent_knowledge.py`, `agent_youtube.py`.

| Category | Count | Examples |
| :--- | :--- | :--- |
| `discovery` | 8 | `list_projects`, `get_project`, `agent_catalog`, `list_script_styles` |
| `research` | 8 | `research_project`, `attach_kb`, `ground_project` |
| `script` | 3 | `update_script`, `analyze_script`, `export_brief` |
| `timeline` | 17 | `split_scene`, `merge_scene`, `move_scene`, `set_keyframes`, `ai_assist` |
| `media` | 22 | `describe_media`, `cut_media`, `join_media`, `compose_images`, `collage_images` |
| `audio` | 22 | `audio_trim`, `audio_mix`, `audio_denoise`, `analyze_audio`, `synthesize_sfx`, `separate_audio_stems`, `apply_audio_mastering`, `dub_audio` |
| `image` | 14 | `edit_image`, `batch_edit_image`, `analyze_image`, `image_session_*` |
| `voice` | 3 | `voice_presets`, `enhance_voice`, `duck_music` |
| `seo` / `production` / other | 13 | `seo_score`, `render_video`, `render_plan`, `start_generation`, `publish_project` |

---

## Agent Skills Index (`.claude/skills/`, mirrored in `.agents/skills/`)

35 skills with YAML frontmatter in each tree:

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
python -m ruff format --check src tests

# Linter
python -m ruff check src tests

# Static types
python -m mypy src

# Unit + integration tests (1 087 collected across 66 modules)
python -m pytest

# End-to-end smoke test — needs a live server on a free port
python scripts/smoke.py --port 8016

# Frontend: structural import/export check, CI-ready, no dependencies
python scripts/frontend_imports.py

# Frontend: real type check and build (requires Node.js and `npm install`)
cd frontend && npm run type-check && npm run build
```

CI (`.github/workflows/ci.yml`) runs Ruff check, Ruff format, Mypy, Pytest and the smoke test — all on `src` and `tests`. The two frontend steps are **not** in CI yet, and `scripts/` is not linted by CI either.

---

## Known gaps

Recorded here so they are not mistaken for working features.

1. **Project storage is in-memory.** `content_factory/store.py` is a thread-safe `dict` with compare-and-save; there is no `projects.json`. Projects disappear on restart. Persisting them is straightforward but needs to be **opt-in** (a setting), because the suite and the smoke test assume a clean store per process.
2. **`scripts/` is not linted by CI.** `python -m ruff check scripts` reports 253 findings (mostly `E501`) while `src` and `tests` are clean. Either add `scripts` to the CI job and fix them, or narrow the job explicitly.
3. **Dubbing and voice cloning need an adapter.** `ai_audio.py` is deliberately honest: with no `"dub"` / `"voice_clone"` adapter registered, those endpoints return a clear 422 rather than a fabricated result. A real backend (ElevenLabs, RVC, XTTS) still has to be wired up.
4. **Stem separation is DSP, not ML.** `audio_separation.py` splits by frequency band and exposes an adapter hook; it is not Demucs. The band split cannot separate two instruments that occupy the same band.
5. **`voice_engine._highpass` is a one-pole approximation**, documented as such. It is adequate for removing speech rumble but is not the RBJ biquad the effect layer uses; the two high-passes will not sound identical.
6. **The Next.js studio cannot pass Gate 1 on its own.** Only the vanilla studio is verified end-to-end; the Next client's gate wiring is newer and less exercised.
7. **The docs reference `docs/KE-HOACH-TONG-THE.md` as the running change log.** Keep appending there after non-trivial work (`docs/README.md` documents the template). `tests/README.md` and `docs/frontend/` carry older figures than the tables above — prefer the numbers in this file when they disagree.

---

## License & Compliance

Source rights are never automatically confirmed. All external assets, research citations and generative footage must be verified by a human operator before Gate 1 and Gate 2 clearance.
