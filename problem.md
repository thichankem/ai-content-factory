# Problem Report

Updated: 2026-09-18

## Latest Full Test Run (2026-09-18)

A complete re-test of the whole system was run on this date. **Every gate is
green** — the current state is healthy. Two real defects were found and fixed,
and two non-blocking issues remain (documentation drift + a tooling edge case).

| Check | Result | Notes |
| --- | --- | --- |
| `python -m pytest -q` | PASS | **919 passed**, 16 upstream deprecation warnings, ~146 s. |
| `python scripts/smoke.py --port <fresh>` | PASS | **64 end-to-end checks** passed on a fresh server. |
| `python -m ruff check src tests` | PASS | All checks passed (0 findings). |
| `python -m ruff format --check src tests` | PASS | 183 files already formatted. |
| `python -m mypy src` | PASS | 0 issues in 129 source files. |
| `python scripts/frontend_imports.py` | PASS | clean, 98 files. |
| `cd frontend && npm run type-check` | PASS | `tsc --noEmit` clean. |
| `cd frontend && npm run build` | PASS | Next.js 14.2.35 build succeeded. |

### Fixed this run

1. **P1 — syntax error broke `photo_compositor.py` (module could not import).**
   `src/content_factory/photo_compositor.py` had a duplicated `def blend_images(`
   line (lines 85–86), producing `invalid-syntax: Expected ')', found newline`
   and `Expected an indented block after function definition`. This made the
   whole module unparseable and would have failed any import of the package.
   Removed the duplicate line; the module now imports cleanly (26 blend modes).
   This was the only syntax-level defect found.
2. **P2 — mypy type errors (fixed).**
   - `photo_compositor.py:49` and `:61` — `Returning Any from function declared
     to return "ndarray"` in `_saturation_of` and `_soft_light` (numpy `.max()/
     .min()` and scalar arithmetic return `Any` under the installed stubs).
     Wrapped both returns in `np.asarray(...)` (behavior-preserving, no copy).
   - `models/audio.py:123` — `default_factory=lambda` returned `list[str]` where
     the field type is `list[Literal["vocals","drums","bass","other"]]`. Replaced
     the lambda with a typed module-level `_default_stems()` function.
   After these fixes `mypy` reports 0 issues across all 129 source files, and the
   full 919-test suite plus the 64-check smoke test still pass.

### Remaining / non-blocking issues

3. **Documentation drift — `README.md` *Status* table is stale.** It still
   claims the Python gates are red (242 `ruff` findings, 13 unformatted files,
   43 `mypy` errors in 7 files, 11 `pytest` failures). Re-measured on this date
   all four are green (`ruff` 0, format 0, `mypy` 0, `pytest` 919/919 pass).
   The table contradicts the actual state and should be updated to avoid
   misleading future agents. **Action:** refresh the *Status* table in
   `README.md`.
4. **Tooling edge case — `scripts/smoke.ps1` does not forward a `--port` arg.**
   When a server is already listening on `:8080`, `smoke.py` reuses it and prints
   `[!!] reusing the server already listening on http://127.0.0.1:8080; pass
   --port <free-port> to test the current code`. During this run a stale server
   on `:8080` reset the connection on `GET /library` (`ConnectionResetError:
   [WinError 10054]`), which looked like a smoke failure but was purely the dead
   reused server. Running `smoke.py --port <fresh>` against the current code
   passed 64/64. **Action:** forward `--port` through `smoke.ps1` (and/or detect
   a stale listener) so the wrapper always tests the current code on a fresh
   port.
5. **Informational — 16 upstream deprecation warnings.** From `starlette`
   (`anyio.abc.BlockingPortal` alias), `torch`/`easyocr` (`torch.ao.quantization`
   and quantized-tensor deprecations), and `Pillow` (`mode` param). None are
   project defects and none fail a test.

## NotebookLM-style Knowledge Q&A (added 2026-09-18)

The RAGFlow-style knowledge engine already existed (chunking, hybrid retrieval,
grounding), but it could only *retrieve* — it could not answer a question with
citations the way Google NotebookLM does. Added the missing layer:

- **`POST /kb/{id}/ask`** — grounded Q&A. Retrieves the top chunks, hands the
  grounded context to the provider chain, and returns a synthesized answer whose
  claims carry `[n]` citations back to the sources. Supports a `history` of prior
  turns for follow-up questions. When no provider is configured it falls back to
  an **offline extractive answer** from the top hits (never fails on a missing
  API key); `grounded` distinguishes the two.
- **`POST /kb/{id}/ingest-url`** — add a web page as a source (NotebookLM
  "add a web source"). Fetches the URL, strips markup, chunks it with the KB's
  template. An unreachable/unreadable page is recorded as a `FAILED` document
  rather than aborting the request.
