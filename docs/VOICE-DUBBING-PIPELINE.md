# Voice Dubbing Pipeline — STT → translate → TTS → align → mux

How the factory turns an original-language video into a dubbed one while
keeping the timing and emotional tone intact. This is the "lồng tiếng"
capability (requirement 4/6 of the master plan) viewed as an end-to-end
pipeline, not a single TTS call.

> Status: partially planned. Today the factory has TTS (`src/content_factory/tts.py`,
> edge-tts → gTTS) and STT (`media_transcribe`, faster-whisper). Translation,
> voice cloning, forced alignment and final muxing are the remaining stages.

## The five stages

```
 original audio/video
        │
  1. STT ───────────────► transcript (text)          [media_transcribe]
        │
  2. TRANSLATE ─────────► target-language script     [provider chain / agent]
        │
  3. TTS ───────────────► new voiceover audio        [voice_synthesize_speech]
        │
  4. ALIGN ─────────────► per-segment timing         [dub_align]
        │
  5. MUX ───────────────► dubbed video (audio swap)  [ffmpeg renderer]
```

Each stage must (a) read config from preset/env, (b) write a reviewable
artifact, (c) be re-runnable without breaking earlier stages, and (d) have an
offline escape hatch.

## How perception feeds dubbing

The optional audio-perception layer (`docs/PERCEPTION-LAYER.md`) makes the dub
*smarter*:

- `audio_detect_silence_and_pace` → land each dubbed line on a natural pause.
- `audio_classify_music_mood` + `audio_detect_events` → don't bury a music swell
  or an important sound effect under the new voice.
- `audio_diarize_speakers` → when several people speak, dub each character
  separately instead of mixing voices.
- `audio_detect_speech_emotion` → carry the original emotional tone into TTS so
  the dub isn't flat.

None of these are required for a basic dub; they are quality upgrades.

## Stage details

### 1. STT — speech to text
`media_transcribe(media_id, language)` (faster-whisper), memoized by content
hash in `storage/cache/`. Output: a transcript with approximate word/timestamp
data usable as a first alignment hint.

### 2. Translate
Reuse the provider chain (`src/content_factory/providers.py`) or an external
agent via the bridge (`docs/AGENT-BRIDGE.md`). Output: a target-language script
with one segment per source segment, preserving line boundaries so timing maps
cleanly.

### 3. TTS
`voice_synthesize_speech(text, language, pitch)` (edge-tts → gTTS). For cloned
voices (planned), a voice-clone backend (XTTS-v2 / F5-TTS) replaces the stock
neural voice. Emotional tone from perception can be passed as a hint.

### 4. Align — forced alignment
Match each translated line to a time range on the original. Two approaches:
- **Duration-based (today):** `tts.py` measures real audio duration (mutagen)
  and the timeline scales scene slots to fit — good enough for single-narrator.
- **Forced alignment (planned):** whisperX-style word-level alignment so
  multi-character dubs and precise lip-sync work.

### 5. Mux
`ffmpeg` swaps the original voice track for the new one (or mixes it under the
music/SFX bed at the right gain). The renderer (`src/content_factory/render.py`)
consumes the timeline render plan.

## Configuration

```ini
CONTENT_FACTORY_TTS_ENABLED=true
CONTENT_FACTORY_TTS_ENGINE=edge        # edge | gtts | off
#CONTENT_FACTORY_TTS_VOICE=vi-VN-HoaiMyNeural
CONTENT_FACTORY_TTS_RATE=+0%
```

## Guardrails

- **Never auto-confirm source rights.** Translating/dubbing a source is not
  permission to redistribute it; the two human gates (script + final video)
  still stand.
- **Learn, don't copy.** The dub carries the *meaning and timing* of the source,
  not its original audio or a cloned voice without consent.