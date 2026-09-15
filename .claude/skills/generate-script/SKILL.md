---
name: generate-script
description: >-
  Ask the AI provider chain to draft a narration script for a project
  (endpoint POST /projects/{id}/script/generate). Use when the user asks for
  an AI draft/script for an existing project.
---

# Generate an AI script draft

> **Note:** The backend is planned but not yet implemented. These steps define
> the target workflow and become usable once the API exists.

Prerequisite: the dev server runs on :8080 and a project exists (use the
`create-project` skill to make one).

1. Call the draft endpoint:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/script/generate
```

2. Expected outcomes:
   - HTTP 200 → the project now has a script, `status` is `script_review`, and
     `source_rights_confirmed` is `false`. AI drafts never auto-confirm rights
     — by design.
   - HTTP 502/503 → every provider failed (e.g. the local MoneyPrinterTurbo
     instance is not running, or no strong LLM is configured). The system
     degrades gracefully; report the failure to the user.
3. Report which provider and tier handled the request (check the `/health`
   body for diagnostics) and remind the user that a human must approve the
   script before production.

Tip: on Windows PowerShell use `curl.exe` instead of `curl`.