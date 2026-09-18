# Pro NLE Studio: `frontend/`

A commercial-grade video creation suite built with **Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + Zustand + Motion**, inspired by premier paid editing software (**CapCut Pro Desktop, Adobe Premiere Pro CC, DaVinci Resolve 19 Studio, Runway Gen-3, and Descript**).

---

## Technology Stack

- **Framework**: Next.js 14 (App Router) with React 18 / 19
- **Language**: TypeScript (strict typing enabled)
- **Styling**: Tailwind CSS with Obsidian Dark palette (`#090a0f`, `#12151f`, `#181d2a`) and Cyber Neon accents (`#00f0ff`, `#8b5cf6`, `#10b981`, `#f59e0b`)
- **UI Components**: shadcn/ui primitives built on Radix UI (`Button`, `Card`, `Dialog`, `Tabs`, `Slider`, `Badge`, `Progress`, `Table`, `Tooltip`, `Separator`)
- **Server State**: TanStack Query v5 (`@tanstack/react-query`) for API fetching, caching, and mutations
- **Client & NLE State**: Zustand v5 (`zustand`) for player transport, multi-track timeline, project state, and modal management
- **Animations**: Motion / Framer Motion (`framer-motion`) for the Spotlight `Ctrl+K` bar, VU meters, modal dialogs, and smooth transitions

---

## Directory Organization

```text
frontend/
├── package.json            # Scripts & dependencies
├── tsconfig.json           # TypeScript configuration with @/* path aliases
├── next.config.mjs         # API proxy rewrites & Next.js config
├── tailwind.config.ts      # NLE design system tokens & animation keyframes
├── components.json         # shadcn/ui configuration
├── README.md               # Frontend architecture guide
├── index.html              # Vanilla/FastAPI fallback entry (satisfies smoke test)
├── style.css               # Base stylesheet
└── src/
    ├── types/              # Domain & API TypeScript definitions
    │   ├── project.ts      # Project, Scene, Script, TimingPlan
    │   ├── api.ts          # QA, Virality, Audit, Thumbnails, NL Command
    │   └── timeline.ts     # Tracks, Clips, Markers
    ├── lib/
    │   ├── utils.ts        # cn() helper & SMPTE timecode formatter
    │   └── api-client.ts   # Unified fetch API client
    ├── stores/             # Zustand reactive stores
    │   ├── useProjectStore.ts   # Active project & review gates
    │   ├── usePlayerStore.ts    # Transport, VU meter, safe zones
    │   ├── useTimelineStore.ts  # Multi-track lanes, clip zoom, active scene
    │   └── useUIStore.ts        # Active tab & modal visibility
    ├── hooks/              # TanStack Query & Mutation hooks
    │   ├── useProjects.ts       # Project CRUD & review gate approvals
    │   ├── useScriptEngine.ts   # Virality scoring & script updates
    │   ├── useTimelineCommands.ts # Natural language Co-Pilot command runner
    │   ├── useQA.ts             # Platform, Brand Kit & Copyright scanner
    │   ├── useThumbnails.ts     # Multi-style CTR thumbnail generator
    │   ├── useMediaLibrary.ts   # Semantic search & dHash deduplication
    │   └── useAuditCost.ts      # Cost Guard & Provenance Audit Trail
    ├── components/
    │   ├── ui/             # Reusable shadcn/ui primitives
    │   ├── layout/         # Topbar navigation & status chips
    │   ├── copilot/        # Spotlight / Raycast Ctrl+K Command Bar
    │   ├── player/         # Canvas player with Audition Dual VU meters
    │   ├── script/         # Script Studio with 4-part virality retention card
    │   ├── timeline/       # Multi-track NLE timeline visualizer
    │   ├── qa/             # Compliance & Brand Kit modal
    │   ├── thumbnails/     # AI Auto-Thumbnail Studio & CTR predictor
    │   ├── audit/          # Cost Guard & Provenance Audit Trail modal
    │   ├── audio/          # Sidechain Auto Music Ducking controls
    │   ├── captions/       # Accessible Subtitle Simplifier
    │   └── media/          # Semantic media search & dHash detector
    └── app/
        ├── layout.tsx      # Root layout with QueryClientProvider
        ├── page.tsx        # Studio dashboard orchestrator
        └── globals.css     # Tailwind directives & custom scrollbars
```

---

## Key Feature Modules

1. **🤖 AI Co-Pilot Command Bar (`Ctrl+K`)**:
   - Floating Spotlight/Raycast modal with quick-prompt chips.
   - Translates bilingual (VI/EN) natural language commands into timeline mutations via `POST /timeline/command`.
2. **🔥 Virality Retention Scorer**:
   - Evaluates Hook (first 3s), Pacing, Duration, and CTA conversion via `POST /script/virality`.
3. **🛡️ Multi-Platform QA & Brand Compliance**:
   - Automated checklist for TikTok, Shorts, Reels, 16:9, and Facebook (`POST /qa/platform`).
   - Brand Kit consistency verification (`POST /qa/brand`).
   - SHA-256 asset provenance scanner (`POST /qa/copyright`).
4. **🎨 AI Auto-Thumbnail & CTR Predictor**:
   - Generates candidate frames in Neon Gamer, Tech Minimal, and Vlog Bold styles (`POST /thumbnail/generate`).
   - Displays CTR prediction scores (e.g. `🔥 15.2% High CTR`).
5. **🎧 Sidechain Auto Music Ducking & Accessible Captions**:
   - Real-time ducking of background music during narration (`POST /render/duck`).
   - Vocabulary simplification for cognitive accessibility (`POST /subtitles/simplify`).
6. **📊 Cost Guard & Provenance Audit Trail**:
   - Budget tracking by AI model (`POST /cost/check`).
   - Immutable audit logs with SHA-256 hashes (`GET /audit`).
7. **Two Mandatory Human Review Gates**:
   - **Gate 1 (Script Approval)**: Protects rights confirmation before video generation.
   - **Gate 2 (Video Approval)**: Mandates operator quality check before distribution.

---

## Development & Build Commands

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server (runs on http://localhost:3000)
npm run dev

# Run TypeScript strict type-checking
npm run type-check

# Build production bundle
npm run build
```
