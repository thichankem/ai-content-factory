# NLE Studio Full Architecture Specification
**Synthesized from Adobe Premiere Pro 2025, CapCut Pro Desktop, DaVinci Resolve Studio 19, Apple Final Cut Pro 11, and Adobe After Effects 2025**

---

## 1. Executive Summary & Pipeline Topology

The **AI Content Factory NLE Studio** synthesizes the best capabilities of the industry's premier non-linear video editing (NLE) suites into an autonomous, AI-driven, human-in-the-loop production pipeline:

- **Adobe Premiere Pro 2025**: Contextual Properties Panel (dynamic Text, Video, Audio typography and appearance), Essential Sound panel (AI speech enhancement, loudness matching), Dual Monitors (Program & Source), Lumetri Scopes (RGB Parade, Waveform, Vectorscope), and SMPTE timecode editing.
- **CapCut Pro Desktop**: Neural Auto-Captions with keyword highlighting and viral templates (Trending Box, Emphasis Bounce, Glow Neon), Auto Cutout without green screen, and dynamic Speed Curves (Speed Ramping) with optical flow frame interpolation.
- **DaVinci Resolve Studio 19**: Fusion Node Graph Compositor with connected node dataflow (`MediaIn` -> `MagicMask AI` / `LumetriColor` -> `Merge` -> `MediaOut`), Fairlight 5-band parametric EQ, and sidechain auto-ducking.
- **Adobe After Effects 2025**: Bezier Keyframe Graph Editor with cubic bezier easing (`P1x`, `P1y`, `P2x`, `P2y`), spatial/temporal interpolation, and track matte switches.
- **Adobe Photoshop & Lightroom**: Multi-layer compositing, RGB tone curves, 4x neural super-resolution upscale, and background removal (`rembg`).

The Studio organizes the creative workflow into **7 sequential steps** on a permanent left taskbar, backed by an **authoritative state machine** with two mandatory human review gates:

```mermaid
graph LR
    Step1["1. Xây dựng Kịch bản<br/>(Scriptwriting & Storyboard)"] --> Gate1{Gate 1: Duyệt Kịch bản<br/>& Xác nhận Bản quyền}
    Gate1 --> Step2["2. Tư liệu & Media Bin<br/>(Asset Hunter)"]
    Step2 --> Step3["3. Chỉnh sửa Ảnh<br/>(Photo Lab & Upscale)"]
    Step3 --> Step4["4. Video & Motion FX<br/>(Speed Ramp, LUTs, Graph)"]
    Step4 --> Step5["5. Âm thanh & Lồng tiếng<br/>(Audio Lab, EQ, Ducking)"]
    Step5 --> Step6["6. Ghép nối Timeline<br/>(Dual Monitors & Tools)"]
    Step6 --> Step7["7. Xuất ra & Kiểm duyệt<br/>(Pre-flight QC & Packaging)"]
    Step7 --> Gate2{Gate 2: Duyệt Video Cuối<br/>(Final Approval)}
    Gate2 --> Publish["Đăng tải Đa nền tảng<br/>(YouTube / TikTok / Reels)"]
```

---

## 2. State Machine & Mandatory Review Gates

The authoritative state machine is defined in `src/content_factory/state.py`. Every mutation through the API, background workers, and AI agents MUST adhere to these rules:

### 2.1 State Lifecycle & Permitted Transitions

| Source State | Target State | Trigger / Action | Authorization & Review Gate |
| :--- | :--- | :--- | :--- |
| `draft` | `script_review` | Script generation complete or manual draft submitted | AI Script Engine |
| `script_review` | `script_approved` | `POST /projects/{id}/approve-script` | **Gate 1: Mandatory Human Review** (`source_rights_confirmed=True`) |
| `script_approved` | `generating` | `POST /projects/{id}/generate` | Worker Task Queue |
| `generating` | `video_review` | Background video render worker completes | Automated Render Engine |
| `video_review` | `video_approved` | `POST /projects/{id}/video/approve` | **Gate 2: Mandatory Human Review** |
| `video_review` | `generating` | `POST /projects/{id}/video/reject` | Human Operator Feedback |
| `video_approved` | `published` | `POST /projects/{id}/publish` | Publisher Syndicator |
| *Any* | `archived` | `POST /projects/{id}/archive` | Operator Action |

