# Technical Specification: Professional Image & Graphic Design Engine (SPEC-IMAGE-EDITING)
**Standardized Architecture, Feature Catalog, and Mathematical Foundations for Digital Image Editing**

---

## 1. Overview & System Scope
This document specifies the complete functional architecture of the **Photo & Graphics Processing Engine**, covering non-destructive raster editing, vector shape design, multi-layer compositing, color space manipulation, and AI neural enhancements.

---

## 2. Comprehensive Feature Matrix

### 2.1 Layer Architecture & Compositing

```
[Layer Stack Engine]
 ├── Base Layer (Raster Pixel Data / Raw Image)
 ├── Vector Shape Layer (Bézier Paths, Fill, Stroke)
 ├── Text & Typography Layer (Glyphs, Fonts, Kerning)
 ├── Adjustment Layer (Curves, Levels, HSL, LUTs)
 ├── Smart Filter Layer (Non-destructive Blur, Sharpen, Noise)
 └── Layer Mask (8-bit Alpha Grayscale Matte)
```

1. **Layer Hierarchy & Grouping**:
   - Nesting, Folder Groups, Clipping Masks, Alpha Lock.
   - Opacity (0% - 100%) and Fill Opacity (affects pixels without affecting layer effects).
2. **27 Industry-Standard Blending Modes**:
   - **Normal Group**: `Normal`, `Dissolve`.
   - **Darken Group**: `Darken`, `Multiply` ($C = A \cdot B$), `Color Burn`, `Linear Burn` ($C = A + B - 1$), `Darker Color`.
   - **Lighten Group**: `Lighten`, `Screen` ($C = 1 - (1-A)(1-B)$), `Color Dodge`, `Linear Dodge (Add)` ($C = A + B$), `Lighter Color`.
   - **Contrast Group**: `Overlay`, `Soft Light`, `Hard Light`, `Vivid Light`, `Linear Light`, `Pin Light`, `Hard Mix`.
   - **Inversion Group**: `Difference` ($C = |A - B|$), `Exclusion` ($C = A + B - 2AB$), `Subtract` ($C = A - B$), `Divide` ($C = A / B$).
   - **Component Group**: `Hue`, `Saturation`, `Color`, `Luminosity`.

---

### 2.2 Color Correction & Tone Mapping

1. **Tone Curves (Cubic Splines)**:
   - **RGB Master Curve**: Controls overall luminance contrast with S-Curve, High-Key, Low-Key presets.
   - **Individual Channel Curves**: Red, Green, Blue splines for chromatic split-toning (e.g., cool shadows, warm highlights).
   - Control points: 16-bit precision coordinate grid $(x, y) \in [0, 255] \times [0, 255]$.
2. **Levels Histogram Adjustment**:
   - Input Black Point, Midtone Gamma ($\gamma \in [0.1, 9.9]$), Input White Point.
   - Output Clipping Range (0 to 255).
3. **HSL & Color Balance**:
   - **Hue Shift**: $-180^\circ$ to $+180^\circ$ circular color wheel translation.
   - **Saturation**: Desaturate ($-100\%$) to Hyper-vibrant ($+100\%$).
   - **Luminance**: Independent luminance offset per color range (Reds, Yellows, Greens, Cyans, Blues, Magentas).
   - **Color Balance**: Cyan-Red, Magenta-Green, Yellow-Blue split across Shadows, Midtones, and Highlights.
4. **Exposure & Contrast Metrics**:
   - Photographic Exposure (EV stops: $-5.0$ to $+5.0$).
   - Highlights Recovery, Shadow Fill, Whites, Blacks, Clarity (Local Contrast), Dehaze, and Vignette.

---

### 2.3 Retouching, Inpainting & Restoration

1. **Healing & Inpainting**:
   - **Content-Aware Fill**: PatchMatch texture synthesis and deep generative inpainting for removing unwanted objects or wires.
   - **Clone Stamp**: Source point sampling with alignment, feather, and opacity controls.
   - **Spot Healing**: Fast Poisson image editing for blemish and dust removal.
2. **Dodge, Burn & Sponge**:
   - Dodge: Selective exposure brightening in highlights or midtones.
   - Burn: Selective exposure darkening for adding contour and depth.
   - Sponge: Localized saturation or desaturation brush.

---

### 2.4 Neural AI Filters & Computer Vision

1. **Neural Background Cutout (Matting)**:
   - High-resolution foreground extraction using `rembg` / `BiRefNet` models.
   - Sub-pixel alpha matte feathering ($0.5\text{px} - 20\text{px}$) with edge despill.
2. **Super-Resolution Upscaling**:
   - 4x AI Upscale via `RealESRGAN-x4plus` / bicubic deep neural interpolator.
   - Preservation of fine facial details, text sharpness, and texture synthesis.
3. **Face Retouching & Beautification**:
   - Bilateral surface smoothing (skin texture preservation).
   - Micro-contrast eye enhancement and teeth whitening.

---

### 2.5 Typography, Vector Shapes & Styling

1. **Type Engine**:
   - Modern OpenType / TrueType font loading with variable weights (`100` to `900`).
   - Tracking (Letter spacing), Leading (Line height), Kerning pairs, All-Caps, Small-Caps, Superscript, Subscript.
2. **Layer Styles & FX**:
   - **Multi-Stroke**: Outer, Center, Inner strokes with solid color or gradient fill.
   - **Drop Shadow**: Light angle ($0^\circ - 360^\circ$), Distance, Spread, Size/Blur, Color, Opacity.
   - **Inner Glow & Outer Glow**: Gaussian radial diffusion with custom color envelopes.
   - **Background Box**: Dynamic auto-sizing bounding box with padding, corner radius, and alpha transparency.

---

## 3. UI Implementation Mapping
All features listed above are mapped directly to the frontend components:
- [PhotoLabStudio.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/photo/PhotoLabStudio.tsx): Canvas Retina Viewport, Layers List, Tone Curves, Sliders.
- [PropertiesInspector.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/inspector/PropertiesInspector.tsx): Text Typography, Stroke, Shadow, Background, Neural Cutout & Retouch.
