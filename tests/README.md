# Test Suite: `tests/`

The pytest suite for the **AI Content Factory**. It covers state-machine adherence, HTTP contract fidelity, the domain engines, and the structural shape of the codebase itself.

---

## Measured status

| | |
| :--- | :--- |
| Test modules | **50** (49 `test_*.py` plus `conftest.py`) |
| Test functions | **~634** (`def test_` across the suite) |
| Passing | ~623 |
| **Failing** | **11** — every one for the same environmental reason |

All 11 failures are `ffmpeg`-related:

```text
tests/test_production.py::test_ffmpeg_binary_is_available
tests/test_production.py::test_duck_music_under_speech_produces_output
tests/test_production.py::test_duck_music_wrapper
tests/test_qa_api.py::test_render_duck_produces_output
tests/test_render.py::test_render_endpoint_persists_and_serves_webm
tests/test_voice_engine.py::test_process_voice_podcast_roundtrip
tests/test_voice_engine.py::test_process_voice_custom_params
tests/test_voice_engine.py::test_unknown_preset_raises
tests/test_voice_engine.py::test_garbage_audio_raises
tests/test_voice_engine.py::test_encode_decode_roundtrip_preserves_duration
tests/test_voice_engine.py::test_duck_music_mixes_and_returns_audio
```

**Cause.** `content_factory/audio.py::ffmpeg_binary()` resolves `ffmpeg` with `shutil.which("ffmpeg")` and raises `RuntimeError("ffmpeg is required for music ducking.")` when it is absent. No `ffmpeg` is on `PATH` on this machine — even though the virtualenv already ships a bundled binary at `imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe` that nothing consults.

**Two ways out, both small.** Put `ffmpeg` on `PATH`, or make `ffmpeg_binary()` fall back to `imageio_ffmpeg.get_ffmpeg_exe()`. The second is the better fix: it removes the manual install step for every contributor and makes the failure mode impossible.

Until then, run the suite excluding the ffmpeg-dependent modules:

```bash
python -m pytest --deselect tests/test_production.py \
                 --deselect tests/test_render.py \
                 --deselect tests/test_voice_engine.py \
                 --deselect tests/test_qa_api.py::test_render_duck_produces_output
```

---

## Test module inventory

### Contracts and guards

| Module | Focus |
| :--- | :--- |
| [`test_state_machine.py`](test_state_machine.py) | Pure transition logic, legal steps, conflict rejection |
| [`test_api.py`](test_api.py) | FastAPI endpoint contracts, status codes, payload validation, negative paths |
| [`test_frontend_contract.py`](test_frontend_contract.py) | **The executable definition of "the backend serves the frontend"** — drives the real pipeline over HTTP with the exact payloads the clients send and asserts the exact fields they read. Field drift here is silent in production (a `NaN` width, a script editor silently falling back to its placeholder), which is why it is pinned verbatim |
| [`test_architecture.py`](test_architecture.py) | Structural guards: module line budget, disjoint mixins, reachable mixin methods, the model/service re-export surface |
| [`test_domain.py`](test_domain.py) | Core domain models and invariants |
| [`test_config.py`](test_config.py) | Settings loading, env prefix behaviour, defaults |
| [`test_store.py`](test_store.py) | Store concurrency, compare-and-save, conflict detection |

### Lifecycle and production

| Module | Focus |
| :--- | :--- |
| [`test_production.py`](test_production.py) | The production worker: generation, ducking, publishing policy |
| [`test_render.py`](test_render.py) | ffmpeg rendering and static serving of the produced file |
| [`test_tts.py`](test_tts.py) | Narration synthesis and published-policy preservation |
| [`test_voice_engine.py`](test_voice_engine.py) | Speech chain: presets, encode/decode round-trips, ducking mixes |
| [`test_timeline.py`](test_timeline.py), [`test_timeline_api.py`](test_timeline_api.py) | NLE operations (trim, ripple, speed, duration fitting) and their HTTP surface |
| [`test_workflow.py`](test_workflow.py), [`test_workflow_api.py`](test_workflow_api.py) | DAG construction, cycle detection, checklist validation, background execution |
| [`test_video.py`](test_video.py) | Video-project assembly and revision handling |

### Content engines

| Module | Focus |
| :--- | :--- |
| [`test_script_engine.py`](test_script_engine.py) | Drafting, section budgeting, timing plans, style preset compilation |
| [`test_presets.py`](test_presets.py) | Preset loading, JSON/Markdown parsing, override and delete semantics |
| [`test_campaign.py`](test_campaign.py) | Multi-platform campaign synthesis, short extraction, export packaging |
| [`test_nl_timeline.py`](test_nl_timeline.py) | Natural-language command parsing, VI/EN patterns, scene resolution |
| [`test_recook.py`](test_recook.py) | Re-cook pipeline from an ingested reference clip |
| [`test_simple_subtitles.py`](test_simple_subtitles.py) | Accessibility simplification, synonym matching, shortening |
| [`test_disaster_niche.py`](test_disaster_niche.py) | The history/disaster specialisation: sources, reconciliation, safety |
| [`test_on_this_day`](test_research.py) *(in `test_research.py`)* | Calendar lookups and grounded bundle assembly |