### 2.2 Invariant Constraints
1. **Source Rights Protection**: `source_rights_confirmed` can NEVER be auto-confirmed by any AI agent, script, or automated toolchain. It requires human operator affirmation.
2. **Timeline vs. Script Independence**:
   - The script cannot be edited once `script_approved` without resetting the project.
   - The timeline (`VideoProject`) can be edited freely in `generating`, `video_review`, `video_approved`, and `published` states (re-cutting is non-destructive to the underlying source rights).
3. **Server-Owned Revision Counter**: Every modification to the timeline increments `revision: int`. Clients must submit current `revision` to prevent race conditions.

---

## 3. Pydantic Domain Contracts (`src/content_factory/models/`)

To support all synthesized NLE capabilities, the following models extend the backend data contracts.

### 3.1 Properties Inspector Model (`models/inspector.py`)

```python
"""Domain models for Premiere Pro 2025 Contextual Properties & CapCut Video Inspector."""

from __future__ import annotations
import enum
from typing import Literal
from pydantic import BaseModel, Field


class TextStrokePosition(enum.StrEnum):
    OUTER = "outer"
    CENTER = "center"
    INNER = "inner"


class TextAlignment(enum.StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextProperties(BaseModel):
    """Premiere Pro 2025 Typography & Text Appearance Properties."""
    
    font_family: str = Field(default="Monument Extended", description="Font family name")
    font_size: int = Field(default=96, ge=12, le=300, description="Font size in pixels")
    font_weight: Literal["Regular", "Medium", "SemiBold", "Bold", "Black"] = "Bold"
    text_align: TextAlignment = TextAlignment.CENTER
    tracking: int = Field(default=15, ge=-100, le=500, description="Letter spacing in 1/1000 em")
    leading: int = Field(default=110, ge=50, le=250, description="Line height percentage")
    all_caps: bool = Field(default=True, description="Transform all characters to uppercase")
    
    # Fill & Color
    fill_color: str = Field(default="#ffffff", regex=r"^#[0-9a-fA-F]{6}$")
    
    # Stroke
    has_stroke: bool = Field(default=True)
    stroke_color: str = Field(default="#000000", regex=r"^#[0-9a-fA-F]{6}$")
    stroke_width: int = Field(default=4, ge=0, le=50)
    stroke_position: TextStrokePosition = TextStrokePosition.OUTER
    
    # Background Box
    has_background: bool = Field(default=False)
    bg_color: str = Field(default="#090a0f", regex=r"^#[0-9a-fA-F]{6}$")
    bg_opacity: int = Field(default=80, ge=0, le=100)
    bg_padding: int = Field(default=16, ge=0, le=100)
    bg_radius: int = Field(default=8, ge=0, le=50)
    
    # Drop Shadow
    has_shadow: bool = Field(default=True)
    shadow_color: str = Field(default="#00f0ff", regex=r"^#[0-9a-fA-F]{6}$")
    shadow_opacity: int = Field(default=90, ge=0, le=100)
    shadow_angle: int = Field(default=135, ge=0, le=360)
    shadow_distance: int = Field(default=8, ge=0, le=100)
    shadow_blur: int = Field(default=16, ge=0, le=100)


class AutoCutoutSettings(BaseModel):
    """CapCut Pro AI Auto Cutout, Chroma Keying & Face Retouch."""
    
    # Auto Cutout (Neural Human Segmentation)
    auto_cutout_enabled: bool = Field(default=False)
    cutout_model: Literal["birefnet", "rembg-human", "u2net"] = "birefnet"
    stroke_feather: float = Field(default=2.5, ge=0.0, le=20.0, description="Edge feathering in pixels")
    invert_cutout: bool = Field(default=False)
    
    # Chroma Keying
    chroma_key_enabled: bool = Field(default=False)
    key_color: str = Field(default="#00ff00", description="Hex key color to remove")
    tolerance: int = Field(default=45, ge=0, le=100, description="Color tolerance")
    softness: int = Field(default=20, ge=0, le=100, description="Edge softness")
    spill_reduction: int = Field(default=35, ge=0, le=100)
    
    # Face Retouch
    face_retouch_enabled: bool = Field(default=False)
    skin_smooth: int = Field(default=30, ge=0, le=100)
    skin_brighten: int = Field(default=15, ge=0, le=100)
    eye_brighten: int = Field(default=20, ge=0, le=100)
    
    # Mask Shapes
    mask_shape: Literal["none", "rectangle", "circle", "heart", "star"] = "none"
    mask_invert: bool = Field(default=False)
```

