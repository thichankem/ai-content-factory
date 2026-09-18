# Test Suite: `tests/`

This directory houses the comprehensive Pytest automated test suite for the **AI Content Factory**, guaranteeing pipeline hermeticity, state machine adherence, and API contract fidelity.

---

## Test Architecture & Categorization

The test suite contains **472+ automated tests** structured into modular modules:

| Test File | Focus Area |
| :--- | :--- |
| [`test_state.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_state.py) | Pure state machine transition logic, legal steps, and conflict rejection. |
| [`test_api.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_api.py) | FastAPI endpoint contracts, status codes, payload validation, and negative paths. |
| [`test_qa_api.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_qa_api.py) | Platform compliance rules, brand kit audits, copyright SHA-256 scanner, ducking, and thumbnails. |
| [`test_nl_timeline.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_nl_timeline.py) | Natural language command parsing, Vietnamese/English regex patterns, scene index resolution, and timeline modifications. |
| [`test_simple_subtitles.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_simple_subtitles.py) | Accessibility subtitle word simplification, synonym matching, and sentence shortening. |
| [`test_timeline.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_timeline.py) | NLE operations: clip trimming, ripple delete, speed changes, duration auto-fitting. |
| [`test_workflow.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_workflow.py) | Node DAG workflow creation, cycle detection, checklist validation, and background execution. |
| [`test_campaign.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_campaign.py) | Multi-platform campaign synthesis, short extraction, and export packaging. |
| [`test_external_ingest.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_external_ingest.py) | Importing external AI media (Kling, Suno, Runway) and linking to project scenes. |
| [`test_script_engine.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_script_engine.py) | Script drafting, section budgeting, timing plans, and style preset compilation. |
| [`test_service.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/tests/test_service.py) | Service layer integration, store persistence, and mock provider interactions. |

---

## Hermeticity & Mocking Rules

1. **No External Network Calls**:
   All unit and integration tests must run in isolated local environments. External search providers (e.g. arXiv, Wikipedia, Crossref) and TTS services are mocked using in-memory adapters or test doubles.
2. **Temporary Directories**:
   File-system artifacts, SQLite index databases, and audio/video files must use Pytest's `tmp_path` fixture to prevent cross-test pollution.
3. **Preset Safety**:
   Tests that create or modify style presets (`presets/*.json`, `presets/*.md`) must clean up after themselves to prevent test pollution in the user workspace.

---

## Running the Quality Gates

Run the test suite and linters from the repository root:

```bash
# 1. Check style and syntax
python -m ruff check src tests scripts

# 2. Check formatting
python -m ruff format --check src tests scripts

# 3. Check static types
python -m mypy src

# 4. Run all unit & integration tests
python -m pytest
```
