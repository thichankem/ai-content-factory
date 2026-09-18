# Problem Report

Updated: 2026-09-16

> ## ⚠️ This report is a historical record. Its verdicts no longer hold.
>
> Every check below is reported as `PASS` against a workspace that has since
> diverged. Re-measured on **2026-09-18**, the same commands give:
>
> | Check | This report (2026-09-16) | Re-measured (2026-09-18) |
> | --- | --- | --- |
> | `python -m pytest -q` | PASS | **11 failures** of ~634 — all need `ffmpeg` on `PATH` |
> | `python -m ruff check src tests` | PASS | **242 findings** (`E501` ×154, `F821` ×20, …) |
> | `python -m ruff format --check src tests` | PASS, 54 files | **13 files would be reformatted** |
> | `python -m mypy src` | PASS, 27 files | **43 errors in 7 files**, 129 checked |
> | `python scripts/toolcheck.py --strict` | PASS — `ffmpeg`/`ffprobe` available | **`ffmpeg` is not on `PATH`** in this environment |
>
> The most likely explanation is a different machine: `--strict` passed there
> because `ffmpeg` was installed, and here it is not. The type and lint counts
> are a different matter — 129 source files are type-checked now against 27 then,
> and the newest modules (`fusion_graph.py`, `photo_compositor.py`,
> `media_tools.py`) account for most of the failures. They were added after this
> report was written.
>
> **Treat the table below as history, not as current state.** The authoritative
> numbers live in the root `README.md` → *Status*.

This report records the checks run in the current Windows workspace and the
remaining problems or unverified capabilities. It does not claim that an
external provider or tool was tested when it was not available locally.

## Checks Run

| Check | Result | Notes |
| --- | --- | --- |
| `python -m pytest -q` | PASS | Full suite passed sequentially; only upstream Starlette/httpx deprecation warnings remain. |
| `python scripts/smoke.py` | PASS | 64 end-to-end checks passed on a fresh server (lifecycle, research, presets, agent bridge, workflow, campaign, external assets, frontend, state-machine guards). |
| `python -m ruff check src tests` | PASS | All checks passed. |
| `python -m ruff format --check src tests` | PASS | 54 files formatted. |
| `python -m mypy src` | PASS | 27 source files checked with no issues. |
| `python scripts/qa_war_full_flow.py` | PASS | 6 distinct war projects driven end-to-end; each produced a real probeable VP9 WebM (~44–45 s, ~1 MB) and reached `published`. |
| `python -m pytest tests/test_script_engine.py -q` | PASS | Includes the new P1 regression lock for the `build_script_prompt(grounding=...)` signature. |
| `python scripts/toolcheck.py` | PASS (inventory) | 8 tools available, 6 optional heavy tools missing. |
| `python scripts/toolcheck.py --strict` | PASS | Required tools `ffmpeg` and `ffprobe` are available. |

## Problems To Fix

### Resolved: P1 — test execution sensitive to concurrent activity

The original anomaly was a stale-bytecode race: a concurrent run of pytest,
smoke, lint, and tool inventory once loaded a `script_engine` from a poisoned
`__pycache__` whose `build_script_prompt()` lacked the `grounding` keyword, so
`service._build_prompt` raised a `TypeError`. The `__pycache__` in this
workspace held bytecode from two different pytest versions (9.0.3 and 9.1.1),
confirming the shared-state cache as the culprit.

Fixed:

1. Added a deterministic regression test
   `test_build_script_prompt_accepts_grounding_keyword` in
   `tests/test_script_engine.py`. It inspects the signature with
   `inspect.signature` to assert `grounding` is a keyword-only parameter and
   proves a `GroundingBundle` actually renders into the prompt. This makes the
   exact P1 failure impossible to reintroduce silently.
2. Removed the stale `__pycache__`, `.pytest_cache`, `.ruff_cache`, and
   `.mypy_cache` directories so no process can import a stale module.

The sequential full suite, smoke test, lint, and mypy all pass. The test and
smoke commands are still documented to run sequentially in CI/local QA; the
regression test guards the prompt contract regardless.

### Resolved: Windows wrappers and missing dependencies

The wrappers call `scripts/setup.ps1` when `.venv` is missing. The project
declares `python-multipart` (runtime) and `pymupdf` (dev), so a fresh
environment can import the upload API and run the benchmark test.

### Partially addressed: P2 — optional local tools

