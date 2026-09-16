---
name: create-project
description: >-
  Create a new production project in the AI Content Factory via the HTTP API.
  Use when the user wants to add a project/topic/idea, or to set up a project
  before generating a script.
---

# Create a project through the API

Prerequisite: the dev server runs at `http://127.0.0.1:8080` (start it with
the `run-dev` skill if needed).

1. Gather three values from the user (or take them from context):
   - `name` — max 120 characters, e.g. "The quiet power of small habits"
   - `topic` — max 500 characters, the story angle/source to explore
   - `target_language` — default `vi`; `duration_target_seconds` — default 45
2. POST to the API:

```bash
curl -s -X POST http://127.0.0.1:8080/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Demo",
    "topic": "Why morning light changes how cities feel",
    "target_language": "vi",
    "duration_target_seconds": 45
  }'
```

3. A successful create returns HTTP 201 with `"status": "draft"` and an `id`.
4. Report the project id to the user. The next step is usually the
   `generate-script` skill.

Tip: on Windows PowerShell use `curl.exe` instead of `curl`.