---
name: media-studio
description: Universal media library — upload any video, audio, image, or document; probe it with ffprobe; transcribe video/audio with faster-whisper; extract text from documents so AI agents can read and re-purpose the content.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
  - web_fetch
---

# Media Studio Skill — Universal Media Library & AI Understanding

This skill guides AI agents in ingesting any media file into the AI Content
Factory's universal media library, letting an AI agent "read" the content
(transcription for video/audio, text extraction for documents), then reuse it.

## 1. Upload anything

`POST /media/upload` (multipart: `file` + optional `language`) accepts any
file. The backend classifies it by extension:

| Kind | Extensions |
| --- | --- |
| video | mp4, mov, mkv, webm, avi, m4v, flv, wmv, ts |
| audio | mp3, wav, m4a, aac, ogg, flac, opus, wma |
| image | jpg, jpeg, png, gif, webp, bmp, svg, tiff |
| document | pdf, txt, md, csv, json, srt, vtt |

Video/audio are probed with ffprobe for duration and resolution. The item is
persisted on disk and indexed in `library/media/index.json`.

## 2. Let the AI read it

- `POST /media/{id}/transcribe` — transcribe a video/audio item with
  faster-whisper (CPU `base` model). Populates `transcription` and timed
  `transcript_segments`. Requires `pip install faster-whisper`.
- `POST /media/{id}/extract-text` — extract plain text from a PDF/text
  document (pypdf for PDFs).
- `POST /media/{id}/convert?target_format=mp4` — convert an item to another
  format: `mp4`, `webm` (video), `mp3`, `wav` (audio), `png`, `jpg` (image).
  The original is preserved; a new sibling MediaItem is created.
- `GET /media` — list all items (newest first).
- `GET /media/{id}` — fetch one item incl. its AI reading.
- `GET /media/{id}/download` — serve the raw file.
- `DELETE /media/{id}` — delete an item and its backing file.

## 3. Reading a transcript for re-purposing

Once transcribed, the `transcription` field is the source of truth for any
re-cook or re-use. Feed it to a re-writer (see `content-recook`) rather than
copying it verbatim — the pipeline's `copy_risk` filter and the re-cook
transformer both enforce "learn, don't copy".

## 4. Offline behaviour

Without `faster-whisper`, transcription raises a clear error; document text
extraction and uploads still work. ffmpeg/ffprobe are required for media
probing and are already present in the toolchain.