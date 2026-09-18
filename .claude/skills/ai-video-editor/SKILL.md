---
name: ai-video-editor
description: >
  Prove an AI can really edit a video: analyse a clip, pick a natural spot to
  insert an image, track it across frames with optical flow, composite it with a
  feathered mask, cut redundant segments, and export final.mp4. Works with or
  without a vision model.
allowed-tools:
  - Read
  - Write
  - Bash
---

# AI Video Editor

Answers the "can the AI really edit a video?" test end-to-end.

## Pipeline (`src/content_factory/ai_video_editor.py`)

1. **Analyse** — sample frames, understand where content sits.
2. **Plan** — pick a natural position + size + time window for the inserted
   image. Two planners:
   - **HeuristicPlanner** (no vision): gradient saliency → lowest-complexity
     cell in the lower two-thirds.
   - **VisionPlanner** (with vision): a vision model describes the scene and
     proposes a placement. Plug one in by passing it to `AiVideoEditor(vision=...)`.
3. **Track** — KLT optical flow (`calcOpticalFlowPyrLK`) follows the insertion
   region so the image moves with the camera/subject; dense Farneback flow is
   the fallback when features are lost.
4. **Composite** — feathered alpha mask blending (mask-based, not a rigid
   overlay). RGBA images are straight-alpha flattened first.
5. **Cut** — trims long near-static (dead-air) segments into a clean timeline,
   capped so it never removes more than half the clip.
6. **Export** — writes frames and muxes with ffmpeg to `final.mp4` (H.264 +
   preserved source audio).

## Usage

```python
from content_factory.ai_video_editor import AiVideoEditor
editor = AiVideoEditor()                      # heuristic (no vision)
report = editor.edit(video_path, image_path, output_path)
print(report.planner, report.placement, report.cuts)
```

With a vision model:

```python
editor = AiVideoEditor(vision=my_vision_planner)  # object with .plan(frames, image)
```

## API

`POST /ai-editor/edit` (multipart `video` + `image`, optional `use_vision` form
field) runs the edit and returns a report with a `download_url` for the edited
MP4. `GET /ai-editor/output/{filename}` serves it.

## Verification

`python scripts/qa_ai_video_editor.py` builds a short clip with a moving
subject, runs both no-vision and with-vision modes, and asserts the exported
MP4 has real video + audio streams.

## Notes

- Windows-safe image IO (`np.fromfile`/`imdecode`) so non-ASCII paths work.
- Even working dimensions are enforced for libx264 + yuv420p.
- Source audio is auto-preserved when the source video has a track.