- **Agent tools + MCP**: registered `kb_ask` and `kb_ingest_url` in the tool
  registry (now 74 tools), reachable through `POST /tools/call` and through the
  MCP server's `factory_call_tool`. The handlers live in a new
  `agent_knowledge.py` module so `agent_tools.py` stays under its line budget.
- **Models**: `KBAskRequest`, `KBAskResponse`, `KBTurn`, `KBIngestUrl`.
- **Tests**: `tests/test_knowledge_qa.py` (10 tests) and
  `tests/test_mcp_connectivity.py` (4 tests).
- **Live MCP check**: `scripts/test_mcp_live.py` spawns the real `mcp_server.py`
  over stdio, connects with a genuine MCP client, and round-trips a tool call —
  **MCP LIVE CONNECTIVITY OK** (23 MCP tools, `kb_ask`/`kb_ingest_url` present).

Verification: full pytest suite green, `ruff` + `format` + `mypy` all clean.

## YouTube Search & Download (added 2026-09-18)

Added native YouTube search and download to the media library, so an operator
(or an AI agent) can find reference videos and pull them into the pipeline.

- **`GET /youtube/search?q=...&limit=N`** — search YouTube by query (metadata
  only, no download). Backed by yt-dlp's `ytsearch` extractor, so search and
  download agree on what a video is. Returns `YouTubeSearchResult`s (id, title,
  url, duration, uploader, thumbnail, description, view_count). Empty query → 422.
- **`POST /youtube/download`** — download a YouTube video (by URL or id) into the
  media library, reusing the existing `download_from_url` path (yt-dlp, with an
  ffmpeg/urllib fallback). Supports `extract_audio` for audio-only grabs.
- **Agent tools + MCP**: registered `youtube_search` and `youtube_download`
  (registry now 76 tools), reachable through `POST /tools/call` and the MCP
  server's `factory_call_tool`. Handlers live in a new `agent_youtube.py` module
  so `agent_tools.py` stays under its line budget.
- **Models**: `YouTubeSearchResult`, `YouTubeSearchRequest`,
  `YouTubeSearchResponse`, `YouTubeDownloadRequest`.
- **Tests**: `tests/test_youtube.py` (9 tests).

Live verification over the real network:
- `GET /youtube/search?q=morning+light+city` returned 3 real videos (titles,
  uploaders, URLs).
- `POST /youtube/download` (audio-only) pulled "Rick Astley - Never Gonna Give
  You Up" into the library: 3.4 MB webm, 213 s, `kind=video`.
- Full pytest suite green (943 tests), `ruff` + `format` + `mypy` clean, smoke
  64/64, MCP live connectivity OK.

## YouTube Transcript — "by any means" (added 2026-09-18)

Getting a transcript from a downloaded video now works **by any means**, in a
two-strategy cascade that never blocks on a missing model:

1. **Existing subtitles/captions (Strategy 1, instant & free).** For any video
   pulled from a YouTube URL, `MediaLibrary.fetch_subtitles` reuses the video's
   own manual or auto-generated captions via yt-dlp — no ML model, no download
   of the full video, milliseconds. `POST /media/{id}/transcribe` now tries this
   first for YouTube-sourced items (before the file check, since subtitles only
   need the source URL).
2. **faster-whisper (Strategy 2, local speech-to-text).** If no captions exist,
   the audio is downloaded and transcribed locally with faster-whisper (already
   installed, CPU-capable).

New surface:
- **`POST /youtube/transcript`** — `{url, language}` → `YouTubeTranscriptResult`
  with `source` (`subtitles` or `whisper`), `text`, `segments`, and `media_id`
  (set only when the whisper path downloaded audio).
- **`MediaLibrary.transcribe_youtube(url, language)`** — the cascade, returns the
  same shape.
- **Agent tool + MCP**: `youtube_transcript` registered (registry now 77 tools),
  reachable via `POST /tools/call` and MCP `factory_call_tool`.
- **Models**: `YouTubeTranscriptRequest`, `YouTubeTranscriptResult`.
- **Tests**: `tests/test_youtube.py` grew to 16 tests (VTT parsing, subtitle
  reuse, whisper fallback, API, agent tool).

Live verification: `transcribe_youtube(".../watch?v=dQw4w9WgXcQ", "en")` returned
`source=subtitles` with the full auto-captioned lyrics instantly (no model run).
Full pytest suite green (**949 tests**), `ruff` + `format` + `mypy` clean, MCP
live connectivity OK.

## Noise Reduction — spectral gating (added 2026-09-18)

Real "remove noise" for voice/audio, in pure numpy (no heavy dependencies). The
existing `_noise_gate` only silenced quiet gaps; the new **spectral gating**
suppresses broadband noise (hiss, hum, room tone) that sits *under* the speech —
the Audacity/Audition "DeNoise" behaviour.