### 3.2 Auto-Captions Engine Model (`models/captions.py`)

```python
"""Domain models for CapCut Pro Auto-Captions & AI Keyword Highlights."""

from __future__ import annotations
import enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CaptionTemplateType(enum.StrEnum):
    TRENDING = "trending"
    EMPHASIS = "emphasis"
    GLOW = "glow"
    EMOJI = "emoji"
    MONOLINE = "monoline"
    MULTILINE = "multiline"


class CaptionWordCue(BaseModel):
    """Word-level alignment for dynamic karaoke animation."""
    word: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    is_highlighted: bool = Field(default=False)


class CaptionSegment(BaseModel):
    """A single subtitle line with word-level cues."""
    id: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    text: str
    words: List[CaptionWordCue] = Field(default_factory=list)
    preset_style: CaptionTemplateType = CaptionTemplateType.TRENDING
    text_color: str = "#ffffff"
    bg_box_color: Optional[str] = "#ef4444"
    glow_color: Optional[str] = None


class AutoCaptionsRequest(BaseModel):
    """Request payload for transcribing and styling auto-captions."""
    project_id: str
    language: Literal["vi", "en", "auto"] = "vi"
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3"] = "base"
    highlight_keywords: bool = Field(default=True, description="AI extraction of emotionally charged viral words")
    max_words_per_line: int = Field(default=4, ge=1, le=12, description="Short-form single/two line cadence")
    template_id: str = Field(default="trend-box")
```

### 3.3 Speed Ramping & Motion Bezier Model (`models/videofx.py`)

```python
"""Domain models for CapCut Dynamic Speed Ramping & After Effects Keyframe Graph."""

from __future__ import annotations
from typing import List, Literal, Tuple
from pydantic import BaseModel, Field


class BezierHandle(BaseModel):
    """Cubic Bezier curve control handle for easing."""
    x: float = Field(ge=0.0, le=1.0, description="Normalized time position")
    y: float = Field(description="Normalized value position")


class BezierKeyframe(BaseModel):
    """Keyframe with incoming and outgoing bezier control points."""
    time: float = Field(ge=0.0, description="Timestamp in seconds")
    value: float = Field(description="Property value at keyframe")
    ease_in: BezierHandle = Field(default_factory=lambda: BezierHandle(x=0.42, y=0.0))
    ease_out: BezierHandle = Field(default_factory=lambda: BezierHandle(x=0.58, y=1.0))
    interpolation: Literal["linear", "bezier", "hold"] = "bezier"


class SpeedCurvePoint(BaseModel):
    """Dynamic speed ramp waypoint."""
    time_offset: float = Field(ge=0.0, le=1.0, description="Normalized clip duration (0 to 1)")
    speed_factor: float = Field(ge=0.1, le=10.0, description="Playback speed multiplier (0.1x to 10x)")


class SpeedRampConfig(BaseModel):
    """CapCut Pro Speed Ramping configuration with Optical Flow blending."""
    preset: Literal["custom", "hero_bullet", "montage_fast", "flash_in"] = "hero_bullet"
    points: List[SpeedCurvePoint] = Field(default_factory=list)
    optical_flow: bool = Field(default=True, description="Use AI frame blending for butter-smooth slow-motion")
    smooth_curve: bool = Field(default=True)
    pitch_correction: bool = Field(default=True, description="Preserve audio pitch when speed changes")


class LumetriColorConfig(BaseModel):
    """Premiere Pro Lumetri Color & 3D LUT configuration."""
    lut_name: Literal["none", "Teal & Orange", "Cyberpunk", "Film Noir", "Kodachrome", "Matrix"] = "Teal & Orange"
    lut_intensity: float = Field(default=1.0, ge=0.0, le=2.0)
    color_temp: int = Field(default=0, ge=-50, le=50, description="Kelvin shift (-50 cold to +50 warm)")
    color_tint: int = Field(default=0, ge=-50, le=50, description="Green-to-Magenta shift")
    exposure: float = Field(default=0.0, ge=-5.0, le=5.0)
    contrast: int = Field(default=0, ge=-50, le=50)
    saturation: int = Field(default=100, ge=0, le=200, description="Saturation percentage (100 is neutral)")
    shadows: int = Field(default=0, ge=-50, le=50)
    highlights: int = Field(default=0, ge=-50, le=50)
```

