---
name: generate-script
description: >-
  Ask the AI provider chain to draft a narration script for a project
  (endpoint POST /projects/{id}/script/generate). Use when the user asks for
  an AI draft/script/gen kịch bản for an existing project.
---

# Generate an AI script draft

Prerequisite: the dev server runs on :8080 and a project exists (use the
`create-project` skill to make one).

1. Call the draft endpoint:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/script/generate
```

2. Expected outcomes:
   - HTTP 200 → the project now has a script but `status` is `script_review`
     and `source_rights_confirmed` is `false` (AI drafts never auto-confirm
     rights — by design).
   - HTTP 503/502 → every provider failed (e.g. local MoneyPrinterTurbo is
     not running / no STRONG LLM configured). Tell the user the system degraded gracefully.
3. Report the provider + tier used (returned in the 200 body? read the
   `/health` body for diagnostics) and remind the user a human must approve the
   script before production.