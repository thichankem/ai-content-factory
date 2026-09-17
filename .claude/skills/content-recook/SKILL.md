---
name: content-recook
description: Content re-cook pipeline — transform any source video/audio/document into a brand-new video by re-wording the transcript, swapping the hook/CTA, changing the title and music, and condensing or expanding the length, then producing a new rendered WebM through the normal two-gate approval flow.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
  - web_fetch
---

# Content Re-Cook Skill — "Xào Nấu" Source Media Into New Videos

This skill guides AI agents in re-cooking an existing media item into a new,
distinct video: read the source, re-word it, change the title/music, and render
a fresh cut. It is designed for operators who bring in source material and want
a transformed derivative, not a verbatim copy.

## 1. The flow

1. **Ingest** the source into the media library (`media-studio` skill):
   `POST /media/upload`, then `POST /media/{id}/transcribe` (video/audio) or
   `POST /media/{id}/extract-text` (document).
2. **Re-cook**: `POST /media/{id}/recook` with a `ReCookRequest`:

   ```json
   {
     "new_title": "Stalingrad: The Turning Point",
     "language": "en",
     "target_seconds": 60,
     "mode": "balanced",
     "change_music": true,
     "script_style": "viral-short"
   }
   ```

   This creates a brand-new project in `script_review` with a re-worded script
   (rule-based paraphrase transformer; swap in a strong LLM provider for richer
   rewrites). `mode` is `condense` (cut), `expand` (pad), or `balanced`.

3. **Drive the two mandatory human gates** (never auto-confirm rights):
   - `PUT /projects/{id}/script` with `source_rights_confirmed: true`
   - `POST /projects/{id}/approvals` `{"stage": "script", "verdict": "approved"}`
   - `POST /projects/{id}/generate` → wait for `video_review`
   - Self-edit: `POST /projects/{id}/video-project/ai-assist`
   - `POST /projects/{id}/render` → real ffmpeg WebM
   - `POST /projects/{id}/approvals` `{"stage": "video", "verdict": "approved"}`
   - `POST /projects/{id}/publish`

## 2. Changing the music

Set `change_music: true` and (once the renderer supports audio beds) the
pipeline mixes a synthesized royalty-free pad under the new narration. Today
`media.synthesize_music_bed()` can generate a cinematic drone bed with ffmpeg.

## 3. Anti-plagiarism guarantees

The re-cook transformer never copies the source verbatim: it compresses
filler, restructures common patterns, and swaps synonyms. Always keep the
"learn, don't copy" rule — the operator owns the rights to their source
material, but the derivative must still be original wording.

## 4. Verification

After rendering, probe the WebM with `ffprobe` to confirm a real video stream
exists. Run `scripts/qa_recook_5_videos.py` for a full 5-source end-to-end
demonstration.