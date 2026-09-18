# System Documentation: `docs/`

This directory contains technical specifications, architecture blueprints, agent integration contracts, and the operator's master plan for the **AI Content Factory**.

---

## Documentation Index

| File | Purpose | Language |
| :--- | :--- | :--- |
| [`KE-HOACH-TONG-THE.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/KE-HOACH-TONG-THE.md) | **The Project Memory & Master Plan**: Comprehensive roadmap, requirements, architectural decisions, technical debt registry, and chronological change log. | Vietnamese (per operator convention) |
| [`AGENT-BRIDGE.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/AGENT-BRIDGE.md) | **External AI Agent Protocol**: The Markdown contract format used to exchange structured briefs with external AI coding agents (Claude, Codex, DeepSeek, Gemini). | English |
| [`TOOLCHAIN.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/TOOLCHAIN.md) | **Local Media & AI Toolchain**: Recommended local utilities (`ffmpeg`, `piper`, `whisper`, `imagemagick`, `yt-dlp`), installation instructions, and fallback strategies. | English |
| [`TOOLS-FOR-AGENTS.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/TOOLS-FOR-AGENTS.md) | **Agent Tool Surface**: How an external agent (Claude, Codex, DeepSeek, Gemini) discovers and calls everything through `GET /tools` + `POST /tools/call`, with curl recipes. | English / Vietnamese |
| [`SEO-SCORING.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/SEO-SCORING.md) | **SEO Scoring & Packaging Audit**: The research-backed scoring model for YouTube/Shorts/TikTok, the verified optimiser contract, the A/B and calibration statistics, and how to score a real project. | English |
| [`COMPUTE-RESOURCES.md`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/docs/COMPUTE-RESOURCES.md) | **Compute Resources**: How the GPU is discovered and used — multi-build NVENC unlock, measured encode/decode numbers, the admission ladder, the overload abort thresholds, and how to unlock the GPU for torch models. | English |

---

## Maintenance & Update Protocol

1. **Language Rules**:
   - `docs/KE-HOACH-TONG-THE.md` is exclusively maintained in Vietnamese to preserve direct communication with the project operator.
   - All other technical documentation must be written in English.
2. **Post-Task Updates**:
   - After completing any non-trivial feature, refactoring, or architectural change, append a record to Section 9 (*Nhật ký thay đổi*) of `KE-HOACH-TONG-THE.md` following the established date-stamped template:
     - `Mục tiêu` (Goal)
     - `Đã làm` (Completed work)
     - `Kiểm chứng` (Verification & Quality gates)
     - `Quyết định` (Key architectural decisions)
     - `Việc tiếp theo` (Next steps)
