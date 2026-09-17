---
name: review-video
description: >-
  Take a project through the final human review gate and publish: wait for
  production to finish, review the video, approve or reject it, then
  POST /projects/{id}/publish. Use when the user reviews/approves a produced
  video or asks to publish.
---

# Review the final video and publish

This is the second mandatory human gate — do NOT publish without explicit
human approval.

1. Confirm production has finished: `GET /projects/<PROJECT_ID>` should show
   `status` `video_review` (the worker runs in the background; poll if it is
   still `generating`). The body includes `video` metadata and a
   `thumbnail_url`.
2. Present the video to the user (thumbnail + duration + format) and ask for
   a verdict.
3. Approve the video gate:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/approvals \
  -H 'Content-Type: application/json' \
  -d '{"stage": "video", "verdict": "approved", "comment": "Approved via agent"}'
```

   On rejection, send `"verdict": "rejected"` — the project stays in
   `video_review` and can be re-rendered via `POST /projects/{id}/generate`.

4. Publish the approved video:

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/publish \
  -H 'Content-Type: application/json' \
  -d '{"platforms": ["youtube"]}'
```

5. Verify the final state is `published`; report the transition chain to the
   user: `video_review → video_approved → published`.

Tip: on Windows PowerShell use `curl.exe` instead of `curl`.