---
name: approve-script
description: >-
  Walk a project through the mandatory human approval gate and start
  generation: update the script, confirm source rights, approve, then
  POST /projects/{id}/generate. Use when the user approves a script or asks
  to start production.
---

# Approve a script and start production

This is the heart of the human-in-the-loop guarantee — do NOT skip the rights
confirmation step below.

> **Note:** The backend is planned but not yet implemented. These steps define
> the target workflow and become usable once the API exists.

1. Update the script and confirm source rights (both in one call):

```bash
curl -s -X PUT http://127.0.0.1:8080/projects/<PROJECT_ID>/script \
  -H 'Content-Type: application/json' \
  -d '{
    "script": "<the final narration text>",
    "source_rights_confirmed": true
  }'
```

`source_rights_confirmed: true` is a legal assertion (source owned / licensed /
public domain / reference-only). Only set it when the user explicitly
confirms, or the script is clearly original.

2. Approve the script gate:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/approvals \
  -H 'Content-Type: application/json' \
  -d '{"stage": "script", "status": "approved", "comment": "Approved via agent"}'
```

3. Start generation:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/generate
```

4. Verify the final state is `generating`; report the transition chain to the
   user: `script_review → script_approved → generating`.

Tip: on Windows PowerShell use `curl.exe` instead of `curl`.