Core engine (`voice_engine.py`):
- `_stft` / `_istft` — Hann-window STFT with a **50% overlap** so the overlap-add
  reconstructs cleanly (a non-COLA hop produced edge transients; those are also
  guarded by zeroing samples where the window-overlap sum is too small).
- `_spectral_gate(samples, sr, strength, noise_profile)` — learns the noise
  spectrum from a pure-noise sample or auto-estimates it from the quietest 10%
  of frames, then applies a Wiener-style per-bin gain: speech bins (mag ≫ noise)
  keep ~1, noise bins collapse. Output is peak-normalised so it never clips.
- `denoise_audio(data, strength, noise_profile, export_format)` — the end-to-end
  decode → gate → encode path, returning `(bytes, report)` with `method`,
  `strength`, `noise_profile`, `input/output_peak`.
- `process_voice` gained `denoise_strength` (and a `noise_profile` param), so the
  existing enhance chain can denoise; a `"denoise"` preset was added.

Surface:
- **Service** `audio_denoise(ref, strength, noise_profile_ref, format)` in
  `MediaToolsMixin` — resolves a media/edited asset, optionally a second asset as
  the noise profile, persists the result under `library/edited/`.
- **Agent tool + MCP**: `audio_denoise` registered (registry now 78 tools), in a
  new `agent_audio.py` module so `agent_tools.py` stays under its line budget.
- **Tests**: `tests/test_denoise.py` (7 tests) — tone-preservation/noise-suppression
  on a synthetic 220 Hz tone buried in noise, report shape, auto-estimation,
  `process_voice` with `denoise_strength`, preset registration, agent dispatch.

Verified on a synthetic tone+noise signal: the 220 Hz tone keeps ~93% of its
energy while the broadband noise collapses and the output error to the clean tone
drops by ~34%; output never clips. Full pytest suite green (**956 tests**),
`ruff` + `format` + `mypy` clean, smoke 64/64, MCP live connectivity OK.

## Wiring into the product (added 2026-09-18)

The YouTube, transcript and noise-reduction features are now reachable from the
studio and from the re-cook pipeline, not just the API/agent tools.

**Backend chain additions:**
- **Auto-denoise in re-cook.** `ReCookRequest` gained `denoise` (bool) and
  `denoise_strength` (0–1). `RecookPipeline.prepare_source` now, when
  `denoise=True` and the source is video/audio, spectrally denoises the audio
  *before* transcribing it (via `voice_engine.denoise_audio` + a new
  `MediaLibrary.transcribe_file` that runs faster-whisper on an arbitrary audio
  file). So a noisy recording yields a cleaner transcript and a better re-cook.
- **Auto-transcribe after YouTube download.** `YouTubeDownloadRequest` gained
  `auto_transcribe`; `youtube_download` transcribes the item right after pulling
  it (subtitles first, then faster-whisper).
- Refactor: `MediaLibrary.list` renamed to `list_items` (it shadowed the builtin
  `list` type in annotations); `_run_whisper` extracted from `transcribe`.

**Frontend (vanilla studio, `frontend/`):**
- **YouTube panel** in Media Studio: search by keyword → list results (title,
  uploader, duration) → **⬇ Tải** (with an "auto-transcribe" checkbox) and
  **📜 Transcript** buttons per result.
- **Transcript display**: a "📜 Transcript" button on YouTube-sourced media cards
  fetches `/youtube/transcript` and shows the text (with source + word count);
  the detail view already shows the AI reading.
- **🎛 Giảm ồn** button on every video/audio media card opens a modal with a
  **strength slider** and an optional **noise-profile dropdown** (picks another
  audio/video asset as the pure-noise sample); it calls the `audio_denoise` tool
  via `/tools/call` and saves the result to Edited Assets.

Verified live over HTTP: `/youtube/search` (2 results), `/youtube/transcript`
(source=subtitles, 2089 chars), upload + `audio_denoise` via `/tools/call`
(method=spectral_gating, asset created). Smoke 64/64, `node --check` clean.

## Audio Editor panel (added 2026-09-18)

A dedicated **Audio Editor** in Media Studio so the operator can edit any
audio/video asset without leaving the UI. It drives the existing audio tools via
`/tools/call` and saves every result to Edited Assets.

Pick an audio/video asset, then:
- **✂ Trim** — cut to a start/end range (`audio_trim`).
- **🌊 Fade** — fade in/out (`audio_fade`).
- **🔊 Normalize** — loudness to a target LUFS (`audio_normalize`).
- **⏩ Retime** — tempo change without pitch shift (`audio_retime`).
- **🎛 Giảm ồn** — spectral denoise with a strength slider (`audio_denoise`).
- **🥁 Beat/BPM** — detect tempo + beat/downbeat grid (`music_beat_grid`).
- **🎵 Mix với nhạc nền** — mix the voice track with a chosen music-bed asset at a
  set gain, with ducking (`audio_mix`).
