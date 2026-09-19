# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

The **AI Content Factory** — an AI-assisted short-form video pipeline with two
mandatory human review gates (script approval, final video approval).

The full pipeline is implemented: a FastAPI backend
(`src/content_factory`), a pytest suite (`tests/`), helper scripts (`scripts/`),
and CI (`.github/workflows/ci.yml`). It covers project creation, AI script
drafting (with a built-in offline template provider), the mandatory script
approval gate, a simulated production worker, the mandatory final-video approval
gate, and publishing.

### There are two frontends. Know which one you are editing.

- **`frontend/index.html` + `app.js` + `editor.js` + `flow.js` + `style.css`**
  (15,650 lines) — the **vanilla studio**. FastAPI serves it at `/`
  (`api/routers/index.py`), it needs no build step, and it is what the smoke test
  covers. **This is the product.**
- **`frontend/src/**`** (97 files, 17,726 lines) — a **Next.js 14 rewrite** on its
  own server at port 3000. FastAPI does not mount or proxy it and CI does not
  build it.

Do not assume a change to one affects the other; they share no code, no styles and
no build. `docs/frontend/` audits both.

## Conventions

- Documentation and skill files are written in English. The one exception is
  `docs/KE-HOACH-TONG-THE.md`, the operator's master plan, which is kept in
  Vietnamese because the operator writes in Vietnamese.
- Skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter
  (`name`, `description`, optional `allowed-tools`).
- Configuration templates belong in `.env.example`; never commit a real
  `.env`.
- Keep agent-facing instructions in the skills; keep the overall picture in
  `README.md`.
- The state machine in `src/content_factory/state.py` is authoritative — do
  not bypass it in the service layer.
- Source rights are never auto-confirmed, by any code path, for any provider
  or external agent.
- **Never let the UI assert something that did not happen.** A number an operator
  will act on — a readiness score, a confirmation, a spend figure, a hash, an
  audit row — must come from the server, and a failed request must read as a
  failure. Three shapes of this bug were found and removed across the frontend
  and are not to be reintroduced:
  - *fabricated placeholder data*: invented demo records shown as real results
    (fake audit rows with fake SHA-256 hashes, a hardcoded SEO score badged
    “measured”, a demo script presented as the project's script, a hardcoded
    media bin).
  - *a success path in a `catch`*: reporting completion from the error branch, so
    a failure looked finished.
  - *`alert()` announcing work*: a button that popped a confirmation while
    calling nothing, or while swallowing the mutation's rejection.

  An empty state, a disabled control with a reason, or an error message is always
  the correct rendering. Client state is never the authority for a gate.

## Backend layout

- `src/content_factory/models/` holds the Pydantic contracts, one module per
  domain; `models/__init__.py` re-exports all of them, so import from
  `content_factory.models` and add the class to the module that matches its
  domain.
- `src/content_factory/services/` holds the service layer as one mixin per
  domain over a shared `ServiceContext`. Add methods to the matching mixin; if a
  method calls another layer, add that layer to the mixin's base list rather
  than reaching across the composition. `service.py` is only a compatibility
  facade.
- Within it, `studio.py` is the image/voice/audio surface and `production.py`
  (`ProductionMixin(StudioMixin)`) owns the video pipeline and the ffmpeg
  export. A new photo or audio operation goes in `studio.py`; a new render or
  publish step goes in `production.py`.
- Compute policy is split the same way, read vs decide:
  `compute.py` holds the value types (`JobKind`, `HardwareProfile`,
  `FfmpegBuild`, `CodecChoice`, `Decision`), `hardware.py` contains only
  *readings* of the machine, and `resources.py` turns those readings into policy
  (`ResourceGovernor`). An encoder is a *(binary, encoder)* pair, never a name —
  builds target different NVENC APIs, so `resolve_hardware_encoder()` opens every
  candidate for real before believing it. See `docs/COMPUTE-RESOURCES.md`.
- Shared helpers live in one module (or the module that owns the concept) —
  never copy a tokenizer, slug, coercer or pixel helper into a second place.
  The shared homes are:
  - `text.py` — tokenizers, slugs, title keys.
  - `params.py` — reading numbers, flags and RNG seeds out of an untyped
    parameter mapping (a dict *or* an object with `.params`).
  - `pixels.py` — `as_rgb`, `rgb_array`, `to_image`, `to_uint8`, `luminance`,
    `remap`.
  - `catalog.py` — the `{name, description, params}` entry shape and the
    grouped catalogue the accessibility layers return.
  - `subtitles.py` — WebVTT parsing (caption text *and* cue timings).
  - `downloads.py` — "is this download really media?" verification.
  - `api/errors.py` — the domain-error to HTTP-status table.

  An engine may still bind a shared helper to its own exception type, but only
  by delegating to the shared implementation (see `audio_effects._num`).
- `tests/test_architecture.py` enforces these rules: disjoint mixins, methods
  reachable from the composed service, a module line budget, the
  `models`/`services` re-export surface, and that no engine re-implements a
  shared helper. Run it after any structural change.
- `agent_tools.py` sits close to its 1900-line registry ceiling (~1884). Adding
  a tool means first moving a whole handler *family* into a sibling module, the
  way `agent_audio.py`, `agent_video.py` and `agent_compute.py` were. It cannot
  be split by spec list alone: `_DISCOVERY` borrows `_h_list_media`/`_h_get_media`,
  `_TIMELINE` borrows `_h_auto_cut_to_beat`, and `_IMAGE` borrows
  `_h_compose_images`/`_h_collage_images`, so those handlers must move with the
  lists that use them or the manifest order changes.
