# `frontend/` — two clients for the same studio

This directory holds **two independent frontends**. Knowing which one you are editing is the first question to answer, because they share no code, no styles and no build.

| | Vanilla studio | Next.js studio |
| :--- | :--- | :--- |
| **Files** | `index.html`, `style.css`, `app.js`, `editor.js`, `flow.js` | `src/**` — 97 `.ts`/`.tsx` files |
| **Size** | 15,650 lines | 17,726 lines |
| **Served at** | `/` — `src/content_factory/api/routers/index.py` returns `index.html` | Nothing. FastAPI does not mount or proxy it |
| **Runs via** | No build step | `npm run dev` → `http://localhost:3000` |
| **Language** | Plain ES2020 + hand-written DOM | TypeScript (strict), React 18, Next 14 App Router |
| **Server state** | `fetch` calls inline in each feature module | TanStack Query v5 + `src/lib/api/*` |
| **UI state** | Module-level variables | Zustand v5 (`src/stores/*`) |
| **Covered by CI** | Indirectly: the smoke test asserts `/` loads | **No CI job** |

**The vanilla studio is the product.** It is what an operator opens, and it is the only client the end-to-end smoke test exercises. The Next.js client is a rewrite in progress: its data layer is complete and type-checks, but its screens must be verified against the backend before being trusted.

---

# Part 1 — Vitrine: the vanilla studio

The sections below describe the Next.js rewrite. For the vanilla studio, the entry point is `index.html`, which loads `style.css` and three script files in order:

| File | Responsibility |
| :--- | :--- |
| `app.js` | Pipeline controller, the 7-stage stepper, empire engine, external ingest hub, project list |
| `editor.js` | NLE timeline, Web Audio SFX synthesizers, Photo Lab canvas, layer stack |
| `flow.js` | Visual DAG canvas, SVG bezier routing, snapping grid, pre-save checklist |

Its seven workspaces (Pipeline, Video Studio, Photo Lab, Node Flow, Agents Orchestra, Document Library, Empire Hub) are documented in the root `README.md`. There is no module system, no bundler and no test suite: changes are made directly and verified through the smoke test.

---

# Part 2 — Next.js Studio Pro (`src/`)

A commercial-grade video creation suite built with **Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query v5 + Zustand v5 + Framer Motion**, modelled on CapCut Pro, Adobe Premiere Pro, DaVinci Resolve, Runway and Descript.

## Current verified state

Measured on this checkout, with dependencies installed:

| Command | Result |
| :--- | :--- |
| `npx tsc --noEmit` | **0 errors** |
| `npx next build` | **✓ compiled successfully** — `/` = 154 kB route, 259 kB first load |
| `python scripts/frontend_imports.py` | **clean** across 97 files (structural import/export check) |
| `npm run lint` | **does not run** — ESLint is not installed and no config exists |

The build passing is recent history, not a given: before the data-layer refactor the project had **62 TypeScript errors** and had never once been compiled, because Node.js is not installed on the development machine by default. Every claim in this file is a claim about a build that has actually been run.

## Technology Stack

- **Framework**: Next.js 14 (App Router), React 18
- **Language**: TypeScript, `strict` mode with `@/*` path aliases
- **Styling**: Tailwind CSS — Obsidian Dark palette (`#090a0f`, `#12151f`, `#181d2a`) with Cyber Neon accents (`#00f0ff`, `#8b5cf6`, `#10b981`, `#f59e0b`)
- **Components**: shadcn/ui primitives over Radix UI (`Button`, `Card`, `Dialog`, `Tabs`, `Slider`, `Badge`, `Progress`, `Table`, `Tooltip`, `Input`, `Separator`)
- **Server state**: TanStack Query v5 — caching, invalidation and mutations
- **Client state**: Zustand v5 — player transport, timeline, project selection, photo lab, video FX, audio lab, modals
- **Motion**: Framer Motion for the `Ctrl+K` bar, VU meters, modals and transitions

## Directory Organization