### 3.4 Audio Lab & Fairlight Console Model (`models/audiolab.py`)

```python
"""Domain models for Adobe Audition 5-Band Parametric EQ & Fairlight Console."""

from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field


class ParametricEQBand(BaseModel):
    """Single frequency band in the parametric equalizer."""
    band_id: Literal["sub", "low_mid", "mid", "presence", "air"]
    freq_hz: int = Field(description="Center frequency in Hertz")
    gain_db: float = Field(default=0.0, ge=-15.0, le=15.0, description="Gain cut or boost in dB")
    q_factor: float = Field(default=1.41, ge=0.1, le=10.0, description="Filter bandwidth Q factor")
    enabled: bool = Field(default=True)


class Audition5BandEQ(BaseModel):
    """5-Band Parametric EQ matching Adobe Audition & DaVinci Fairlight."""
    bands: List[ParametricEQBand] = Field(
        default_factory=lambda: [
            ParametricEQBand(band_id="sub", freq_hz=60, gain_db=0.0),
            ParametricEQBand(band_id="low_mid", freq_hz=250, gain_db=0.0),
            ParametricEQBand(band_id="mid", freq_hz=1000, gain_db=0.0),
            ParametricEQBand(band_id="presence", freq_hz=4000, gain_db=0.0),
            ParametricEQBand(band_id="air", freq_hz=12000, gain_db=0.0),
        ]
    )
    master_gain_db: float = Field(default=0.0, ge=-24.0, le=12.0)


class SidechainDuckingConfig(BaseModel):
    """Fairlight Sidechain Compressor for Auto-Ducking BGM under Voiceover."""
    enabled: bool = Field(default=True)
    ducking_depth_db: float = Field(default=-16.0, ge=-36.0, le=0.0, description="Attenuation amount")
    threshold_db: float = Field(default=-22.0, ge=-60.0, le=0.0)
    ratio: float = Field(default=4.0, ge=1.0, le=20.0)
    attack_ms: float = Field(default=80.0, ge=1.0, le=500.0)
    release_ms: float = Field(default=450.0, ge=50.0, le=2000.0)
    hold_ms: float = Field(default=100.0, ge=0.0, le=1000.0)


class MultiTrackFaders(BaseModel):
    """Fairlight audio channel strip faders with mute and solo controls."""
    narration_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    narration_mute: bool = Field(default=False)
    bgm_gain: float = Field(default=0.35, ge=0.0, le=2.0)
    bgm_mute: bool = Field(default=False)
    sfx_gain: float = Field(default=0.8, ge=0.0, le=2.0)
    sfx_mute: bool = Field(default=False)
    master_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    target_lufs: float = Field(default=-14.0, ge=-24.0, le=-8.0, description="-14 LUFS YouTube, -16 LUFS TikTok")
```

### 3.5 DaVinci Resolve 19 Fusion Node Graph Model (`models/fusion.py`)

```python
"""Domain models for DaVinci Resolve Studio 19 Fusion Node Graph Compositing."""

from __future__ import annotations
import enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class FusionNodeType(enum.StrEnum):
    INPUT = "input"
    AI_TRANSFORM = "ai"
    EFFECT = "effect"
    MERGE = "merge"
    OUTPUT = "output"


class FusionBlendOperator(enum.StrEnum):
    OVER = "Over"
    SCREEN = "Screen"
    MULTIPLY = "Multiply"
    ADD = "Add"
    SUBTRACT = "Subtract"
    UNDER = "Under"


class FusionNodeSocket(BaseModel):
    name: str
    socket_type: Literal["image", "mask", "audio", "data"]
    connected_to: Optional[str] = None  # Format: "node_id:socket_name"


class FusionNode(BaseModel):
    """A node inside the DaVinci Resolve Fusion compositing graph."""
    id: str
    name: str
    node_type: FusionNodeType
    pos_x: float
    pos_y: float
    params: Dict[str, Any] = Field(default_factory=dict)
    inputs: List[FusionNodeSocket] = Field(default_factory=list)
    outputs: List[FusionNodeSocket] = Field(default_factory=list)
    is_cached: bool = Field(default=False)
    is_active: bool = Field(default=True)


class FusionGraphPayload(BaseModel):
    """Directed Acyclic Graph representing full visual compositing tree."""
    project_id: str
    nodes: List[FusionNode]
    output_resolution: Literal["1080x1920", "1920x1080", "2160x3840", "3840x2160"] = "1080x1920"
    color_space: Literal["Rec.709", "DaVinci Wide Gamut", "sRGB"] = "Rec.709"
    bit_depth: Literal["8-bit", "10-bit", "16-bit float", "32-bit float"] = "10-bit"
```