- A sibling module builds its specs through a `*_tool_specs()` function that
  imports `ToolSpec`/`_p` lazily from `agent_tools`, and the parent splices it in
  at the *same* position in `TOOL_SPECS`, so the published manifest order never
  moves.
- An engine raises a `ValueError` subclass (or `MediaToolArgumentError`) for a
  request it cannot serve: `api/errors.py` turns that into a 4xx **with the
  message** app-wide. Raising a bare `Exception` (or letting a `TypeError`
  escape) hands the caller an empty 500, which is what the audit's L3 was about.
  New error families go in the table in `api/errors.py`, not in a router's
  `except` clause.
- New tools must be reachable: `tests/test_tool_dispatch_contract.py` dispatches
  **every** tool in the manifest with a minimal argument set and fails on any
  undeclared failure. Two tools were dead for the life of the project because
  nothing ever called them.
- A required text field that two kinds of caller spell two different ways uses
  `models.common.TwinSpelling`: declare `PRIMARY` and `ALIAS`, expose whichever
  accessor name the callers already use, and let the base class own the
  "either one, exactly one" rule. Do not hand-roll that validator again.

## The contract with the web clients

`frontend/` (the studio) and `frontend/app.js` (the legacy dashboard) read
specific field names out of specific responses. A mismatch there is silent — a
`NaN` width, an editor stuck on its placeholder, a cost card reading `$0.00` —
so `tests/test_frontend_contract.py` drives the real pipeline over HTTP with the
payloads the clients actually send and asserts the fields they actually read.
Change a request model or a response model and run that file.

The house rule for a name that genuinely has two spellings is to **serve both**
rather than pick one: canonical fields stay (`script`, `calls`, `text`,
`duration_seconds`) and the client-facing spelling is added beside them
(`raw_script`, `estimated_usage`, `command`, `duration`), either as a real field,
a `@computed_field` alias, or a `TwinSpelling` mixin. Rejecting the spelling a
working client already sends is how a UI breaks without anyone noticing.

## Read this first

`docs/KE-HOACH-TONG-THE.md` is the project's memory: the operator's
requirements, the target architecture, the roadmap phases, the open decisions,
and a change log. Read it before starting work and update it when you finish,
following the template at the bottom of that file.

`docs/TOOLCHAIN.md` lists the optional local media/AI tools;
`scripts/toolcheck.py` reports which are actually installed — run it before
debugging a media failure, because the most common cause is a missing `ffmpeg`.
`docs/AGENT-BRIDGE.md` documents the Markdown contract used with external AI
agents (Claude Code, Codex, DeepSeek, Gemini).

Before claiming a quality gate is green, run it and read the number. The Python
gates are currently **red** — 242 `ruff` findings, 13 unformatted files, 43 `mypy`
errors in 7 files, and 11 `pytest` failures caused by `ffmpeg` not being on
`PATH`. `README.md` carries the full table; do not contradict it without
evidence.

## Workflow

- To add or change a skill, edit the matching `SKILL.md` and keep the
  frontmatter description accurate.
- Anything the operator can tune belongs in a preset file (`presets/*.json`,
  `presets/*.md`) or an environment variable — not as a constant in code.
  `src/content_factory/presets.py` and `script_engine.py` are the reference
  examples.
- After editing Python code, run the quality gates (on Windows use
  `.venv/Scripts/python.exe`, on Linux/macOS/WSL `./.venv/bin/python` or
  `scripts/lint.sh`): `python -m ruff check src tests`,
  `python -m ruff format --check src tests`, `python -m mypy src`, and
  `python -m pytest`.
- The ruff rule set in `pyproject.toml` is wider than the defaults. If you add a
  rule, fix the tree rather than the rule; the `ignore` list carries a reason per
  entry and nothing lands there without one.
- Never run `ruff --select <rule>` to decide whether a `# noqa` is stale:
  `--select` *replaces* the configured set, so every directive in the tree looks
  unused and a `--fix` will delete live ones. Use the plain `ruff check` —
  `RUF100` is enabled and reports genuinely unused directives correctly.
- Before reporting a large task done, run the smoke test: `scripts/smoke.ps1`
  (Windows) or `scripts/smoke.sh` (Linux/macOS/WSL).
- After editing anything under `frontend/src/`, verify it. Node.js is **not**
  installed by default, so `npm` may be missing entirely; fix that first rather
  than editing TypeScript unverified.

  ```bash
  python scripts/frontend_imports.py       # no dependencies; checks every import resolves
  cd frontend && npm run type-check        # tsc --noEmit
  cd frontend && npm run build             # next build
  ```

  `frontend_imports.py` catches deleted modules and renamed exports, which is the
  most common breakage in this tree. It cannot catch a type error, a wrong prop
  or a wrong data shape — those need `tsc`. A change to the Next.js client is not
  verified until `tsc` has run clean.
- The vanilla studio has no test suite and no type system. If you change it, the
  smoke test is your only guard: it asserts that `/` loads and that the pages the
  scripts depend on still respond.
- Do not invent files or commands that do not exist yet. If a step depends on
  unimplemented infrastructure, mark it as planned.