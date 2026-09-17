# Toolchain — installing the local media/AI stack

Everything here is optional: the pipeline degrades gracefully. Each tool is
reached through an adapter, so once a binary is on `PATH` (or its Python
package is installed) the matching feature turns on.

`python scripts/toolcheck.py` prints what is present and what each missing
tool would enable.

> Nothing in this file is executed automatically. Run the commands you want,
> yourself, at a terminal you control. Feel free to skip the AI/CUDA section
> if the machine has no GPU.

## 1. Core media (required for real rendering)

| Tool | Why | Windows | macOS | Debian/Ubuntu |
| ---- | --- | ------- | ----- | ------------- |
| ffmpeg + ffprobe | cut, concat, xfade, overlay, subtitle burn-in, audio mix, transcode | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| yt-dlp | download reference videos *you have the rights to use* | `winget install yt-dlp.yt-dlp` | `brew install yt-dlp` | `pipx install yt-dlp` |
| fonts with Vietnamese coverage | correct diacritics in burned-in captions | `winget install Google.NotoSans` | `brew install --cask font-noto-sans` | `sudo apt install fonts-noto-core` |

## 2. Speech (transcription, alignment, separation)

| Tool | Why | Install |
| ---- | --- | ------- |
| faster-whisper | fast transcription, word timestamps | `pip install faster-whisper` |
| WhisperX | forced alignment → word-perfect subtitles | `pip install whisperx` |
| Demucs | split vocals from music for remixes | `pip install demucs` |
| audioop / ffmpeg loudnorm | EBU R128 loudness normalization | ships with ffmpeg |

## 3. Images and video

| Tool | Why | Install |
| ---- | --- | ------- |
| Pillow | image compositing, thumbnails | `pip install pillow` |
| OpenCV | frame analysis, stabilization | `pip install opencv-python` |
| rembg | background removal for subject cut-outs | `pip install rembg` |
| Real-ESRGAN | upscaling stills | `pip install realesrgan` (plus model weights) |
| ComfyUI | local Stable Diffusion / Flux image and video generation | clone the repo, `pip install -r requirements.txt`, run with `--listen 127.0.0.1` |
| MoviePy | quick programmatic edits | `pip install moviepy` |

## 4. Voice synthesis and cloning

| Tool | Why | Install |
| ---- | --- | ------- |
| edge-tts | free Microsoft neural voices (already a dependency) | `pip install edge-tts` |
| gTTS | dependency-light fallback (already a dependency) | `pip install gTTS` |
| Coqui XTTS v2 | multilingual voice cloning | `pip install TTS` (Python 3.11 recommended) |
| RVC / so-vits-svc | sing/voice conversion from a reference clip | separate repos, GPU strongly recommended |

Only clone a voice you have the right to use. Keep the original recording and
a written permission note next to the model file.

## 5. Local LLMs (script drafting with no API cost)

```bash
# Install Ollama, then pull a model that is strong in Vietnamese
ollama pull qwen2.5:7b          # small, fast, decent Vietnamese
ollama pull llama3.1:8b         # stronger reasoning
ollama pull gemma2:9b           # good multilingual balance
```

Then enable it for the pipeline:

```ini
CONTENT_FACTORY_OLLAMA_ENABLED=true
CONTENT_FACTORY_OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
CONTENT_FACTORY_OLLAMA_MODEL=qwen2.5:7b
```

## 6. Cloud AI (optional, paid)

| Provider | Env vars | Notes |
| -------- | -------- | ----- |
| Anthropic Claude | `CONTENT_FACTORY_ANTHROPIC_*` | best long-form script quality; native `/v1/messages` adapter |
| Google Gemini | `CONTENT_FACTORY_GOOGLE_*` | strong multilingual, long context |
| DeepSeek | `CONTENT_FACTORY_DEEPSEEK_*` | cheap reasoning tier |
| Any OpenAI-compatible | `CONTENT_FACTORY_STRONG_LLM_*` | OpenAI, OpenRouter, Groq, vLLM, Together |

Order matters — the strong tier tries vendors in the order set by
`CONTENT_FACTORY_STRONG_PROVIDER_ORDER`.

## 7. Verify the machine

```bash
ffmpeg -version
ffprobe -version
python scripts/toolcheck.py
python -m pytest -q
python scripts/smoke.py
```
