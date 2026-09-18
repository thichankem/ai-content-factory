# MCP Servers — tool contract for AI agents

The AI Content Factory exposes its media library, editing, voice, and (optional)
vision capabilities to any MCP-capable agent (Claude, Codex, Gemini, DeepSeek,
…) through a single MCP server. This document is the contract: what tools exist,
what they do, and how they are confined.

> The server is intentionally **one process**, not one per media domain. Heavy
> media work (ffmpeg, image ops, TTS) lives in-process behind adapters, so there
> is no extra process to babysit and the pipeline degrades gracefully when a
> tool is missing (see `docs/TOOLCHAIN.md`).

## Running the server

```bash
python mcp_server.py          # stdio transport (default, for Claude Code etc.)
python mcp_server.py --sse    # SSE transport on :8765
```

Point your MCP client at `python mcp_server.py` (stdio). For SSE, use
`http://127.0.0.1:8765/sse`.

## Safety: the path sandbox

Every file the server reads or writes must resolve inside one of the configured
asset directories (`media_dir`, `uploads_dir`, `cache_dir`, `library_dir`),
enforced by `src/content_factory/sandbox.py`. An agent can never touch files
outside those roots — no roaming the host filesystem.

## Tool inventory

### Media library

| Tool | Purpose |
| ---- | ------- |
| `media_list()` | List every item in the universal media library. |
| `media_upload(path, language?)` | Upload a local file (inside the sandbox) into the library. |
| `media_get(media_id)` | Fetch one item including its AI reading (transcript/text). |
| `media_transcribe(media_id, language?)` | Transcribe a video/audio item (cached by content hash). |
| `media_extract_text(media_id)` | Extract plain text from a document item. |
| `media_recook(media_id, new_title, …)` | Re-cook an item into a brand-new project + re-worded script. |

### Image editing

| Tool | Purpose |
| ---- | ------- |
| `image_crop(media_id, left, top, width, height, out)` | Crop an image to a fixed box. |
| `image_remove_background(media_id, out, tolerance?)` | Chroma-key background removal. |
| `image_upscale(media_id, scale, out)` | Upscale an image (Lanczos). |

### Video editing

| Tool | Purpose |
| ---- | ------- |
| `video_cut_clip(media_id, start_seconds, end_seconds, out)` | Cut a clip (ffmpeg stream copy). |
| `video_concat_clips(media_ids, out)` | Concatenate clips in order. |
| `video_detect_scene_cuts(media_id, threshold?)` | Detect scene cuts (non-vision histogram). |
| `video_score_best_frame(media_id, top_k?)` | Score frames and return the best timestamps. |

### Voice / TTS

| Tool | Purpose |
| ---- | ------- |
| `voice_synthesize_speech(text, language?, out?, pitch?)` | Synthesize speech (edge-tts → gTTS fallback). |

### Audio perception (optional "hearing")

These tools let an agent *hear* a soundtrack, not just read its transcript.
Three run free with a deterministic non-AI backend (numpy + ffmpeg); four
need an AI backend and return a clear error until one is wired in — see
`docs/PERCEPTION-LAYER.md`.

| Tool | Purpose | Backend |
| ---- | ------- | ------- |
| `audio_detect_silence_and_pace(media_id)` | Silent gaps + coarse speaking pace. | non-AI (free) |
| `audio_classify_music_mood(media_id)` | Coarse mood (energy / centroid / tempo). | non-AI (free) |
| `audio_check_quality(media_id)` | Clipping, DC offset, noise floor, peak. | non-AI (free) |
| `audio_detect_events(media_id)` | Sound events (applause, bells, music swell). | AI (PANNs/YAMNet) |
| `audio_diarize_speakers(media_id)` | "Who speaks when". | AI (pyannote) |
| `audio_detect_speech_emotion(media_id)` | Dominant emotion in the voice. | AI (SER model) |
| `audio_describe_scene(media_id)` | Natural-language description of the soundtrack. | AI (audio-capable LLM) |

## Contract check

CI runs `scripts/mcp_healthcheck.py --smoke` (`.github/workflows/mcp-contract-check.yml`)
on every PR: it boots the server in-process, lists every tool, and fails if any
tool is missing a name, description, or JSON-Schema input — so a PR that breaks
the contract fails the build instead of shipping a broken tool to agents.

## Design notes

- **Orchestrator never does media itself.** The agent plans, calls the right
  tool, checks the result, and decides the next step; ffmpeg / image / TTS /
  vision work happens inside the server.
- **Vision is opt-in.** `video_detect_scene_cuts` and `video_score_best_frame`
  default to cheap non-vision heuristics. Enable the vision layer only when a
  task must "understand" a frame — see `docs/VISION-LAYER.md`.
- **Audio perception is opt-in too.** Silence/pace, music mood and technical
  quality always run free; event detection, diarization, emotion and scene
  description need an AI backend. See `docs/PERCEPTION-LAYER.md` for when to
  pay for "hearing" and how to fall back to non-AI.
- **Idempotent checkpoints.** Transcription is memoized by content hash in
  `storage/cache/`, so a retried run resumes instead of recomputing.
- **Two human gates stand.** Nothing here auto-confirms source rights or skips
  the script/video approval gates; that invariant is enforced upstream in the
  service layer.