Four lightweight, GPU-free optional tools were installed into the `.venv`:

- `pillow` (PIL) — image compositing and thumbnails
- `opencv-python-headless` (`cv2`) — frame analysis and stabilization
- `moviepy` — programmatic video edits
- `yt-dlp` (Python package) — reference-video download

`toolcheck.py` now reports 8 available. The remaining missing tools are the
heavy torch/GPU-dependent ones, which were intentionally not installed in this
offline workspace:

- `faster-whisper`: transcription and word timestamps
- `whisperx`: forced alignment
- `demucs`: vocal/music separation
- `rembg`: background removal
- `TTS`: local multilingual voice cloning

Notes:

- Installing the optional tools pulled in `numpy 2.5.3`, whose type stubs use
  Python 3.12 syntax and broke `mypy` (configured for `python_version = "3.11"`).
  `numpy` was pinned to `2.2.6` (3.11-compatible stubs); opencv and moviepy do
  not pin numpy, so the downgrade is safe. mypy passes again.
- `yt-dlp` is installed as a Python package but `toolcheck.py` checks for the
  `yt-dlp` CLI binary on `PATH`, so it still reports `[missing]`. The package
  is importable; only the console-script wrapper is not on `PATH`.

## Unverified Skills

The repository contains the current skill set under `.claude/skills/`. The
following were exercised directly or covered by automated tests: `test`,
`lint`, `smoke-test`, `run-dev` behavior through smoke startup, project
lifecycle/approval, script generation and analysis, agent bridge, workflow,
campaign, external asset ingestion, TTS, timeline/editor APIs, research,
library behavior, and the server-side ffmpeg render path.

The following could not be fully run without user data, external credentials,
or an installed provider/tool: `agent-brief`, `ai-agent-orchestrator`,
`ai-audio-editing`, `ai-scripting`, `ai-thumbnail-photo`, `ai-video-editing`,
`ai-workflow-dag`, `approve-script`, `create-project`, `edit-video`,
`external-results-ingestion` beyond its API smoke coverage,
`generate-script` with real providers, `hybrid-footage-director`,
`multi-format-campaign` beyond its offline API coverage,
`prompt-master-kling-veo-mj`, `review-video`, and `search-documents` against
the public network.

## Roadmap Gaps

The following are documented as planned but are not implemented as complete
production features yet:

- Full media rendering with source images/videos, voiceover/music mixing,
  transitions, and subtitle burn-in; the current ffmpeg renderer handles real
  WebM colour-card timelines with text overlays.
- Persistent on-disk job queue and restart recovery.
- Reference-video analysis into a style blueprint.
- Text-to-image, text-to-video, and image-to-video provider adapters.
- Multi-character dubbing, voice cloning, forced alignment, and loudness
  normalization.
- Advanced image editing and the planned professional video-editing features.
- MCP control, scheduled batch production, multi-user permissions, signed
  approval history, A/B hook measurement, and scheduled publishing.

## Full-Flow QA: Six War Projects With Real Video Rendering

A new reproducible driver, `scripts/qa_war_full_flow.py`, was added. Unlike the
earlier `qa_war_projects.ps1` (which validated lifecycle and timeline metadata
only), this driver produces a **real ffmpeg WebM for every project** and probes
each one with `ffprobe`. For each project it runs the complete flow:

    draft -> script_review -> script_approved -> generating ->
    video_review -> (self-edit) -> render -> video_approved -> published

Self-edit steps exercised: AI-assist (fit + beat sync), a scene polish, and
timeline normalize. Each rendered WebM was verified to be VP9 at 1080x1920 with
a non-trivial duration.

| # | Project | Scenes | Duration (s) | WebM size (B) | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | WWI Verdun | 6 | 45.0 | 1,115,443 | published |
| 2 | WWII Stalingrad | 6 | 45.0 | 990,167 | published |
| 3 | Vietnam Trail | 6 | 45.0 | 979,947 | published |
| 4 | Korean Pusan | 6 | 45.0 | 1,116,200 | published |
| 5 | Waterloo | 6 | 44.0 | 1,141,272 | published |
| 6 | Civil War Vicksburg | 6 | 44.0 | 1,139,346 | published |

Result: **6/6 passed**, all published with a probeable WebM. No code defect was
found in the render path during this run; the only wrinkle was the QA driver
itself needing to confirm `source_rights_confirmed` before the script-approval
gate (an intentional, mandatory human gate, not a bug).