### Media, vision and perception

| Module | Focus |
| :--- | :--- |
| [`test_media.py`](test_media.py), [`test_media_cache.py`](test_media_cache.py), [`test_media_tools.py`](test_media_tools.py) | Media library, metadata, caching, tool wrappers |
| [`test_perception.py`](test_perception.py) | Silence/pace detection, music-mood classification, loudness/peak measurement |
| [`test_vision.py`](test_vision.py) | Frame scoring and vision-provider behaviour |
| [`test_image_engine.py`](test_image_engine.py) | Image operations and composition |
| [`test_ai_video_editor.py`](test_ai_video_editor.py) | The vision-driven editor |
| [`test_sandbox.py`](test_sandbox.py) | Sandboxed execution boundaries |
| [`test_cache.py`](test_cache.py) | Content-addressed checkpoints |

### Knowledge, QA and growth

| Module | Focus |
| :--- | :--- |
| [`test_documents.py`](test_documents.py), [`test_search.py`](test_search.py), [`test_library.py`](test_library.py) | Federated search, ranking, FTS5 index |
| [`test_research.py`](test_research.py) | Grounded research bundles and fact reconciliation |
| [`test_qa_api.py`](test_qa_api.py), [`test_qa_service.py`](test_qa_service.py) | Platform rules, brand kit, copyright fingerprints, ducking, thumbnails. `test_qa_service.py` is also where the service-layer integration and provider-double behaviour live |
| [`test_compliance.py`](test_compliance.py) | Monetisation-safety scoring and the sensitivity linter |
| [`test_seo_engine.py`](test_seo_engine.py), [`test_seo_validation.py`](test_seo_validation.py) | The 70-signal model, optimiser, A/B statistics, input validation |
| [`test_external_ingest.py`](test_external_ingest.py) | Importing external AI media and binding it to scenes |
| [`test_commercial_editing_suite.py`](test_commercial_editing_suite.py) | Keyframe math, grades, shaders, multi-aspect rendering |
| [`test_agent_bridge.py`](test_agent_bridge.py), [`test_agent_tools.py`](test_agent_tools.py), [`test_agents.py`](test_agents.py) | Markdown briefs, the tool registry, agent adapters |
| [`test_providers.py`](test_providers.py), [`test_resources.py`](test_resources.py), [`test_smart.py`](test_smart.py) | Provider chain, circuit breakers, resource admission, smart edits |

---

## Hermeticity & Mocking Rules

1. **No external network calls.** `conftest.py` builds deterministic, fully offline settings with every provider disabled (`template_enabled`, `money_printer_enabled`, `strong_llm_enabled`, `documents_web_enabled` and the rest). Search providers (arXiv, Wikipedia, Crossref) and TTS services are exercised through in-memory doubles.
2. **Temporary directories.** Filesystem artifacts, SQLite indexes and audio/video files use pytest's `tmp_path` so runs cannot pollute each other.
3. **Preset safety.** Tests that create or modify presets clean up afterwards, so the user's `presets/` workspace is never left dirty.
4. **`ffmpeg` is the one real external dependency.** Tests that shell out to it are the 11 failures listed above. A test must not silently skip on a missing binary if it can instead be pointed at the bundled one.

---

## Running the Quality Gates

From the repository root:

```bash
# 1. Lint
python -m ruff check src tests scripts

# 2. Formatting
python -m ruff format --check src tests scripts

# 3. Static types
python -m mypy src

# 4. Unit + integration tests
python -m pytest

# 5. End-to-end HTTP smoke test (needs a server)
python scripts/smoke.py --port 8016
```

### Current measured status

| Gate | Result |
| :--- | :--- |
| `ruff check src tests scripts` | **242 findings** — 154 `E501`, 20 `F821`, 8 `E402`, 7 `BLE001`, 6 `PTH202`, … |
| `ruff format --check src tests scripts` | **13 files would be reformatted** |
| `mypy src` | **43 errors in 7 files** (129 checked) |
| `pytest` | **11 failures** out of ~634 (all `ffmpeg`) |

The `ruff` configuration in `pyproject.toml` carries the comment *"Every addition here is a rule the tree passes."* That was true when it was written; it is not true now. The `E501` findings alone (154, against a `line-length = 88`) mean the tree passes neither the linter nor the formatter.

Do not describe these gates as green in a commit message or a plan until the numbers are actually zero.
