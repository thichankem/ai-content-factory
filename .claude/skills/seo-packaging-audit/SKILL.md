---
name: seo-packaging-audit
description: Use before publishing anything to YouTube, Shorts or TikTok. Scores the publish pack (title, description, tags, hashtags, hook, structure, sound), returns the exact fixes worth the most points, rewrites the pack with a measured gain, and designs the A/B test that proves a change helped. No API key, no platform call.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# SEO Packaging Audit — Score, Fix, Then Prove It

The factory can tell you what a video's packaging is worth **before** it ships,
and — more usefully — whether a change actually helped. Everything below runs
against `http://127.0.0.1:8000` (see `run-dev`), offline and deterministically.

## 1. Discover the rules first, do not assume them

```bash
curl -s http://127.0.0.1:8000/seo/rules | python -m json.tool | head -60
```

`GET /seo/rules` returns each platform's targets (title band and hard max,
description band, keyword zone, hashtag and tag bands, duration band, hook
window, completion/CTR targets, minimum cut rate) **and the full weighted signal
table**. Read it: the score you are about to see is the sum of these signals.

## 2. Score the real project, not a hypothetical

```bash
curl -s -X POST "http://127.0.0.1:8000/projects/{project_id}/seo" \
  -H "Content-Type: application/json" \
  -d '{"platform":"all","keywords":["tàu titanic"],"publish_hour":20}'
```

The report reads the stored project: hook from the script, runtime and cut rate
from the timeline, aspect ratio, caption and music state, chapter markers and the
on-screen text of every scene. `platform: "all"` scores every profile in one
call. A pack you have not built yet can be scored directly with
`POST /seo/score` (or the `seo_score` tool) by passing the fields as `pack`.

How to read the response:

- `score` + `grade` — the headline, 0–100.
- `confidence` — how much of the model could actually be measured. **Low
  confidence is missing information, never a passing grade.** Collect the missing
  field instead of guessing it.
- `blocking` — the only things that cap the score (wrong aspect for a vertical
  surface, a repost watermark, an empty/over-length title). Fix these first.
- `quick_wins` — fixes ranked by the points they are worth. This is the worklist.
- `verdict` + `notes` — plain language, including the platform facts behind it.

## 3. Get the rewrite — and the measured gain

```bash
curl -s -X POST http://127.0.0.1:8000/seo/optimize \
  -H "Content-Type: application/json" \
  -d '{"platform":"youtube","pack":{ ...the current pack... }}'
```

Read `gain`, `changes`, and `pack` (the ready-to-publish version). **The
optimiser only lists a change when re-scoring proved it moved the number**, and
the returned pack re-scores to exactly `after.score` — so verify it if you like,
the numbers will match. Anything it could not fix (runtime, thumbnail, playlist)
stays in `after.quick_wins` as work for the creator.

## 4. Never ship a guess: size and run the test

```bash
# 1. How much traffic does a detectable lift need?
curl -s -X POST http://127.0.0.1:8000/seo/ab/plan -H "Content-Type: application/json" \
  -d '{"metric":"ctr","baseline_rate":0.04,"relative_lift":0.15,"daily_traffic":5000}'

# 2. After the run, did the variant really win?
curl -s -X POST http://127.0.0.1:8000/seo/ab/evaluate -H "Content-Type: application/json" \
  -d '{"metric":"ctr","arms":[{"name":"control","impressions":40000,"clicks":1600},
                             {"name":"variant_b","impressions":40000,"clicks":2200}]}'
```

`ab/plan` returns the sample per arm, the calendar days at your traffic, the
decision rule and which metric to read. `ab/evaluate` returns a p-value, lift,
required-per-arm and a verdict — a tie is reported as `keep_running`, never as a
winner. Report the p-value, not just the lift.

## 5. Close the loop with real numbers, then re-fit the weights

Pass measured results back as `engagement` (impressions, views, likes, comments,
shares, saves, follows, watch time, average view, completion) and the same score
is recomputed against performance rather than metadata hygiene. Once you have a
handful of published videos, `POST /seo/calibrate` correlates each signal with
the real outcome and suggests weights fitted to this channel — the shipped
weights are priors, and they are meant to be replaced.

## Hard rules

1. **Never invent engagement.** If you were not given analytics, leave them out;
   the score drops its confidence instead of accepting a made-up number.
2. **Never report a gain you did not measure.** Quote `before` → `after` from the
   optimiser, or a p-value from an evaluation. "Should perform better" is not a
   result.
3. **The two human gates still apply.** This skill audits the packaging before
   the video gate; it never approves a script or a video, and it never confirms
   source rights.
4. **Score all platforms before choosing.** The same pack that scores 80 on
   YouTube can fail on TikTok for aspect and runtime — score `"all"` and fix
   per platform rather than guessing.

## Related

- `docs/SEO-SCORING.md` — the model, the platform sources, and the statistics.
- `docs/TOOLS-FOR-AGENTS.md` — the full agent tool surface (`seo_*` tools).
- `publish-scheduler` skill — the publishing step that follows this audit.
- `multi-format-campaign` skill — one master becomes a long video plus shorts.
