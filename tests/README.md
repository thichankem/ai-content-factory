# Test Suite: `tests/`

The pytest suite for the **AI Content Factory**. It covers state-machine adherence, HTTP contract fidelity, the domain engines, and the structural shape of the codebase itself.

---

## Measured status

| | |
| :--- | :--- |
| Test modules | **67** — 66 `test_*.py` plus `conftest.py` |
| Tests collected | **1 087** |
| Result | **All pass** — the full run exits 0 |
| Command | `python -m pytest` |

Earlier revisions of this file reported ~634 tests and 11 `ffmpeg` failures. Both numbers are obsolete: the suite has grown, and `ffmpeg` is no longer a blocker (see below).

```bash
python -m pytest                      # the whole suite
python -m pytest tests/test_audio_effects.py -q
```

The suite is heavy. It loads OCR (`easyocr`/`torch`) and speech models, and a few tests reach the network through `yt-dlp`, so a full run takes minutes rather than seconds and can take considerably longer on a loaded machine. Modules that do not need those models are still fast.

---

## How `ffmpeg` is resolved

`ffmpeg` is the one real external dependency of the suite. `hardware.require_ffmpeg()` resolves it in this order:

1. the explicit path the caller passes (from the `ffmpeg_binary` setting),
2. `PATH`,
3. **a build bundled inside an installed package** — `imageio-ffmpeg` ships one and `hardware._bundled_ffmpeg_candidates()` finds it.

Step 3 is what closed the old gap. Before it, `require_ffmpeg` stopped at `shutil.which("ffmpeg")` and every ffmpeg-backed test failed on a virtualenv that already contained a perfectly good binary that nothing consulted. `resolve_ffmpeg()` — the function used for *reporting* on the machine — deliberately still returns only `PATH`/explicit results, so the capability report never claims a build the machine does not have.

Regression coverage lives in `tests/test_production.py`:

- `test_require_ffmpeg_falls_back_to_a_bundled_build`
- `test_require_ffmpeg_prefers_path_over_bundled`
- `test_require_ffmpeg_still_raises_when_nothing_is_found`
- `test_resolve_ffmpeg_reports_only_what_is_on_path`

A test must not silently skip on a missing binary when it can instead be pointed at the bundled one.

---

## Test module inventory

### Contracts and guards

| Module | Focus |
| :--- | :--- |
| [`test_state_machine.py`](test_state_machine.py) | Pure transition logic, legal steps, conflict rejection |
| [`test_api.py`](test_api.py) | FastAPI endpoint contracts, status codes, payload validation, negative paths |
| [`test_frontend_contract.py`](test_frontend_contract.py) | **The executable definition of "the backend serves the frontend"** — drives the real pipeline over HTTP with the exact payloads the clients send and asserts the exact fields they read. Field drift here is silent in production (a `NaN` width, a script editor silently falling back to its placeholder), which is why it is pinned verbatim |
| [`test_architecture.py`](test_architecture.py) | Structural guards: module line budget, disjoint mixins, reachable mixin methods, the model/service re-export surface, and **no engine re-implementing a shared `params`/`pixels`/`catalog` helper**. Also pins the behaviour of those three modules (coercion, error types, RGB maths, catalogue grouping), so the shared surface cannot drift silently |
| [`test_domain.py`](test_domain.py) | Core domain models and invariants |
| [`test_config.py`](test_config.py) | Settings loading, env prefix behaviour, defaults |
| [`test_store.py`](test_store.py) | Store concurrency, compare-and-save, conflict detection |
| [`test_mcp_connectivity.py`](test_mcp_connectivity.py) | The MCP server's tool contract over a real client session |

### Lifecycle and production

| Module | Focus |
| :--- | :--- |
| [`test_production.py`](test_production.py) | The production worker: generation, ducking, publishing policy, ffmpeg resolution |
| [`test_render.py`](test_render.py) | ffmpeg rendering and static serving of the produced file |
| [`test_tts.py`](test_tts.py) | Narration synthesis and published-policy preservation |
| [`test_voice_engine.py`](test_voice_engine.py) | Speech chain: presets, encode/decode round-trips, ducking mixes |
| [`test_timeline.py`](test_timeline.py), [`test_timeline_api.py`](test_timeline_api.py) | NLE operations (trim, ripple, speed, duration fitting) and their HTTP surface |
| [`test_workflow.py`](test_workflow.py), [`test_workflow_api.py`](test_workflow_api.py) | DAG construction, cycle detection, checklist validation, background execution |
| [`test_video.py`](test_video.py) | Video-project assembly and revision handling |

### Audio, image and video engines

| Module | Focus |
| :--- | :--- |
| [`test_audio_effects.py`](test_audio_effects.py) | All 32 DSP effects, and the **frequency-response** assertions that pin the RBJ high/low-pass fixes |
| [`test_audio_analysis.py`](test_audio_analysis.py) | Waveform, spectrogram, dominant frequency, clipping, noise floor, phase correlation |
| [`test_audio_assist.py`](test_audio_assist.py) | Plain-language description, the operation catalogue, the mastering chain |
| [`test_audio_separation.py`](test_audio_separation.py) | Two- and three-stem splits, per-band energy, adapter registration |
| [`test_denoise.py`](test_denoise.py) | Spectral gating: tone preservation, noise suppression, profile learning |
| [`test_sfx.py`](test_sfx.py) | Every synthesised sound effect and its catalogue |
| [`test_ai_audio.py`](test_ai_audio.py) | Dubbing / voice-clone adapter contract and its failure mode |
| [`test_photo_ops.py`](test_photo_ops.py), [`test_photo_assist.py`](test_photo_assist.py) | Photo operations, detail work, the image accessibility layer |
| [`test_image_engine.py`](test_image_engine.py), [`test_image_session.py`](test_image_session.py) | Image op pipeline and the non-destructive undo/redo sessions |
| [`test_video_effects.py`](test_video_effects.py), [`test_video_assist.py`](test_video_assist.py) | Frame effects and the video accessibility layer |
| [`test_ai_video_editor.py`](test_ai_video_editor.py) | The vision-driven editor |
| [`test_commercial_editing_suite.py`](test_commercial_editing_suite.py) | Keyframe math, grades, shaders, multi-aspect rendering |

