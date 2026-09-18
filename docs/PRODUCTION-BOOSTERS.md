# Production Boosters — ducking, virality, thumbnails

Small, high-value helpers that make finished videos feel professional without
heavy models. Implemented in `src/content_factory/audio.py`, `virality.py`,
`thumbnail.py`.

## Auto music ducking — `audio.py`

Automatically lowers the background music whenever there is speech, so the
voiceover is never buried. Uses ffmpeg's `sidechaincompress` (sidechain = voice
drives the gain reduction on the music).

```python
from content_factory.audio import duck_music_under_speech, DuckSettings

out = duck_music_under_speech(
    "music.mp3", "voiceover.mp3", "mixed.mp3",
    settings=DuckSettings(duck_level_db=-12.0, attack_ms=20, release_ms=300),
)
```

## Virality scorer — `virality.py`

A pre-publish heuristic that scores how likely a script is to hold attention —
an early warning instead of discovering after posting. No platform data needed.

```python
from content_factory.virality import score_virality

result = score_virality(script, duration_seconds=45, hook="You won't believe this")
print(result.score, result.warnings)   # 0-100 + warnings like "hook too long"
```

Factors: hook strength (short, curiosity-driven opening), pace (words/minute
vs 130–170 ideal), length fit (30–90s for shorts), and a call-to-action.

## Auto thumbnail + CTR heuristic — `thumbnail.py`

Picks the strongest frames (via `vision.score_best_frame`), optionally draws a
text overlay, and predicts a click-through rate to pick the best candidate.

```python
from content_factory.thumbnail import generate_thumbnails

candidates = generate_thumbnails("final.mp4", "thumbs/", top_k=3,
                                 overlays=("Watch till the end",))
best = candidates[0]   # sorted by ctr_prediction descending
```

## Configuration

```ini
# No dedicated flags; ducking/thumbnail take their params as arguments.
# Virality is purely a function of the script + duration.
```

## Guardrail

Ducking and thumbnails are deterministic transforms. The virality score is a
*heuristic advisory* — it never auto-publishes or auto-confirms rights; the two
human gates still stand.