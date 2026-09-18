# Technical Specification: Professional Video & Motion FX Engine (SPEC-VIDEO-EDITING)
**Standardized Architecture, Feature Catalog, and Mathematical Foundations for Non-Linear Video Editing**

---

## 1. Overview & System Scope
This document specifies the complete functional architecture of the **Non-Linear Video Editing (NLE) & Motion FX Engine**, covering multi-track timeline assembly, non-destructive editing tools, dynamic speed curves, cubic bézier easing, 3D LUT color grading, real-time video scopes, speech-to-text auto-captions, and node-based compositing.

---

## 2. Comprehensive Feature Matrix

### 2.1 Multi-Track Timeline & Editing Operations

```
[Master Timeline Architecture]
 ├── Video Track 3 (V3): Title Overlays, Graphics, Watermarks
 ├── Video Track 2 (V2): B-Roll, Picture-in-Picture (PiP), Stems
 ├── Video Track 1 (V1): Primary Storyline (A-Roll Main Footage)
 ├── Audio Track 1 (A1): Dialogue, Voiceover & Narration
 ├── Audio Track 2 (A2): Background Music (BGM with Auto-Ducking)
 └── Audio Track 3 (A3): Sound Effects (SFX & Foley)
```

1. **Precision NLE Tool Palette**:
   - **Selection Tool (`V`)**: Move, trim head/tail, select single or multi-clip ranges.
   - **Track Select Forward (`A`)**: Select all clips downstream from playhead.
   - **Ripple Edit Tool (`B`)**: Adjust an edit point without leaving gaps; ripples entire timeline duration.
   - **Rolling Edit Tool (`N`)**: Adjust the cut point between two adjacent clips simultaneously without altering project duration.
   - **Razor Tool (`C`)**: Split clip at exact frame playhead.
   - **Slip Tool (`Y`)**: Shift source in/out points while keeping the clip position and duration unchanged on timeline.
   - **Slide Tool (`U`)**: Move clip left or right while adjusting adjacent head/tail cuts.
   - **Pen Tool (`P`)**: Add and manipulate keyframes directly on clip tracks.
   - **Hand Tool (`H`)**: Pan horizontally across zoomed timeline view.
   - **Type Tool (`T`)**: Create on-screen text overlays at cursor point.

2. **Magnetic Snapping & Beat Alignment**:
   - Frame-accurate snapping to playhead, markers, cut points, and audio transients.
   - **BPM Grid Sync**: Automatic snapping of clip cuts to musical beats (e.g., 120 BPM quarter-notes).

---

### 2.2 Dynamic Speed Ramping & Time Remapping

1. **Non-Linear Speed Curves**:
   - Playback speed modulation from **$0.1\times$** (Extreme Slow-Motion) to **$10.0\times$** (Fast-Forward Montage).
   - Bézier curve velocity profile with smooth continuous acceleration and deceleration.
2. **Frame Interpolation Algorithms**:
   - **Optical Flow (AI Motion Vector)**: Deep pixel motion vector synthesis generating synthetic in-between frames for artifact-free 60fps/120fps slow-mo.
   - **Frame Blending**: Sub-frame alpha blending across adjacent temporal samples.
   - **Nearest Neighbor**: Instantaneous integer frame repetition for stylized stop-motion.
3. **Pitch Preservation (Time-Stretch without Pitch Shift)**:
   - WSOLA (Waveform Similarity Overlap-Add) audio time-stretching keeping vocal pitch identical.

---

### 2.3 Keyframe Bézier Graph Editor & Motion Dynamics

1. **Cubic Bézier Tangents**:
   - Dual control handles: $P_1(x_1, y_1)$ and $P_2(x_2, y_2)$ defining temporal easing:
     $$B(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3$$
   - Presets: `Linear`, `Ease In`, `Ease Out`, `Easy Ease` ($P_1 = (0.25, 0.1)$, $P_2 = (0.25, 1.0)$), `Exponential Pop`, `Rubber Band Bounce`.
2. **Transform Properties Track**:
   - Position ($X, Y, Z$), Scale (Uniform / Non-uniform $W, H$), Rotation ($\theta$), Anchor Point, Opacity.
3. **Motion Blur Synthesis**:
   - Dynamic shutter angle simulation ($0^\circ - 360^\circ$) proportional to velocity vector.

---

### 2.4 Color Grading, 3D LUTs & Real-Time Scopes

1. **Color Scopes (Rec.709 Standard)**:
   - **RGB Parade**: Discrete Red, Green, Blue channel luminance waveform comparison (0 to 255 IRE).
   - **Waveform (Luma)**: Overall scene brightness distribution detecting highlights blow-out ($>100$ IRE) and shadows crush ($<0$ IRE).
   - **Vectorscope (HSL)**: Chrominance distribution and skin tone line verification.
2. **Cinematic 3D LUTs (.CUBE)**:
   - Trilinear interpolation over $33\times 33\times 33$ or $65\times 65\times 65$ color cubes.
   - Built-in cinematic palettes: `Teal & Orange`, `Cyberpunk Neon`, `Film Noir 1940`, `Kodachrome 64`, `Matrix Emerald`.
3. **Primary Color Controls**:
   - Kelvin White Balance ($-50$ Cold to $+50$ Warm), Tint (Green vs. Magenta), Exposure (EV), Contrast, Saturation.

---

### 2.5 Neural Auto-Captions & Dynamic Subtitle Engine

1. **Speech-to-Text Recognition**:
   - Automatic word-level alignment ($t_{\text{start}}, t_{\text{end}}$ per word) via Faster-Whisper.
2. **Viral Kinetic Subtitle Styles**:
   - **Trending Box**: High-contrast solid color background pill behind current word.
   - **Emphasis Bounce**: Micro scale animation ($100\% \to 125\% \to 100\%$) on active spoken word.
   - **Glow Neon**: Cyberpunk outer luminescence pulsing with voice volume.
   - **Emoji Pop**: Automatic keyword recognition binding relevant emoji (🔥, ⚡, 💡, 🚨).
3. **Safe Margins HUD**:
   - **Title Safe Zone (80%)** & **Action Safe Zone (90%)**.
   - **Mobile 9:16 UI Exclusion Margins**: Top 15% (avatar/search), Bottom 22% (captions/audio title), Right 15% (likes/comments).

---

### 2.6 Visual Node Graph Compositor

1. **Dataflow Node Graph Architecture**:
   - Directed acyclic graph (DAG) processing media through connected sockets.
   - Core node types: `MediaIn`, `MagicMask AI` (neural segmentation), `ColorCorrect`, `Transform`, `Merge` (Over, Screen, Multiply, Add), `MediaOut`.
2. **Real-time Caching & Evaluation**:
   - Upstream node output caching preventing redundant frame computations.

---

## 3. UI Implementation Mapping
All features listed above are mapped directly to the frontend components:
- [TimelineAssemblyStudio.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/timeline/TimelineAssemblyStudio.tsx): Dual Monitors, Tool Palette, Multi-track Timeline, Properties Inspector.
- [VideoMotionFXStudio.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/videofx/VideoMotionFXStudio.tsx): Speed Ramping, Keyframe Graph Editor, Color Grading & LUTs, Node Graph Compositor.
- [CaptionSimplifier.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/captions/CaptionSimplifier.tsx): Auto-Captions, Templates, Keyword Highlighting.
- [FusionNodeCompositor.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/fusion/FusionNodeCompositor.tsx): Node Canvas, SVG Cable Connections, Parameter Inspector.