---

## 4. Service Layer Architecture (`src/content_factory/services/`)

The service layer is composed via Python Mixins inheriting from `ServiceContext`. This design ensures high modularity, testability, and adherence to `tests/test_architecture.py`.

```
src/content_factory/services/
├── __init__.py               # Re-exports all service mixins
├── context.py                # ServiceContext with storage, config, db handles
├── script.py                 # Script generation & approval mixin
├── media.py                  # Asset hunting & media library mixin
├── photolab.py               # Photo Lab, tone curves, upscale, rembg mixin
├── videofx.py                # Speed ramping, Bezier graph, Lumetri color mixin
├── audiolab.py               # 5-Band EQ, Fairlight ducking, Edge-TTS mixin
├── inspector.py              # Contextual properties, typography, auto-cutout mixin
├── fusion.py                 # DaVinci Resolve Fusion node graph executor mixin
├── timeline.py               # Multi-track timeline assembly & normalization mixin
└── export_qc.py              # Pre-flight QC checklist, LUFS audit & packaging mixin
```

### 4.1 Service Mixin Interface Definitions

#### A. VideoFXServiceMixin (`services/videofx.py`)
```python
class VideoFXServiceMixin:
    """Methods for dynamic speed curves, Lumetri LUT application, and After Effects easing."""

    async def apply_speed_ramp(
        self, project_id: str, scene_index: int, config: SpeedRampConfig
    ) -> Dict[str, Any]:
        """Calculates optical flow frame points and generates ffmpeg filter graph for non-linear speed."""
        ...

    async def apply_lumetri_grade(
        self, project_id: str, scene_index: int, config: LumetriColorConfig
    ) -> Dict[str, Any]:
        """Applies 3D LUT .cube file and color temperature/tint matrix."""
        ...

    async def evaluate_bezier_curve(
        self, keyframes: List[BezierKeyframe], time_t: float
    ) -> float:
        """Evaluates De Casteljau cubic bezier easing for smooth parameter transition."""
        ...
```

#### B. AudioLabServiceMixin (`services/audiolab.py`)
```python
class AudioLabServiceMixin:
    """Methods for 5-band parametric EQ, sidechain ducking, and neural speech enhancement."""

    async def process_parametric_eq(
        self, audio_path: Path, eq_config: Audition5BandEQ
    ) -> Path:
        """Runs ffmpeg 'equalizer' filter chain across 60Hz, 250Hz, 1kHz, 4kHz, and 12kHz."""
        ...

    async def process_sidechain_ducking(
        self, speech_path: Path, bgm_path: Path, ducking_config: SidechainDuckingConfig
    ) -> Path:
        """Runs ffmpeg 'sidechaincompress' or 'asubboost' with attack/release envelopes."""
        ...

    async def enhance_dialogue_speech(
        self, audio_path: Path, noise_reduction_db: float = 12.0
    ) -> Path:
        """Performs spectral subtraction and speech clarity enhancement."""
        ...
```

#### C. FusionServiceMixin (`services/fusion.py`)
```python
class FusionServiceMixin:
    """Executes DaVinci Resolve Fusion Node Graphs."""

    async def validate_fusion_graph(self, graph: FusionGraphPayload) -> List[str]:
        """Checks for cycles, missing input sockets, or mismatched resolutions."""
        ...

    async def execute_fusion_compositing(
        self, graph: FusionGraphPayload, output_path: Path
    ) -> Dict[str, Any]:
        """Compiles graph into an optimal filter_complex ffmpeg/OpenCV pipeline and renders result."""
        ...
```

---

## 5. Complete REST API Endpoints Specification

