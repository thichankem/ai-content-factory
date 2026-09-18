# Script style presets

Everything in the scripting stage is driven by a **style preset**: tone, section
structure, hook rules, sentence budget, call to action, banned phrases, and the
speech rate used for duration estimates.

Five presets ship with the package (`viral-short`, `documentary`,
`educational`, `story`, `product-review`). This directory is where **you**
override them or add your own.

## How loading works

- The directory is `CONTENT_FACTORY_PRESETS_DIR` (default `./presets`).
- Every `*.json` and `*.md` file is loaded at startup and on demand.
- A file whose `name` matches a built-in preset **replaces** it.
- Files with the same slug: the last one wins; broken files are ignored with a
  warning, never a crash.
- No file here means the built-in presets apply.

## JSON (canonical, lossless)

```json
{
  "name": "vietnamese-short",
  "title": "Vietnamese vertical short",
  "description": "Câu ngắn, khẩu ngữ, hook trong 6 chữ đầu.",
  "tone": "thân mật, nhanh, xưng 'bạn'",
  "structure": ["Hook", "Turn", "Payoff", "CTA"],
  "hook_rules": ["Mở bằng một con số hoặc mâu thuẫn."],
  "sentence_max_units": 12,
  "max_sections": 8,
  "cta": "Theo dõi để xem phần tiếp theo.",
  "banned_phrases": ["trong video này", "hôm nay chúng ta sẽ"],
  "language_notes": {"vi": "Tránh từ Hán-Việt nặng, ưu tiên từ thuần Việt."},
  "units_per_second": {"vi": 2.7}
}
```

## Markdown (human/AI-agent friendly)

The same fields with a lighter syntax — good for handing to an AI agent:

```markdown
# Style: my-style

title: My style
tone: dry, factual
sentence_max_units: 14
max_sections: 10
cta: Save this.

## Structure
- Hook
- Evidence
- Payoff

## Hook rules
- Lead with a number.

## Banned phrases
- game changer

## Language notes
- vi: Câu ngắn, không dùng từ đệm.

## Speech rate overrides
- vi: 2.9
```

## Score reference

`sentence_max_units` is **words** for Latin-script languages and **characters**
for CJK/Thai. `units_per_second` overrides the built-in speech rate that
`content_factory.script_engine` uses for duration planning — raise it if
your narrator speaks faster than the default.

## Multi-Format Empire & AI Integration

Style presets also drive the prompt generation matrix in the **Multi-Format Empire Engine**:
- In **YouTube Master Documentaries**, presets like `documentary` enforce measured pacing, formal evidence citations, and dramatic narrative arcs.
- In **TikTok / Shorts**, presets like `viral-short` and `vietnamese-short` enforce high-tension 0–3s hooks, 12 words/sentence limits, and high-retention call-to-actions.
- External AI agents (Claude, Codex, Gemini, DeepSeek) receive these presets via `GET /projects/{id}/brief.md` and can return customized presets via `POST /projects/{id}/agent-result`.

## Manage presets

```bash
curl http://127.0.0.1:8000/script/styles                  # list all presets
curl http://127.0.0.1:8000/script/styles/story/md         # read as Markdown
curl -X PUT http://127.0.0.1:8000/script/styles/my-style \
     -H 'Content-Type: application/json' -d @my-style.json
curl -X DELETE http://127.0.0.1:8000/script/styles/my-style
```

Assign a preset to a project:

```bash
curl -X PUT http://127.0.0.1:8000/projects/<ID>/script/style \
     -H 'Content-Type: application/json' -d '{"style":"my-style"}'
```
