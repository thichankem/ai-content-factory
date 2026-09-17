---
name: ai-thumbnail-photo
description: AI Agent Skill for designing click-worthy viral video thumbnails, cover graphics, and promotional artwork in Photo Lab with Photoshop-style layers, tone curves, typography, and contrast balancing.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Thumbnail & Photo Design Skill — Photoshop-Style Graphics Lab

This skill guides AI agents in crafting viral thumbnail covers for TikTok, YouTube Shorts, and Instagram Reels using the built-in Photo Lab studio.

## 1. Dimensional Standards

- **Vertical Cover (TikTok / Shorts / Reels)**: `720 × 1280` px (9:16 aspect ratio).
- **Cinematic Landscape (YouTube Video)**: `1280 × 720` px (16:9 aspect ratio).
- **Square Feed (Instagram Post)**: `1080 × 1080` px (1:1 aspect ratio).
- **Portrait Feed**: `1080 × 1350` px (4:5 aspect ratio).

## 2. Viral Thumbnail Principles

1. **High Contrast**: Subjects and typography must stand out clearly even on small mobile screens (<2 inches).
2. **Curiosity Gap Text**: Maximum 3-5 bold words in all caps with stroke or drop shadow (e.g. "WAIT FOR IT!", "THE 1% SECRET", "NEVER DO THIS").
3. **Color Balance**: Complementary or high-saturation palettes (Teal & Orange, Cyber Neon, Crimson & White).
4. **Focal Anchor**: A single dramatic focal point (expressive face, glowing icon, comparison split) positioned in the upper-middle third.

## 3. Layer Architecture in Photo Lab

- **Base Layer**: Captured high-resolution frame from the video timeline via `captureFrameToPhotoLab()`.
- **Adjustment Layer**: Curves, Exposure (+10%), Contrast (+25%), Saturation (+20%), and subtle Vignette to draw eyes to the center.
- **Graphic Overlays**: Glowing arrows, comparison badges ("VS"), highlight boxes.
- **Typography Layer**: Bold title font ('Outfit' or 'Inter' 68pt+) with dark stroke (`lineWidth = 8`) and glowing drop shadow.