| Method | Route Path | Request Body | Response Shape | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/inspector/properties/text` | `TextProperties` | `{"success": bool, "css_preview": str}` | Renders text typography with multi-stroke & drop shadow |
| `POST` | `/api/v1/inspector/cutout` | `AutoCutoutSettings` | `{"mask_url": str, "foreground_url": str}` | Executes neural cutout segmentation (`rembg`/`birefnet`) |
| `POST` | `/api/v1/captions/transcribe` | `AutoCaptionsRequest` | `List[CaptionSegment]` | Transcribes audio with Whisper and highlights emotional words |
| `POST` | `/api/v1/videofx/speed-ramp` | `SpeedRampConfig` | `{"rendered_clip": str, "duration": float}` | Applies dynamic speed ramping with optical flow blending |
| `POST` | `/api/v1/videofx/lumetri` | `LumetriColorConfig` | `{"preview_frame": str}` | Applies 3D LUT cube and color temperature adjustments |
| `POST` | `/api/v1/audiolab/eq` | `Audition5BandEQ` | `{"processed_audio": str, "frequency_response": list}` | Applies 5-band parametric equalizer filter |
| `POST` | `/api/v1/audiolab/ducking` | `SidechainDuckingConfig` | `{"mixed_audio": str, "attenuation_log": list}` | Ducks background music under dialogue track |
| `POST` | `/api/v1/fusion/render` | `FusionGraphPayload` | `{"task_id": str, "status": str}` | Executes asynchronous Fusion Node Graph rendering |
| `GET` | `/api/v1/fusion/graph/{project_id}` | *None* | `FusionGraphPayload` | Retrieves current project node compositing graph |
| `GET` | `/api/v1/export/preflight-qc/{id}` | *None* | `QCReport` (Loudness, Safe Zones, Bitrate) | Runs automated pre-flight quality control audit |
| `POST` | `/api/v1/projects/{id}/approve-script` | `{"source_rights_confirmed": bool}` | `Project` | **Gate 1**: Mandatory script approval (Requires human rights check) |
| `POST` | `/api/v1/projects/{id}/video/approve` | `{"reviewed_by": str}` | `Project` | **Gate 2**: Mandatory final video approval |
| `POST` | `/api/v1/projects/{id}/publish` | `{"platforms": list, "schedule": str}` | `PublishReceipt` | Publishes approved video to YouTube, TikTok, Facebook |

---

## 6. Universal AI Agent Harness & MCP Protocol Integration

All synthesized capabilities are exposed to external autonomous AI agents (Google Antigravity, Claude Code, Gemini CLI, Codex) through two universal interfaces:

### 6.1 Unified REST Tool Invocation (`POST /tools/call`)

External agents can execute any operation by sending a JSON payload:

```json
POST /tools/call
{
  "tool": "apply_speed_ramp",
  "args": {
    "project_id": "proj_viral_hook_01",
    "scene_index": 0,
    "config": {
      "preset": "hero_bullet",
      "optical_flow": true,
      "points": [
        {"time_offset": 0.0, "speed_factor": 1.0},
        {"time_offset": 0.3, "speed_factor": 0.25},
        {"time_offset": 0.7, "speed_factor": 3.5},
        {"time_offset": 1.0, "speed_factor": 1.0}
      ]
    }
  }
}
```

### 6.2 Model Context Protocol (`mcp_server.py`)

Every tool is automatically registered in the MCP tool registry:

```python
@mcp.tool()
async def audiolab_parametric_eq(
    project_id: str,
    sub_gain_db: float = 0.0,
    low_mid_gain_db: float = -2.0,
    presence_gain_db: float = 3.5,
    air_gain_db: float = 2.0,
) -> str:
    """Fine-tune narration dialogue with Adobe Audition 5-band parametric EQ."""
    ...
```

---

## 7. Quality Gates & Architectural Compliance Verification

To maintain the architectural integrity of the repository, all new backend modules MUST satisfy:

1. **Ruff Lint & Format**:
   ```bash
   python -m ruff check src tests
   python -m ruff format --check src tests
   ```
2. **Mypy Static Type Checking**:
   ```bash
   python -m mypy src
   ```
3. **Architecture Constraint Enforcer (`tests/test_architecture.py`)**:
   - Every service mixin must be disjoint (no overlapping method names).
   - Every method must be reachable from `ContentFactoryService`.
   - All domain models must be re-exported in `src/content_factory/models/__init__.py`.
   - State machine in `src/content_factory/state.py` must never be bypassed.
4. **Pytest Full Suite**:
   ```bash
   python -m pytest
   ```