```text
frontend/
├── package.json            # Scripts & dependencies
├── tsconfig.json           # Strict TypeScript, @/* aliases
├── next.config.mjs         # /api/* → 127.0.0.1:8000 rewrites
├── tailwind.config.ts      # NLE design tokens & animation keyframes
├── components.json         # shadcn/ui configuration
├── index.html              # Vanilla studio entry — served by FastAPI at /
├── style.css               # Vanilla studio stylesheet
├── app.js / editor.js / flow.js   # Vanilla studio scripts
└── src/
    ├── app/
    │   ├── layout.tsx      # Root layout + QueryClientProvider
    │   ├── page.tsx        # Studio orchestrator (project selection, workflow, campaign)
    │   └── globals.css
    ├── lib/
    │   ├── api/            # One module per backend domain — the only place URLs live
    │   │   ├── client.ts   # Transport: apiFetch, ApiError carrying FastAPI's `detail`
    │   │   ├── index.ts    # Barrel re-exporting every domain as a namespace
    │   │   └── projects.ts timeline.ts script.ts media.ts qa.ts seo.ts workflow.ts
    │   │       campaign.ts agents.ts external.ts library.ts history.ts
    │   ├── queryKeys.ts    # TanStack Query key factory (one definition per query)
    │   ├── projectSync.ts  # The single writer of project cache + store
    │   ├── scenes.ts       # makeScene/makeScenes — fills a full VideoScene's defaults
    │   └── utils.ts        # cn() and the SMPTE timecode formatter
    ├── types/              # Typed contracts, one module per backend domain
    │   ├── project.ts script.ts timeline.ts media.ts qa.ts seo.ts workflow.ts
    │   │   campaign.ts agent.ts external.ts library.ts history.ts research.ts
    │   │   voice.ts common.ts studio.ts
    │   └── index.ts        # Barrel
    ├── stores/             # Zustand: useProjectStore, usePlayerStore, useTimelineStore,
    │                       # useUIStore, usePhotoStore, useVideoFXStore, useAudioLabStore
    ├── hooks/              # TanStack Query hooks (+ index barrel)
    │   ├── useProjects.ts           # Lifecycle, both gates, script save, publish
    │   ├── useScriptEngine.ts       # Styles, virality scoring, script analysis
    │   ├── useTimelineCommands.ts   # Natural-language Co-Pilot command runner
    │   ├── useWorkflowDAG.ts        # Blocks, DAG, checklist, run history
    │   ├── useCampaign.ts           # Multi-format campaign + shorts
    │   ├── useExternalIngestion.ts  # External asset import/upload
    │   ├── useMediaLibrary.ts       # Library, search, dedup, URL ingest, re-cook
    │   ├── useQA.ts                 # Platform, brand-kit and copyright verdicts
    │   ├── useSEO.ts                # 70-signal scoring, optimiser, A/B plan, keywords
    │   ├── useThumbnails.ts         # Thumbnail candidates + CTR prediction
    │   ├── useAuditCost.ts          # Provenance audit trail + cost guard
    │   └── useAgentBridge.ts        # Markdown briefs and agent-result import
    └── components/
        ├── ui/                     # shadcn/ui primitives
        ├── layout/                 # SidebarWorkflowNav — the 7-step permanent sidebar
        ├── copilot/                # AIAgentBar, AgentBridgeModal, Ctrl+K CommandBarModal
        ├── script/                 # ScriptStudio + brief panel, editor, pacing bar, chatbot
        ├── media/                  # MediaStudio, ExternalIngestionModal,
        │                           # HtmlSlideDeckStudio, VideoUrlRecookStudio
        ├── timeline/               # TimelineAssemblyStudio, TimelineVisualizer, DualMonitorPlayer
        ├── workflow/               # DAGWorkflowStudio (blocks come from GET /workflow/blocks)
        ├── fusion/                 # FusionNodeCompositor (VFX node graph)
        ├── videofx/                # VideoMotionFXStudio
        ├── photo/                  # PhotoLabStudio
        ├── audio/                  # AudioLabStudio — mixer, EQ, ducking, TTS
        ├── qa/                     # ComplianceModal — platform / brand / copyright
        ├── export/                 # ExportReviewStudio, SeoPackagingModal
        ├── campaign/               # ContentEmpireStudio
        ├── thumbnails/             # ThumbnailModal
        ├── captions/               # CaptionSimplifier
        ├── inspector/              # PropertiesInspector
        ├── audit/                  # AuditCostModal — cost guard + audit trail
        └── project/                # NewProjectModal
```

### Layering rules

The data layer follows one direction, and deviating from it is how the earlier version drifted:

