# SEO Scoring & Packaging Audit — YouTube, Shorts, TikTok

A deterministic, offline scorer for the *publish pack* (title, description, tags,
hashtags, hook, structure, sound, settings), an optimiser whose every change is
verified by re-scoring, and the statistics needed to prove a change actually
helped. No API key, no scraping, no platform call.

Engine: `src/content_factory/seo/` · Service: `services/seo.py` ·
HTTP: `api/routers/seo.py` · Agent tools: `seo_*` in `agent_tools.py`.

---

## 1. What the platforms actually say (and where the model encodes it)

Every threshold in the model traces back to platform guidance rather than folklore.

| Fact encoded in the model | Source |
| :--- | :--- |
| Search ranking weighs **how well the title, description and video content match the query**, plus **which videos drive the most engagement for that search** | YouTube Help — *YouTube performance FAQ* <https://support.google.com/youtube/answer/141805> |
| Home/Recommended ranking weighs **performance** and **watch/search history**, not metadata alone | same page |
| Title/thumbnail must **accurately represent the content**; misleading, ALL-CAPS or sensation-bait packaging is explicitly penalised | same page |
| A video's description can hold **up to 5,000 characters**; a title is **truncated at 100** | YouTube Help — *Titles, thumbnails & descriptions* family (modelled as `title_hard_max`, `description_hard_max`) |
| **Up to 3 hashtags** are surfaced above the title, chosen as *most engaging* | YouTube Help — *Find playlists & videos using hashtags* <https://support.google.com/youtube/answer/6390658> |
| **More than 60 hashtags → every hashtag on that content is ignored**; over-tagging, unrelated or misleading hashtags risk removal and are penalised | same page |
| Hashtags contain **no spaces**; joined form (`#TwoWords`) | same page |
| TikTok surfaces content from **caption, on-screen text and spoken words**, and search/recsys favour **completion and rewatch**, so the first seconds decide the rest | TikTok guidance for creators (modelled as `caption_keyword`, `on_screen_text`, `spoken_keyword`, `retention_measured`, `loop`) |

Platform constants live in one place, `seo/profiles.py`, so a rule change is a
one-line edit rather than a hunt.

## 2. The model

Three profiles, four weighted dimensions each, 70 weighted signals in total.

| Platform | Signals | Dimensions (weight) | Blocking signals |
| :--- | :---: | :--- | :--- |
| `youtube` (long-form) | 26 | search 30% · packaging 20% · retention 30% · distribution 20% | `title_length` *(only when empty/over hard max)*, `aspect` |
| `youtube_shorts` | 21 | search 20% · packaging 30% · retention 35% · distribution 15% | `title_length` *(as above)*, `aspect` |
| `tiktok` | 23 | retention 35% · discoverability 30% · sound 15% · distribution 20% | `repost_watermark`, `aspect` |

Per-profile targets: duration band, hook window, completion target, watch-ratio
target, CTR target, minimum cut rate, title/description/keyword-zone lengths,
hashtag and tag bands. `GET /seo/rules` returns all of them plus the full signal
table, so an agent never has to guess what the number means.

**Scoring.** A dimension score is the weighted mean of its *measurable* signals;
the overall score is the weighted mean of dimensions. A signal whose input is not
recorded scores `unknown` and is **excluded** (it lowers `confidence` instead of
being invented). Status bands: `ok ≥ 0.85`, `warn ≥ 0.55`, else `fail`.

**Blocking policy (deliberately narrow).** A signal may cap the score at 45 only
when the pack is genuinely unusable or the platform will suppress it:
a wrong aspect ratio for a vertical-first surface, a repost watermark, or an
empty/over-length title. Advisory signals — a short title, a missing hashtag set,
a 4-minute runtime — cost points but **never** freeze the score, because a
4-minute video is perfectly publishable and "do not publish" for a short title is
crying wolf. Blocking conditions are declared next to the signal
(`blocking_when=_title_unusable`), so the rule is visible where it applies.

**Output.** `score` (0–100), `grade` (A+…F), `confidence` (fraction of the model
that could be measured), `capped`/`cap_reason`, per-dimension breakdown with every
signal's `detail` + `fix`, `blocking`, the top `quick_wins` ranked by points they
are worth, `projected_score`, a plain-language `verdict`, `metrics`, and `notes`
that restate the platform facts used.

## 3. Optimiser: every claimed gain is measured

`optimize_pack` rewrites the pack, then **proves** the rewrite:

1. Build candidates per field (title, description, hashtags, tags, hook, comment
   prompt) — filling the platform's ideal bands, using the pack's own material
   (hook sentence, on-screen text, chapters) rather than filler.
2. Apply candidates greedily: a field is kept only if re-scoring the trial pack
   **improves** the result. A second pass catches fields that only pay off
   together. Ties are broken on the un-rounded score (`SeoReport.precision`), so
   a real 0.4-point win is not lost to rounding.
