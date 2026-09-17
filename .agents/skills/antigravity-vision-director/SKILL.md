---
name: antigravity-vision-director
description: >-
  Autonomous Multimodal AI Vision Director for Google Antigravity and vision-enabled AI agents.
  Performs deep visual inspection of video frames, aesthetic scoring, color grading verification,
  safe margins / HUD layout checks (TikTok 9:16 vs YouTube 16:9), subtitle readability audit,
  optical flow tracking verification, and thumbnail clickability review.
allowed-tools:
  - Read
  - Write
  - Bash
---

# Antigravity AI Vision Director

The **AI Content Factory** is designed with a two-tier perception model:
1. **Text-First Heuristics**: For non-vision models (using OCR bounding boxes, HSV histograms, LUFS loudness, and beat grids).
2. **Multimodal AI Vision**: Powered natively by **Google Antigravity** and vision-capable LLMs. Antigravity acts as an executive **Visual Director**, examining actual rendered frames, reviewing compositions, and catching subtle visual flaws that raw numbers miss.

---

## 👁️ Why Antigravity Has the Edge

| Task | Non-Vision Heuristic | Antigravity AI Vision |
| :--- | :--- | :--- |
| **Frame Quality** | Laplacian variance (sharpness number) | Evaluates composition, focal point, lighting, and emotional resonance |
| **Subtitle Placement** | Fixed pixel coordinates ($y = h - 85$) | Sees if subtitles cover faces, hands, or clash with busy backgrounds |
| **Safe Margins** | Hardcoded rectangle math | Identifies whether TikTok/Reels UI buttons actually obscure key visual elements |
| **Color Grading** | Contrast & Saturation multiplier | Analyzes skin tone warmth, filmic mood, quầng sáng plasma, and aesthetic depth |
| **Thumbnail Selection** | Sharpest frame | Frame with the strongest psychological visual hook and curiosity gap |

---

## 🎬 Core Director Workflows

### 1. Visual Frame Extraction & Inspection

When reviewing a video or scene, extract key candidate frames and inspect them directly with `view_file`:

```python
import subprocess
from pathlib import Path

def extract_keyframe(video_path: Path, timestamp_sec: float, output_image: Path) -> Path:
    cmd = [
        "ffmpeg", "-y", "-ss", str(timestamp_sec),
        "-i", str(video_path),
        "-vframes", "1", "-q:v", "2",
        str(output_image)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_image
```

Once extracted, call `view_file` on the resulting `.jpg` or `.png` to view and evaluate the frame with native AI vision.

---

### 2. Safe Margins & HUD Audit Checklist

When inspecting 9:16 (Shorts/TikTok/Reels) or 16:9 (YouTube) frames, verify against the following rules:

1. **Title Safe Zone (80%)**: All titles, chapter badges, and watermarks must stay inside the inner 80% boundary.
2. **Action Safe Zone (90%)**: Critical moving subjects or focal objects must not touch the outer 5% edge.
3. **Shorts/TikTok Danger Zone (9:16)**:
   - **Top 15%**: Header, search bar, and camera icons.
   - **Right 15%**: Like, comment, bookmark, share buttons.
   - **Bottom 22%**: Account username, caption text, sound title.
   - *Rule*: Subtitles MUST be centered in the vertical sweet spot between 60% and 75% height.
4. **Subtitle Legibility**:
   - Subtitle text must have an opaque or semi-transparent background box (`boxcolor=black@0.75`).
   - Font size must be minimum 20pt on 720p, 28pt on 1080p.
   - Text must never collide with on-screen faces or logos.

---

### 3. Contact Sheet Multi-Frame Aesthetic Selection

Generate a visual contact sheet of the top candidate frames using the backend media tool:

```bash
# Call via POST /tools/call
curl -s -X POST http://127.0.0.1:8080/tools/call \
  -H 'Content-Type: application/json' \
  -d '{"tool": "media_contact_sheet", "args": {"ref": "<asset_id_or_path>", "num_frames": 9, "columns": 3}}'
```

Antigravity then reads the generated contact sheet image via `view_file` to:
- Compare facial expressions and action peaks across all 9 tiles.
- Select the best candidate for the video thumbnail (`image_crop` to 16:9 or 9:16).
- Instruct the pipeline to trim dead-air or blurry transitions.

---

### 4. Vision-Assisted Optical Flow Compositing

In `src/content_factory/ai_video_editor.py`, the AI video editor can receive a `VisionPlanner` directly:

```python
from content_factory.ai_video_editor import AiVideoEditor

class AntigravityVisionPlanner:
    def plan(self, frames, overlay_image):
        # 1. Inspect the scene background and subject movement
        # 2. Return optimal placement (x, y, scale, angle, time_window)
        #    so the image blends naturally into negative space without blocking the subject.
        return {"x": 80, "y": 120, "scale": 0.25, "start_sec": 4.0, "duration_sec": 8.0}

editor = AiVideoEditor(vision=AntigravityVisionPlanner())
report = editor.edit(video_path, image_path, output_path)
```

---

### 5. Gate 2 (Video Approval) Visual QA Protocol

Before approving Gate 2 (`ApprovalStage.VIDEO`), Antigravity executes this 4-point visual audit:

1. **Frame Stability**: Sample 3 frames (beginning, middle, climax). Ensure no black frames or encoding corruption.
2. **Color Balance**: Ensure contrast and saturation enhance the footage without clipping highlights or muddying shadows.
3. **Text & Watermark Alignment**: Confirm channel branding and subtitles are crisp, sharp, and correctly positioned.
4. **Motion Dynamic**: Confirm moving footage (NASA/stock/AI video) flows smoothly without stutter or frame duplication.