- **🎞 Tách audio** — pull the soundtrack out of a video (`extract_audio_track`).

Each action shows the resulting asset id, duration, and a download link. The
panel lives in `frontend/index.html` + `frontend/app.js`
(`loadAudioEditor`, `aeCall`, `setupAudioEditorListeners`).

Verified live over HTTP: all eight audio tools return 200 and produce an asset —
trim, fade, normalize, retime, denoise, extract, beat grid (BPM 163, 4 beats on a
synthetic tone), and mix. Smoke 64/64, `node --check` clean, `ruff`/`mypy` clean.

## Download any audio clip (added 2026-09-18)

A way to pull **any audio** (or a specific clip of it) into the library from a URL.

- **`POST /media/audio-clip`** — `{url, start_seconds, end_seconds, language}`.
  Downloads the audio from any URL (YouTube, podcast, direct MP3, SoundCloud,
  etc.) with `extract_audio=True`, and when a valid `end_seconds > start_seconds`
  range is given, trims it to that range and registers the clip as its own media
  item. Backed by `MediaMixin.download_audio_clip` (reuses `media_from_url` +
  `media_tools.trim_audio`).
- **Agent tool + MCP**: `download_audio_clip` registered (registry now 79 tools).
- **UI**: a "⬇ Tải bất kỳ đoạn âm thanh từ URL" box at the top of the Audio
  Editor — paste any URL, optionally set a start/end range, and hit **⬇ Tải
  audio** (full) or **✂ Tải đoạn (clip)**.

Verified live over HTTP: `POST /media/audio-clip` with a real YouTube URL and
`start=30, end=40` returned a 10-second `clip_Rick_Astley_...webm` item. Smoke
64/64, `node --check` clean, `ruff`/`mypy` clean.

## Media database (added 2026-09-18)

Turned the media library into a proper queryable **database** for all audio,
images, videos and documents — not just a flat list.

- **`MediaItem.tags`** — items can carry tags (normalised: stripped, lowercased,
  de-duped).
- **`MediaLibrary.query(...)`** — rich filtering by `kind`, `tag`, free-text
  `q` (over filename + transcription + text_content + source + tags), `source`,
  `min_duration`/`max_duration`, `date_from`/`date_to`, and `sort`
  (newest|oldest|name|size|duration).
- **Tag management** — `set_tags`/`add_tag`/`remove_tag`/`all_tags`.
- **`stats()`** — aggregate counts by kind, total bytes, and the tag list.
- **Endpoints**:
  - `GET /media` now accepts all the filter query params above.
  - `GET /media/stats`, `GET /media/tags`.
  - `POST /media/{id}/tags`, `POST /media/{id}/tags/{tag}`,
    `DELETE /media/{id}/tags/{tag}`.
- **UI (Media Studio)**: a filter bar (kind / tag / sort dropdowns + Lọc button),
  a live stats line (item count, MB, counts by kind), and a **🏷 Tag** button on
  every media card.

Verified: query by tag/kind/free-text, tag CRUD, stats and all-tags all work over
HTTP. Smoke 64/64, `node --check` clean, `ruff`/`mypy` clean.

## Cloud media storage (added 2026-09-18)

The media database can now be **cloud-backed** (S3-compatible object storage)
while staying fully local by default.

- **`src/content_factory/cloud.py`** — a pluggable `MediaStorage` backend:
  - `LocalMediaStorage` — files under a root dir (the default).
  - `S3MediaStorage` — S3-compatible via `boto3` (lazy import; keys map to
    `<prefix>/media/<id>/<filename>` in the bucket).
  - `MemoryMediaStorage` — in-memory, for tests.
  - `build_media_storage(...)` — picks S3 when a bucket is configured, else local.
- **`MediaLibrary`** now takes an optional `storage` backend. The local
  `media_dir/files/` stays the working cache for in-place processing (ffmpeg,
  transcription, trimming), while the *authoritative* copy lives in the backend:
  uploads are written to storage, and `path_for` fetches the object back into the
  local cache when it is missing. `delete` removes from storage too.
- **Config** (`Settings`): `s3_bucket`, `s3_endpoint`, `s3_region`,
  `s3_access_key`, `s3_secret_key`, `s3_prefix`. Set `s3_bucket` (+ install
  `boto3`) to go cloud; leave empty for a purely local library.
- **Tests**: `tests/test_cloud.py` (7 tests) — local/memory CRUD, `path_for`
  fetch-back, backend selection, and S3 delegation against a mocked boto3 client.

Verified: upload → storage, `path_for` fetch-back, delete-from-storage all work
against the in-memory backend; S3 path delegates correctly (mocked). Smoke 64/64,
`ruff`/`mypy` clean.

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