3. Return the resulting pack, `before`/`after` reports, `gain`, and `changes`
   listing **only the rewrites that measurably moved the number**.

The response's `pack` is the exact pack that was scored, so a caller can rebuild
it, re-score it, and get the identical number back. That is asserted in
`tests/test_seo_engine.py::test_optimizer_gain_is_measured_not_claimed` and
end-to-end in `scripts/qa_seo_tools_http.py`.

## 4. Testing a change like an experiment

- **`POST /seo/ab/plan`** — sample size per arm and calendar days for a target
  lift (two-proportion sizing with α and power), plus the decision rule,
  the variable to hold constant, and which metric to read.
- **`POST /seo/ab/evaluate`** — two or more arms in, and out: pooled
  two-proportion z-test (or Welch test for continuous metrics), p-value, lift and
  relative lift, observations per arm, required-per-arm, and a `verdict` that
  says *ship* or *keep running*. A coin-flip is never declared a winner.
- **`POST /seo/keywords`** — demand-versus-competition ranking of phrases against
  a competitor corpus (views, channel size, age, duration), plus winning
  phrasings mined from titles.
- **`POST /seo/calibrate`** — correlate each signal with real outcomes
  (views/day, CTR, retention) and suggest weights fitted to *your* channel.
  The shipped weights are reasonable priors; calibration replaces them.

## 5. Using it

| Endpoint | Tool name | Question it answers |
| :--- | :--- | :--- |
| `GET /seo/rules` | `seo_rules` | What does the model measure, and how much does each part weigh? |
| `POST /seo/score` | `seo_score` | How ready is this pack (`youtube` \| `youtube_shorts` \| `tiktok` \| `all`)? |
| `POST /seo/optimize` | `seo_optimize` | Give me the rewrite and the measured gain |
| `POST /projects/{id}/seo` | `seo_score_project` | What would *this project* actually publish, and how good is it? |
| `POST /seo/ab/plan` | `seo_ab_plan` | How much traffic does a real test need? |
| `POST /seo/ab/evaluate` | `seo_ab_evaluate` | Did the variant really win? |
| `POST /seo/keywords` | `seo_keywords` | Which phrases are worth targeting? |
| `POST /seo/calibrate` | `seo_calibrate` | Which signals actually predict my results? |

```bash
# Score a stored project on every platform through the agent tool surface
curl -s -X POST http://127.0.0.1:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"seo_score_project","args":{"project_id":"<id>","platform":"all"}}'

# Optimise a hypothetical pack and see the measured gain
curl -s -X POST http://127.0.0.1:8000/seo/optimize \
  -H "Content-Type: application/json" \
  -d '{"platform":"tiktok","pack":{"title":"Tàu Titanic","description":"Chuyện con tàu.",
       "keywords":["tàu titanic"],"hook":"Con tàu này được cho là không thể chìm.",
       "aspect_ratio":"9:16","has_captions":true}}'
```

`seo_score_project` reads the project rather than trusting the caller: hook from
the script's first section, runtime and cut rate from the timeline, aspect,
caption and music state, chapter markers, and the on-screen text of every scene.
Pass `engagement` (impressions, views, likes, comments, shares, saves, follows,
watch time, average view, completion) after publishing and the same score is
recomputed against measured performance instead of metadata hygiene.

## 6. Verification of record

| Check | Result |
| :--- | :--- |
| `pytest` (full suite) | 854 tests, 0 failed, 0 errors, 0 skipped |
| `tests/test_seo_engine.py`, `test_seo_validation.py` | 110 tests green, incl. deterministic engine snapshot |
| `ruff check` + `format --check` + `mypy src` | clean (115 files) |
| `scripts/smoke.py` | 64/64 checks PASS on a fresh server |
| `scripts/qa_seo_tools_http.py` (real HTTP, agent path) | 22/22 checks PASS |
| Optimiser round-trip | weak pack 68 → 83 on YouTube; the returned pack re-scores to exactly 83 |
| Score responsiveness | a 4-minute pack with a short title and no hashtags is no longer capped; the same pack with an empty title still is |

## 7. Limits, stated plainly

- The scorer cannot see analytics it was not given; watch-time and engagement
  signals stay `unknown` and reduce confidence until `engagement` is supplied.
- It does not call platform APIs, so it cannot know a sound is trending *today*;
  `sound_trend` / `beat_sync` accept what the creator or an external tool knows.
- Weights are priors derived from published platform guidance plus practice.
  `seo_calibrate` is the intended way to replace them with your channel's data.
- A high score is not a promise of reach — it is a statement that the packaging
  is free of the faults the platform documents as damaging, and complete on every
  field the platform reads.
