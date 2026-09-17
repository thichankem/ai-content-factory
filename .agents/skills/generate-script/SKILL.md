---
name: generate-script
description: >-
  Ask the AI provider chain to draft a narration script for a project
  (endpoint POST /projects/{id}/script/generate). Use when the user asks for
  an AI draft/script for an existing project.
---

# Generate an AI script draft

Prerequisite: the dev server runs on :8080 and a project exists (use the
`create-project` skill to make one).

1. (Optional but recommended) Run a research pass first so the draft is
   grounded in reference sources:

```bash
curl -s -X POST "http://127.0.0.1:8080/projects/<PROJECT_ID>/research?web=true"
```

   This gathers a bundle of sources (curated library + live federated web
   results from arXiv, Crossref, Gutenberg, Open Library, Wikipedia, and
   Internet Archive) plus key facts and stores it on the project. Generation
   reuses it automatically, so this step is only needed to preview the
   material. Use the `search-documents` skill to browse and download
   documents first.

2. Call the draft endpoint:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/script/generate
```

2. Expected outcomes:
   - HTTP 200 → the project now has a script, `status` is `script_review`,
     and `source_rights_confirmed` is `false`. AI drafts never auto-confirm
     rights — by design. The body includes `provider_used` (usually
     `template` unless a real provider is configured) and a `research` bundle
     with the sources and key facts the draft was grounded on.
   - HTTP 503 → every provider failed (e.g. the template provider is disabled
     and the local MoneyPrinterTurbo / strong LLM are unavailable). The system
     degrades gracefully; report the failure to the user. See `.env.example`
     for enabling a provider.
3. Report which provider and tier handled the request (the project body
   includes `provider_used`; the `/health` body shows breaker states) and
   remind the user that a human must approve the script before production.

Tip: on Windows PowerShell use `curl.exe` instead of `curl`.