1. **URLs live only in `src/lib/api/*`.** No component calls `fetch`, and none hardcodes a host. `client.ts` owns transport; each domain module owns its paths.
2. **`hooks/*` own TanStack Query.** A component reads a hook, never a raw API function.
3. **`lib/queryKeys.ts` owns every key.** Invalidation targets a factory entry, so a typo cannot silently no-op.
4. **`lib/projectSync.ts` is the only writer of the project cache and store.** Every mutation that returns a project calls it.
5. **`lib/scenes.ts` builds scenes.** Screens that assemble a scene locally (auto-assemble, slide deck, re-cook) call `makeScene` instead of hand-writing a 30-field object.

### Gate 1 from this client

The two human gates are enforced by the backend, so the client must not act as if it can open them:

- **Confirming source rights is a request.** Ticking the checkbox in `ScriptEditorView` calls `saveScriptMutation` with `sourceRightsConfirmed: true`, which is `PUT /projects/{id}/script`. The store has no local `confirmSourceRights` any more — a local flag could only ever disagree with the server.
- **The script must be saved before approval.** `PUT /projects/{id}/script` is what puts the narration on the server; the editor's "Lưu Kịch Bản" button does that explicitly.
- **Failures are rendered, not swallowed.** Save and approval errors appear in `ScriptStudio`'s status banner. The previous version called `alert()` and discarded the mutation's error, so a rejected Gate 1 approval looked like nothing happening.

## Key Feature Modules

1. **🤖 AI Co-Pilot Command Bar (`Ctrl+K`)** — bilingual (VI/EN) natural-language timeline commands via `POST /timeline/command`.
2. **🔥 Virality Retention Scorer** — hook (first 3 s), pacing, duration and CTA scoring via `POST /script/virality`.
3. **🛡️ Multi-Platform QA & Brand Compliance** — platform verdicts (`POST /qa/platform/verdict`), brand-kit consistency (`POST /qa/brand/verdict`) and fingerprint comparison against a supplied protected set (`POST /qa/copyright/verdict`).
4. **🎨 Thumbnail Candidates & CTR Prediction** — `POST /thumbnail/candidates` returns backend filesystem paths, timestamps, scores and CTR predictions. No route serves those files yet, so the studio shows measurements, not previews.
5. **🎧 Audio Lab & Accessible Captions** — mixer, 5-band EQ, sidechain ducking controls, neural voiceover, and subtitle simplification (`POST /subtitles/simplify`).
6. **📊 Cost Guard & Provenance Audit Trail** — `POST /cost/check` prices a *proposed* plan against the configured budget (there is no spend ledger), and `GET /audit` returns the append-only provenance log with a backend-derived `sha256_hash` per entry.
7. **Two Mandatory Human Review Gates** — Gate 1 (script) and Gate 2 (video), both server-enforced.

## Development & Build Commands

Node.js 18.17+ is required. It is **not installed by default** on the machine this repository was developed on.

```bash
cd frontend

npm install          # or `npm ci` to honour package-lock.json exactly
npm run dev          # Next dev server → http://localhost:3000, proxies /api/* to :8000
npm run type-check   # tsc --noEmit
npm run build        # production build
npm run start        # serve the production build
```

Without Node, this dependency-free structural check still verifies that every import in `src/` resolves and every named import is actually exported:

```bash
python ../scripts/frontend_imports.py
```

## Known gaps

1. **Not reachable from the backend.** The vanilla studio owns `/`. Serving the Next app would need a mount, a proxy, or a port convention change — see `docs/frontend/01-KIEN-TRUC-VA-TECH-DEBT.md`.
2. **No ESLint.** `npm run lint` is defined in `package.json` but ESLint is not a dependency and no config file exists.
3. **No tests.** No unit, component or end-to-end test suite for either client.
4. **No CI job.** A frontend regression cannot fail the build.
5. **Some screens still need backend verification**, and a few capabilities have no endpoint at all (audio perception/ducking, stem splitting, setting a project poster). Those screens now say so on-screen rather than displaying fabricated values — the reasoning is recorded in `docs/frontend/02-DANH-SACH-LOI.md`.

The full audit — architecture and tech debt, an evidenced bug list, the security and trust model, feature proposals, and the upgrade/testing roadmap — lives in [`../docs/frontend/`](../docs/frontend/README.md).