## Recommended Order

1. Add or install the remaining heavy optional tools (faster-whisper, whisperx,
   demucs, rembg, TTS) only when implementing the corresponding feature, then
   add focused integration tests for each adapter.
2. Expand the ffmpeg renderer to consume source media, audio tracks, captions,
   and persistent render jobs before treating production video generation as
   complete.
3. Put the `yt-dlp` console script on `PATH` (or teach `toolcheck.py` to accept
   the importable package) so the inventory reflects the installed package.

The final test run emitted only upstream deprecation warnings from Starlette's
TestClient/httpx compatibility layer; no project test failed because of them.

## Media Studio & Content Re-Cook (universal media + AI re-purposing)

Built a universal media library and a full "xào nấu" (content re-cook) pipeline
so the operator can bring in any source media, let an AI agent read it, and
turn it into a new, distinct video.

### New backend modules

- `src/content_factory/media.py` — `MediaLibrary`: upload any video/audio/image/
  document, classify by extension, probe duration/resolution with ffprobe,
  transcribe video/audio with faster-whisper (CPU `base`), extract text from
  documents with pypdf, persist to `library/media/index.json`. Also
  `synthesize_music_bed()` for a royalty-free cinematic drone.
- `src/content_factory/recook.py` — `RecookPipeline`: read a source item,
  re-word the transcript (rule-based paraphrase: compress filler, restructure
  patterns, swap synonyms), and create a brand-new project in `script_review`
  with a fresh hook/CTA. Modes: `condense` / `expand` / `balanced`.
- New models: `MediaItem`, `MediaKind`, `TranscriptSegment`, `ReCookRequest`,
  `ReCookResult`.

### New API endpoints

`POST /media/upload`, `GET /media`, `GET /media/{id}`,
`GET /media/{id}/download`, `DELETE /media/{id}`,
`POST /media/{id}/transcribe`, `POST /media/{id}/extract-text`,
`POST /media/{id}/recook`, `POST /media/{id}/convert?target_format=mp4`.

### Media format conversion (integrated)

`POST /media/{id}/convert` converts any uploaded item to `mp4`, `webm` (video),
`mp3`, `wav` (audio), or `png`, `jpg` (image) via ffmpeg. The original is
preserved and a new sibling MediaItem is created. The Media Studio UI exposes a
Convert button with a format selector per item, so the operator can turn any
uploaded file into a Windows-playable MP4 (H.264 + AAC) directly in the system.
Conversion failures return HTTP 422 with the ffmpeg message.

### Render bug fixed (apostrophe in narration)

The 5-video re-cook QA revealed that inline `text='...'` in ffmpeg's drawtext
aborts with "Option not found" when narration contains an apostrophe (e.g.
"Napoleon's army" — Waterloo). `render_video_file` now writes each scene's text
to a temporary `textfile=` instead, which renders arbitrary narration reliably.
Added `test_render_handles_apostrophes_and_commas` as a regression lock.

### Real footage + full audio (voiceover + music)

The renderer was upgraded from silent colour cards to a real media render:

- **Moving source footage**: `render_video_file` gained a `background_video`
  mode that loops a source video as a continuously moving backdrop and overlays
  each scene's narration text at its own time window (`enable='between(t,…)'`).
  Re-cooked projects remember their source video (`Project.source_media_id`) and
  the service supplies it at render time (`_background_video_for`).
- **Voiceover**: per-scene narration (edge-tts) is mixed in at each scene's
  start time (`adelay` + `atrim`), so the re-cooked script is spoken aloud.
- **Music**: a royalty-free bed is synthesized (`synthesize_music_bed`) and
  mixed under the voiceover at the plan's music volume.
- **Output**: VP9 video + Opus audio in one WebM (verified by ffprobe), so a
  re-cooked video ships with a real soundtrack, not silence.
- Fixed a missing-comma bug between `setpts` and `drawtext` that broke the
  image-source path with "Option not found".
- Added `test_render_with_background_video_has_audio` as a regression lock.

### 5-video re-cook QA — all passed (real footage + full audio)

`scripts/qa_recook_5_videos.py` synthesizes 5 ~60s source videos (edge-tts +
ffmpeg), uploads each, transcribes with faster-whisper, re-cooks into a new
project, drives the two human gates + production + voiceover + render, and
publishes. Result: **5/5 passed**, each producing a real WebM with **VP9 video
(moving source footage) + Opus audio (voiceover + music)**:

