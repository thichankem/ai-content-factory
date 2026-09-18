# System Documentation: `docs/`

Architecture blueprints, specifications, agent integration contracts, and the operator's master plan for the **AI Content Factory**.

All links below are relative, so they resolve wherever the repository is cloned. (Earlier revisions used absolute `file:///c:/Users/ADMIN/...` paths, which only worked on one machine.)

---

## The project memory

| File | Lines | Purpose |
| :--- | :--- | :--- |
| [`KE-HOACH-TONG-THE.md`](KE-HOACH-TONG-THE.md) | 1,539 | **The operator's master plan and change log.** Roadmap, requirements, architectural decisions, technical-debt registry, and a dated change history. Section 9 (*Nhật ký thay đổi*) is the running log. **Vietnamese**, by operator convention. |

## Architecture and engines

| File | Purpose |
| :--- | :--- |
| [`NLE-STUDIO-FULL-ARCHITECTURE.md`](NLE-STUDIO-FULL-ARCHITECTURE.md) | The full studio architecture specification |
| [`EDITING.md`](EDITING.md) | The video editing engine: timeline model, the 15-rule validator, render-plan compilation |
| [`MEDIA-INTELLIGENCE.md`](MEDIA-INTELLIGENCE.md) | Understanding and searching the footage library (dHash, metadata, transcript search) |
| [`PERCEPTION-LAYER.md`](PERCEPTION-LAYER.md) | When it is worth paying for "understanding" content |
| [`VISION-LAYER.md`](VISION-LAYER.md) | When it is worth paying for "understanding" a frame |
| [`VOICE-DUBBING-PIPELINE.md`](VOICE-DUBBING-PIPELINE.md) | STT → translate → TTS → align → mux |
| [`COMPUTE-RESOURCES.md`](COMPUTE-RESOURCES.md) | GPU discovery and use: multi-build NVENC unlock, measured encode/decode numbers, the admission ladder, overload-abort thresholds, unlocking the GPU for torch models |

## Specifications

| File | Purpose |
| :--- | :--- |
| [`SPEC-VIDEO-EDITING.md`](SPEC-VIDEO-EDITING.md) | Professional video & motion-FX engine |
| [`SPEC-AUDIO-EDITING.md`](SPEC-AUDIO-EDITING.md) | Professional audio engineering & sound-design engine |
| [`SPEC-IMAGE-EDITING.md`](SPEC-IMAGE-EDITING.md) | Professional image & graphic-design engine |

## Quality, provenance and growth

| File | Purpose |
| :--- | :--- |
| [`QA-LAYER.md`](QA-LAYER.md) | The QA and traceability layer — the "critic" that runs before publish |
| [`PRODUCTION-BOOSTERS.md`](PRODUCTION-BOOSTERS.md) | Ducking, virality scoring, thumbnails |
| [`SEO-SCORING.md`](SEO-SCORING.md) | The research-backed scoring model for YouTube/Shorts/TikTok, the verified optimiser contract, the A/B and calibration statistics, and how to score a real project |

## Agents and tooling

| File | Purpose |
| :--- | :--- |
| [`TOOLS-FOR-AGENTS.md`](TOOLS-FOR-AGENTS.md) | How an external agent discovers and calls everything through `GET /tools` + `POST /tools/call`, with curl recipes |
| [`AGENT-BRIDGE.md`](AGENT-BRIDGE.md) | The Markdown contract used to exchange structured briefs with external agents (Claude, Codex, DeepSeek, Gemini) |
| [`MCP-SERVERS.md`](MCP-SERVERS.md) | The MCP server tool contract |
| [`TOOLCHAIN.md`](TOOLCHAIN.md) | Installing the optional local media/AI stack (`ffmpeg`, `piper`, `whisper`, `imagemagick`, `yt-dlp`) and the fallbacks when it is absent |

## Frontend audit (`docs/frontend/`)

An audit of the **two parallel frontends** — the vanilla-JS studio FastAPI actually serves at `/`, and the Next.js client under `frontend/src/`. Architecture and tech debt, a verified bug list with `file:line` evidence, security and trust findings, feature proposals, and an upgrade/testing roadmap.

These are **operator-facing reports**, so they follow the same Vietnamese exception as `KE-HOACH-TONG-THE.md`.

| File | Purpose |
| :--- | :--- |
| [`frontend/README.md`](frontend/README.md) | Index and measured snapshot of both frontend surfaces, library-version drift |
| [`frontend/01-KIEN-TRUC-VA-TECH-DEBT.md`](frontend/01-KIEN-TRUC-VA-TECH-DEBT.md) | Architecture, state layering, dead code, and the two-frontend decision |
| [`frontend/02-DANH-SACH-LOI.md`](frontend/02-DANH-SACH-LOI.md) | The concrete bug list (P0–P3) with evidence, cause and fix |
| [`frontend/03-BAO-MAT-VA-DO-TIN-CAY.md`](frontend/03-BAO-MAT-VA-DO-TIN-CAY.md) | Security posture, exposure chain, and the Gate 1 trust model |
| [`frontend/04-CHUC-NANG-DE-XUAT.md`](frontend/04-CHUC-NANG-DE-XUAT.md) | Feature proposals (WebCodecs/WebGPU export, provenance per clip, script↔timeline sync, undo/redo, a11y, i18n) |
| [`frontend/05-LO-TRINH-VA-KIEM-THU.md`](frontend/05-LO-TRINH-VA-KIEM-THU.md) | Testing strategy, ESLint/CI gates, and the Next 14→16 / React 18→19 upgrade path |

> The bug list and the security document were written **before** the Next.js data layer was rebuilt and before the frontend was first compiled. Some findings have since been fixed — in particular the Gate 1 flow, the fabricated demo data, and every `alert()` that announced work nothing had done. Read those two files as a record of what was wrong and what was done about it, and check `docs/frontend/README.md` for the current state.

---

## Maintenance & Update Protocol

1. **Language rules**
   - `KE-HOACH-TONG-THE.md` is maintained **in Vietnamese**, to preserve direct communication with the operator.
   - The `docs/frontend/` audit reports are likewise Vietnamese: they are reports written *to* the operator.
   - All other technical documentation is written **in English**.

2. **Post-task updates**
   After any non-trivial feature, refactor or architectural change, append a record to Section 9 (*Nhật ký thay đổi*) of `KE-HOACH-TONG-THE.md`, following the established template:
   - `Mục tiêu` — the goal
   - `Đã làm` — what was done
   - `Kiểm chứng` — verification and which quality gates were run
   - `Quyết định` — key architectural decisions
   - `Việc tiếp theo` — next steps

3. **Keep numbers measured**
   Where a document quotes a count (tests, findings, files), quote the number a command actually produced and name the command. Several places in this repository still carry figures from an earlier revision; correct them when you touch the file rather than repeating them.
