# Vision Layer — when to pay for "understanding" a frame

The same task runs in two modes: a cheap **non-vision heuristic** (no model, no
GPU, no API cost) and an optional **vision mode** (a model that understands
content). The calling code does not change — you swap the backend, not the call.

> **Sibling layer:** audio perception (`docs/PERCEPTION-LAYER.md`) applies the
> exact same dual-mode idea to the *soundtrack* (silence, music mood, sound
> events, speakers, emotion). Vision understands frames; audio perception
> understands sound.

This is deliberate: mechanical work (cut by timestamp, composite by template,
detect a hard cut) never needs vision, and paying a vision model for every
frame is wasteful.

## The two seams

Both live in `src/content_factory/vision.py`.

| Task | Non-vision (default) | Vision (opt-in) |
| ---- | -------------------- | --------------- |
| Shot boundaries | `detect_scene_cuts()` — HSV/grayscale histogram + pixel-diff via OpenCV | (same boundary math; vision adds *semantic* scene choice) |
| Best frame | `HeuristicSceneScorer` — sharpness (Laplacian), exposure, saturation | `VisionSceneScorer` protocol — a model that rates content |

`build_scorer(settings, vision_scorer)` returns the heuristic unless
`enable_vision` is on **and** a vision scorer is wired in.

## Configuration

```ini
# Off by default — mechanical tasks never spend vision cost.
CONTENT_FACTORY_ENABLE_VISION=false
# rule_based | claude | local
CONTENT_FACTORY_VISION_BACKEND=rule_based
```

- `rule_based` — `HeuristicSceneScorer` (free, deterministic).
- `claude` / `local` — plug a `VisionSceneScorer` implementation (multimodal LLM
  or a local YOLO/CLIP model). The seam is the protocol; wire the backend in
  `build_scorer` without touching the call sites.

## Cost discipline

- Default to non-vision. Only enable vision when the task genuinely needs to
  "understand" content (e.g. pick the most expressive highlight frame, choose a
  b-roll that matches the script).
- Sample frames (`sample_every`) and score a subset, not every frame.
- Cache vision results by content hash (`storage/cache/`) so the same input is
  never rescored.

## Example flow: auto highlight

1. `video_detect_scene_cuts(media_id)` → raw shot boundaries (non-vision, free).
2. *(Optional, vision on)* `video_score_best_frame(media_id, top_k)` with a
   `VisionSceneScorer` → pick the strongest frame per scene, drop blurry/underexposed.
3. `video_cut_clip` + `video_concat_clips` → assemble the highlight.
4. `voice_synthesize_speech` + `media_transcribe` → narration/subtitles.

Steps 1, 3, 4 run without vision; only step 2 spends vision cost, and only when
enabled.