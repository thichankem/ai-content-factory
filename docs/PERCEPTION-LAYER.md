# Perception Layer — when to pay for "understanding" content

The factory has two perception layers that let an agent *understand* content
rather than just transform it. Both follow the same rule: a cheap, deterministic
**non-AI** backend runs everywhere, and an optional **AI** backend is swapped in
only when a task genuinely needs to understand meaning. The calling code does
not change — you swap the backend, not the call.

- **Vision** (see `docs/VISION-LAYER.md`) — understanding *frames*.
- **Audio perception** (this doc) — understanding the *soundtrack*: not just
  "what words were said" (that is STT in `voice_mcp`/`media_transcribe`), but
  the music, sound effects, silences, who is speaking, and emotional tone.

## Why "perception" ≠ "processing"

`image_mcp` / `video_mcp` / `voice_mcp` are **deterministic transforms** — they
always run. Perception is **interpretation** — it is optional, costs money when
an AI backend is on, and should be switched off for mechanical work.

## Audio perception tools

Implemented in `src/content_factory/perception.py`; exposed as MCP tools in
`mcp_server.py` (see `docs/MCP-SERVERS.md`).

| Tool | What it answers | Non-AI (default, free) | AI (opt-in) |
| ---- | --------------- | ---------------------- | ----------- |
| `detect_silence_and_pace` | Where are the gaps? How much talking vs dead air? | RMS-energy framing + threshold | — |
| `classify_music_mood` | Is the bed music energetic / calm / ambient? | energy + spectral centroid + tempo heuristic | CLAP / audio-LLM for a semantic tag |
| `check_audio_quality` | Clipping, DC offset, noise floor, peak? | numpy spectral analysis | — |
| `detect_audio_events` | Applause, a bell, glass breaking, a music swell? | — | PANNs / YAMNet |
| `diarize_speakers` | Who speaks when? | — | pyannote-audio |
| `detect_speech_emotion` | Urgent / sad / excited voice? | — | speech-emotion-recognition model |
| `describe_audio_scene` | A natural sentence about the whole soundtrack | — | audio-capable multimodal LLM |

## Configuration

```ini
# Off by default — mechanical tasks never spend perception cost.
CONTENT_FACTORY_ENABLE_AUDIO_PERCEPTION=false
# rule_based | ai
CONTENT_FACTORY_AUDIO_PERCEPTION_BACKEND=rule_based
```

- `rule_based` — silence/pace, music mood and quality run free; the AI-only
  tools return a clear "backend not wired" error.
- `ai` — attach AI backends (event detector, diarizer, emotion analyzer, scene
  describer) in `build_audio_perception(...)` without touching the MCP call
  sites. The seam is the Protocol; wire the backend, keep the call.

## Important: Claude does not accept audio input today

Claude's API does not yet take raw audio, so the `describe_audio_scene` /
`detect_audio_events` / `diarize_speakers` / `detect_speech_emotion` backends
must be a model that actually ingests audio (e.g. Gemini, or a self-hosted
Qwen2-Audio / PANNs / pyannote). Claude stays the orchestrator that decides and
reads the returned text — it just delegates the "hearing" step to that backend.

## Cost discipline

- Default to non-AI. Only enable the AI backends when the task genuinely needs
  to understand the soundtrack.
- Cache perception results by content hash (`storage/cache/`) so the same input
  is never re-analyzed.
- Sample frames / audio windows, don't analyze every millisecond.

## Example flow: auto-dub that respects the original audio

1. `voice_mcp.transcribe_audio` → the spoken lines (text).
2. `audio_detect_silence_and_pace` → where the gaps are, so the dub lands on
   natural pauses.
3. *(Optional, AI on)* `audio_classify_music_mood` + `audio_detect_events` →
   know when music swells or an important sound effect occurs, so the dubbed
   voice never buries it.
4. *(Optional, AI on)* `audio_diarize_speakers` → if multiple people speak,
   translate/dub each character separately instead of mixing voices.
5. *(Optional, AI on)* `audio_detect_speech_emotion` → carry the original
   emotional tone into `voice_mcp.synthesize_speech` so the dub doesn't read
   flat.
6. `voice_mcp.synthesize_speech` + `dub_align` → mux the new voice over the
   original at the right timings.

Steps 1, 2, 6 run without any perception cost; steps 3–5 spend it only when
enabled.