| # | Topic | Transcript | Script | Duration | WebM |
| --- | --- | --- | --- | --- | --- |
| 1 | WWI Verdun | 76w | 87w | 39.4s | 1.20 MB |
| 2 | WWII Stalingrad | 74w | 88w | 41.3s | 1.25 MB |
| 3 | Vietnam Trail | 73w | 89w | 37.5s | 1.11 MB |
| 4 | Waterloo | 71w | 83w | 36.6s | 1.10 MB |
| 5 | Punic Wars | 68w | 81w | 36.2s | 1.12 MB |

(Durations now track the spoken narration length, so they are shorter than the
fixed 60s colour-card cut.)

### Frontend, skills, and MCP

- **Frontend**: added a "Media Studio" workspace (Key 8) to the studio — upload
  any file, browse the media grid, transcribe, re-cook, and view the AI reading.
- **Skills**: `.claude/skills/media-studio/` and `.claude/skills/content-recook/`.
- **MCP**: `mcp_server.py` exposes `media_list`, `media_upload`, `media_get`,
  `media_transcribe`, `media_extract_text`, `media_recook` as Model Context
  Protocol tools (stdio or SSE).

### Parallel-agent repairs

During this session a parallel agent contributed image/voice editing engines
(`image_engine.py`, `voice_engine.py`, `image_voice_service.py`) that arrived
mid-write and repeatedly broke the build. Repaired to keep the gates green:
PIL `Resampling` constants, pixel-access typing, missing return annotations,
a syntax error in `agent_tools.py`, a numpy broadcast bug in `duck_music`, and
`gate_db: None` now correctly disables the noise gate.

## AI Video Editor (can the AI really edit a video?)

`src/content_factory/ai_video_editor.py` implements the full test:

1. **Analyse** — sample frames and understand where content sits.
2. **Plan** — pick a natural position/size/time for an inserted image.
   - **No-vision** (`HeuristicPlanner`): gradient saliency → lowest-complexity
     cell in the lower two-thirds.
   - **With-vision** (`VisionPlanner`): a pluggable vision model proposes the
     placement; `_demo_vision_planner` stands in offline.
3. **Track** — KLT optical flow (`calcOpticalFlowPyrLK`) follows the insertion
   region; dense Farneback flow is the fallback.
4. **Composite** — feathered alpha-mask blending (mask-based, not a rigid
   overlay); RGBA images are straight-alpha flattened.
5. **Cut** — trims long near-static (dead-air) segments, capped at 50%.
6. **Export** — `final.mp4` (H.264 + preserved source audio).

API: `POST /ai-editor/edit` (multipart video+image, optional `use_vision`) →
report + `download_url`; `GET /ai-editor/output/{filename}` serves the edit.

QA: `scripts/qa_ai_video_editor.py` builds a clip with a moving subject and
runs both modes, asserting the MP4 has video + audio streams (**2/2 pass**).
Tests: `tests/test_ai_video_editor.py`.

Windows-safe image IO (`np.fromfile`/`imdecode`) and even working dimensions
were required because the workspace path contains non-ASCII characters
("Máy tính") and libx264+yuv420p need even heights.

## Latest Continuation

Implemented and verified the first real server-side render path:

- Added `src/content_factory/render.py` with an ffmpeg WebM renderer for
  timeline colour cards and text overlays.
- Added `POST /projects/{project_id}/render`; ffmpeg failures return HTTP 503
  with an actionable message.
- Added direct and API-level render tests; both create probeable WebM output.
- Added explicit Windows font discovery so drawtext does not depend on a
  missing Fontconfig installation.
- Fixed agent-tool JSON serialization for lists of models and preserved the
  required `source_rights_confirmed` flag in agent script updates.
- Fixed several pre-existing lint/test contract issues found by the fresh
  `.venv` run.

New in this continuation:

- Added the P1 regression test locking the `build_script_prompt(grounding=...)`
  signature and removed stale bytecode/test caches.
- Installed four lightweight optional tools (pillow, opencv-python-headless,
  moviepy, yt-dlp) and pinned `numpy` to `2.2.6` so mypy stays green.
- Added `scripts/qa_war_full_flow.py` and ran it: 6 distinct war projects each
  produced a real probeable VP9 WebM and reached `published`.

Remaining renderer work is source image/video compositing, voiceover/music
mixing, subtitle burn-in, and durable render progress/jobs.