### Media, perception and vision

| Module | Focus |
| :--- | :--- |
| [`test_media.py`](test_media.py), [`test_media_cache.py`](test_media_cache.py), [`test_media_db.py`](test_media_db.py), [`test_media_tools.py`](test_media_tools.py) | Media library, metadata, caching, the media database, tool wrappers |
| [`test_perception.py`](test_perception.py) | Silence/pace detection, music-mood classification, loudness/peak measurement |
| [`test_vision.py`](test_vision.py) | Frame scoring and vision-provider behaviour |
| [`test_sandbox.py`](test_sandbox.py) | Sandboxed execution boundaries |
| [`test_cache.py`](test_cache.py) | Content-addressed checkpoints |
| [`test_youtube.py`](test_youtube.py) | Search, download and the transcript cascade (VTT parsing, subtitle reuse, whisper fallback) |
| [`test_cloud.py`](test_cloud.py) | Local / memory / S3 media storage backends |

### Knowledge, QA and growth

| Module | Focus |
| :--- | :--- |
| [`test_documents.py`](test_documents.py), [`test_search.py`](test_search.py), [`test_library.py`](test_library.py) | Federated search, ranking, FTS5 index |
| [`test_research.py`](test_research.py) | Grounded research bundles and fact reconciliation |
| [`test_knowledge_qa.py`](test_knowledge_qa.py) | Grounded Q&A with citations, URL ingestion |
| [`test_qa_api.py`](test_qa_api.py), [`test_qa_service.py`](test_qa_service.py) | Platform rules, brand kit, copyright fingerprints, ducking, thumbnails. `test_qa_service.py` is also where the service-layer integration and provider-double behaviour live |
| [`test_compliance.py`](test_compliance.py) | Monetisation-safety scoring and the sensitivity linter |
| [`test_seo_engine.py`](test_seo_engine.py), [`test_seo_validation.py`](test_seo_validation.py) | The 70-signal model, optimiser, A/B statistics, input validation |
| [`test_external_ingest.py`](test_external_ingest.py) | Importing external AI media and binding it to scenes |
| [`test_disaster_niche.py`](test_disaster_niche.py) | The history/disaster specialisation: sources, reconciliation, safety |
| [`test_recook.py`](test_recook.py) | Re-cook pipeline from an ingested reference clip |
| [`test_simple_subtitles.py`](test_simple_subtitles.py) | Accessibility simplification, synonym matching, shortening |
| [`test_nl_timeline.py`](test_nl_timeline.py) | Natural-language command parsing, VI/EN patterns, scene resolution |
| [`test_campaign.py`](test_campaign.py) | Multi-platform campaign synthesis, short extraction, export packaging |
| [`test_script_engine.py`](test_script_engine.py) | Drafting, section budgeting, timing plans, style preset compilation |
| [`test_presets.py`](test_presets.py) | Preset loading, JSON/Markdown parsing, override and delete semantics |
| [`test_agent_bridge.py`](test_agent_bridge.py), [`test_agent_tools.py`](test_agent_tools.py), [`test_agents.py`](test_agents.py) | Markdown briefs, the 110-tool registry, agent adapters |
| [`test_providers.py`](test_providers.py), [`test_resources.py`](test_resources.py), [`test_smart.py`](test_smart.py) | Provider chain, circuit breakers, resource admission, smart edits |

---

## Hermeticity & Mocking Rules

1. **No external network calls.** `conftest.py` builds deterministic, fully offline settings with every provider disabled (`template_enabled`, `money_printer_enabled`, `strong_llm_enabled`, `documents_web_enabled` and the rest). Search providers (arXiv, Wikipedia, Crossref) and TTS services are exercised through in-memory doubles.
2. **Temporary directories.** Filesystem artifacts, SQLite indexes and audio/video files use pytest's `tmp_path` so runs cannot pollute each other.
3. **Preset safety.** Tests that create or modify presets clean up afterwards, so the user's `presets/` workspace is never left dirty.
4. **`ffmpeg` is the one real external dependency** — and it is resolved through the three-step fallback above rather than assumed to be on `PATH`.

---

## Running the Quality Gates

From the repository root:

```bash
# 1. Lint (src + tests; scripts/ is not covered by CI)
python -m ruff check src tests

# 2. Formatting
python -m ruff format --check src tests

# 3. Static types
python -m mypy src

# 4. Unit + integration tests
python -m pytest

# 5. End-to-end HTTP smoke test (needs a server on a free port)
python scripts/smoke.py --port 8016
```

### Current measured status

| Gate | Result |
| :--- | :--- |
| `ruff check src tests` | **0 findings** |
| `ruff format --check src tests` | **220 files already formatted** |
| `mypy src` | **0 issues in 149 source files** |
| `pytest` | **1 087 tests, all pass** (exit 0) |
| `scripts/smoke.py` | **64 / 64 checks pass** |
| `ruff check scripts` | 253 findings — `scripts/` is deliberately outside the CI job for now |

Do not describe a gate as green unless the command above was actually run; the numbers in this file were re-measured after the backend refactor (shared `params`/`pixels`/`catalog` modules, `services/studio.py` split out of `services/production.py`) and will drift as the tree changes.
