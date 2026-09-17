# The video editing engine

Every structural decision about a cut lives in one pure module,
`src/content_factory/timeline.py`. The API, the worker, the renderer, an
external AI agent, and the browser all mutate a timeline through that single
code path — there is no second implementation to drift out of sync.

## The model

A `VideoProject` is a document with:

| Field | Meaning |
| ----- | ------- |
| `scenes` | Ordered clips. Each has look, text, narration, timing, motion, and audio gain. |
| `aspect_ratio` / `fps` | Output geometry (`9:16`, `16:9`, `1:1`, `4:5`, `3:4`). |
| `captions`, `background_music`, `music_volume`, `voiceover_volume` | Audio and caption layers. |
| `bpm` | Beat grid used by the AI tempo-sync action. |
| `markers` | Labelled points (beats, chapter turns, cues). |
| `revision` | Server-owned counter, bumped on every saved edit. |

A `VideoScene` carries:

* **Identity**: `id`, `label`.
* **Content**: `text` (on-screen), `narration` (spoken), `image_url`.
* **Timing**: `duration_seconds` (the timeline slot), `speed`.
* **Look**: `background`, `text_color`, `font_size`, `text_style`,
  `text_position`, `filter`, `effect`, `grade`, `ken_burns`, `overlay_*`.
* **Animation**: `entrance`, `exit`, `motion` (single segment, legacy), and
  `keyframes` (a real track).
* **Source handles**: `trim_start` / `trim_end` — in/out points on the source
  media. They select which part of the source is shown; the timeline slot is
  unchanged, exactly like an NLE clip's handles.
* **Audio**: `volume`, `pitch`.

## Guarantees

1. **Normalization on every write.** `normalize()` is idempotent and repairs:
   duplicate or empty scene ids, out-of-range numbers, keyframes out of order
   or outside `0..1`, invalid hex colours, unknown aspect ratios, oversized
   font sizes, and a transition on the opening scene. `PUT /video-project` and
   every structural endpoint run it, so a broken document cannot be persisted.
2. **The revision counter is server-owned.** A client cannot jump or reset it,
   so `revision` stays a trustworthy "someone else moved the timeline" signal.
3. **Validation never blocks a save.** `GET /timeline/report` reports; it does
   not refuse. A human decides.
4. **Editing stays open late.** A cut can be edited in `generating`,
   `video_review`, `video_approved`, and `published`. Re-cutting after publish
   is normal; rewriting an approved *script* is not, and stays blocked.

## The validator

`GET /projects/{id}/timeline/report` returns measured stats plus findings, and
a 0–100 readiness score (ERROR −25, WARNING −8, INFO −2).

| Code | Severity | Trigger |
| ---- | -------- | ------- |
| `empty_timeline` | error | No scenes at all. |
| `scene_too_short` | warning | A scene is shorter than 0.8s. |
| `frantic_pacing` | warning | More than 42 cuts per minute. |
| `speed_extreme` | warning | Non-1× speed leaves under 0.8s on screen. |
| `transition_too_long` | warning | The blend occupies ≥40% of the shorter neighbour. |
| `empty_scene` | warning | No text and no narration. |
| `text_overflows_scene` | warning | On-screen text cannot be read in the scene's time. |
| `narration_overflows_scene` | warning | Narration needs >125% of the scene's time. |
| `low_text_contrast` | warning | WCAG contrast below 4.5:1 between text and background. |
| `narration_underfills` | warning | Narration covers under 50% of the cut — dead air. |
| `duration_drift` | warning | The cut is off the target duration by more than 15%. |
| `opening_transition` | info | The first scene has a transition (only on raw documents). |
| `flat_look` / `flat_look_partial` | info | Scenes with no image, filter, or grade. |
| `marker_out_of_range` | info | A marker sits past the end of the timeline. |
| `no_markers` | info | No markers on a long cut. |

Stats include `total_seconds`, `narration_seconds`, `transition_seconds`,
`shortest/longest/average_scene_seconds`, `words`, `words_per_minute`, and
`cuts_per_minute`.

## Structural operations

| Endpoint | Effect |
| -------- | ------ |
| `POST /timeline/scenes/{id}/split` | Split at a fraction (`{"at": 0.5}`); total runtime is preserved. |
| `POST /timeline/scenes/{id}/merge` | Merge into the following scene (the inverse of a split). |
| `POST /timeline/scenes/{id}/duplicate` | Insert a copy directly after. |
| `DELETE /timeline/scenes/{id}` | Remove it; the last remaining scene is protected. |
| `POST /timeline/scenes/{id}/move` | Reorder (`{"to_index": 3}`). |
| `POST /timeline/scenes/bulk` | Apply one look to many scenes at once. |
| `POST /timeline/normalize` | Repair the document and record a new revision. |
| `POST /timeline/markers` | Add a marker (clamped to the timeline). |
| `DELETE /timeline/markers/{id}` | Remove a marker. |

`bulk` patches are validated through pydantic rather than assigned raw: a
`"noir"` string becomes `ColorGrade.NOIR`, and a typo is rejected instead of
poisoning the document. `id`, `text`, `narration`, and `keyframes` are never
bulk-assigned.

## Motion and keyframes

`evaluate_motion(scene, progress)` returns `scale`, `rotation`, `opacity`,
`pos_x`, `pos_y` at any point of a scene's runtime, in this order of
precedence:

1. **Keyframe track** — interpolated between the surrounding keyframes with the
   destination keyframe's easing (`linear`, `ease-in`, `ease-out`,
   `ease-in-out`), clamped outside the track.
2. **`motion`** — the legacy single segment, animated from neutral.
3. **Resting pose** — no animation.

Because `at` is a *fraction*, a track stays valid when a scene is retimed by a
split, a speed change, or the duration slider.

## Captions and the render plan

`GET /projects/{id}/render-plan` compiles the timeline into an explicit,
backend-agnostic plan:

* **`steps`** — every scene at an absolute `start_seconds` / `end_seconds`,
  with its resolved look, keyframes, source in-point, speed, gain, and the
  duration of the blend at its head. Transitions blend *inside* a scene's slot,
  so the total never changes because a transition was added.
* **`subtitles`** — narration broken into readable cues (≤9 words, ≤42
  characters) distributed across the scene proportionally to their length, so
  captions stay in sync without forced alignment.
* **`audio`** — the voiceover and music layers with their gain and BPM.
* **`warnings`** — unknown aspect ratio, or a cut made only of colour cards.

`narration_urls` wires each scene to its synthesized clip, so a renderer knows
which audio belongs in which slot. This is the artifact a real renderer (P2,
ffmpeg) consumes.

## In the Studio UI

The editor's **Pro Engine** bar drives all of this: live score and stats, the
finding list (click a finding to jump to its scene), and buttons for split,
merge, duplicate, delete, reorder, marker, clean, check, and render plan.

The browser is no longer authoritative for structure. Each Pro action
(1) pushes local property tweaks to the server, (2) calls exactly one
operation, and (3) adopts the returned document — so the server and the
browser cannot disagree. `Save Project` sends the same payload, which keeps
markers and the revision counter intact.
