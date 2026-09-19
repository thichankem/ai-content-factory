"""Application configuration loaded from ``CONTENT_FACTORY_*`` env vars."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_STREAM_CHUNK_BYTES = 1024 * 1024
MAX_STREAM_CHUNK_BYTES = 16 * 1024 * 1024
DEFAULT_UPLOAD_MAX_BYTES = 1024 * 1024 * 1024
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024 * 1024


def validate_stream_chunk_bytes(value: int) -> None:
    if type(value) is not int or not 1 <= value <= MAX_STREAM_CHUNK_BYTES:
        raise ValueError(
            f"stream_chunk_bytes must be between 1 and {MAX_STREAM_CHUNK_BYTES}"
        )


def validate_upload_max_bytes(value: int) -> None:
    if type(value) is not int or not 1 <= value <= MAX_UPLOAD_BYTES:
        raise ValueError(f"upload_max_bytes must be between 1 and {MAX_UPLOAD_BYTES}")


class Settings(BaseSettings):
    """Runtime configuration for the AI Content Factory.

    Every value can be overridden through a ``CONTENT_FACTORY_`` prefixed
    environment variable (see ``.env.example``) or a local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="CONTENT_FACTORY_",
        env_file=".env",
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    app_name: str = "ai-content-factory"
    debug: bool = False

    # --- Provider routing --------------------------------------------------
    # cost_first    -> try weak/cheap/local tier first, fall back to strong API
    # quality_first -> try strong tier first, fall back to weak tier
    provider_strategy: Literal["cost_first", "quality_first"] = "cost_first"

    # --- Weak tier: local MoneyPrinterTurbo ---------------------------------
    money_printer_enabled: bool = True
    money_printer_base_url: str = "http://127.0.0.1:8080"
    money_printer_api_key: str | None = None

    # --- Strong tier: OpenAI-compatible endpoint -----------------------------
    strong_llm_enabled: bool = False
    strong_llm_base_url: str = "https://api.openai.com/v1"
    strong_llm_api_key: str | None = None
    strong_llm_model: str = "gpt-4o-mini"
    strong_llm_timeout_seconds: float = 90.0

    # Order in which the strong tier tries its vendors. Any name that is
    # disabled or unconfigured is skipped. Recognized names:
    # anthropic | google | deepseek | openai
    strong_provider_order: str = "anthropic,google,deepseek,openai"
    strong_max_tokens: int = 4096

    # --- Anthropic Claude (native /v1/messages) ------------------------------
    anthropic_enabled: bool = False
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    anthropic_version: str = "2023-06-01"

    # --- Google Gemini (native generateContent) ------------------------------
    google_enabled: bool = False
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    google_api_key: str | None = None
    google_model: str = "gemini-2.5-flash"

    # --- DeepSeek (OpenAI-compatible) ----------------------------------------
    deepseek_enabled: bool = False
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"

    # --- Ollama local models (OpenAI-compatible /v1) -------------------------
    ollama_enabled: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_api_key: str | None = "ollama"
    ollama_model: str = "qwen2.5:7b"

    # --- Scripting presets ----------------------------------------------------
    # Directory scanned for user preset files (*.json / *.md). Users can
    # override built-in presets or add their own without touching code.
    presets_dir: str = "./presets"

    # --- External AI agent bridge ---------------------------------------------
    # Enables exporting Markdown briefs and importing agent results.
    agent_bridge_enabled: bool = True

    # --- Built-in template provider (offline fallback) ------------------------
    # Always-on local provider that drafts a script from the topic, so the
    # pipeline works out of the box with no external service.
    template_enabled: bool = True

    # --- Research -------------------------------------------------------------
    # Maximum number of reference sources gathered per research pass.
    research_max_sources: int = 6

    # --- Document search & library --------------------------------------------
    # Federated web search across arXiv, Crossref, Gutenberg, Open Library,
    # Wikipedia, and Internet Archive. Disable for fully offline operation.
    documents_web_enabled: bool = True
    documents_search_timeout_seconds: float = 8.0
    library_dir: str = "./library"
    library_db_path: str = "./library/.index.db"
    # Universal media library (video/audio/image/document uploads).
    media_dir: str = "./library/media"
    # Optional cloud object storage for media files. When ``s3_bucket`` is set
    # (and boto3 is installed), the authoritative copy of every media file is
    # kept in S3-compatible storage; the local ``media_dir`` remains a cache for
    # in-place processing. Leave empty for a purely local library.
    s3_bucket: str = ""
    s3_endpoint: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_prefix: str = "content-factory"
    stream_chunk_bytes: int = Field(
        default=DEFAULT_STREAM_CHUNK_BYTES, ge=1, le=MAX_STREAM_CHUNK_BYTES
    )
    upload_max_bytes: int = Field(
        default=DEFAULT_UPLOAD_MAX_BYTES, ge=1, le=MAX_UPLOAD_BYTES
    )

    # --- Content-addressed cache (idempotent checkpoints) ----------------------
    # Expensive steps (transcription, vision scoring, scene analysis) memoize
    # their results here by input hash, so a retried pipeline resumes instead
    # of recomputing.
    cache_dir: str = "./storage/cache"

    # --- Optional vision layer --------------------------------------------------
    # Off by default: mechanical tasks (cut by timestamp, template composites)
    # never spend vision cost. Turn on only when a task must "understand" a
    # frame, and pick a backend.
    #   rule_based -> heuristic scoring (sharpness/exposure/saturation), free
    #   claude     -> multimodal LLM scorer (opt-in, paid)
    #   local      -> local model scorer (YOLO/CLIP) when one is wired in
    enable_vision: bool = False
    vision_backend: str = "rule_based"

    # --- Optional audio perception layer ----------------------------------------
    # "Hearing" the soundtrack. Silence/pace, music mood and technical quality
    # always run free (numpy + ffmpeg). Sound-event detection, speaker
    # diarization, speech emotion and natural scene description need an AI
    # backend (PANNs/YAMNet, pyannote, SER, CLAP or an audio-capable LLM) and
    # are off by default.
    #   rule_based -> non-AI analysis only (free, deterministic)
    #   ai         -> attach AI backends when one is wired in
    enable_audio_perception: bool = False
    audio_perception_backend: str = "rule_based"

    # --- QA & traceability layer ------------------------------------------------
    # Append-only provenance/audit trail of every AI edit (model, prompt, time).
    audit_dir: str = "./storage/audit"
    # Cost guard: before running an expensive plan (many vision/audio-LLM calls),
    # estimate USD cost and require confirmation when it exceeds the threshold.
    cost_guard_enabled: bool = False
    cost_guard_threshold_usd: float = 5.0
    cost_unit_vision_usd: float = 0.010
    cost_unit_audio_llm_usd: float = 0.020
    cost_unit_tts_usd: float = 0.002
    cost_unit_stt_usd: float = 0.003
    cost_unit_embedding_usd: float = 0.0001

    # --- Media intelligence ------------------------------------------------------
    # Max Hamming distance for perceptual-hash near-duplicate detection.
    dedup_max_distance: int = 4
    # Semantic-search seam over the media library: "lexical" (BM25, default) or
    # "embedding" when an embedder is wired in.
    search_embedder: str = "lexical"

    # --- Knowledge engine (RAGFlow-style) --------------------------------------
    # Template-based chunking + hybrid vector/BM25 retrieval with RRF fusion.
    kb_enabled: bool = True
    kb_default_template: str = "naive"
    kb_chunk_tokens: int = Field(default=256, ge=64, le=2048)
    kb_chunk_overlap: int = Field(default=48, ge=0, le=512)
    kb_top_k: int = Field(default=6, ge=1, le=50)
    kb_rerank: bool = True

    # --- Simulated video production -------------------------------------------
    # The vertical slice simulates rendering; these tune the fake worker.
    generation_steps: int = 10
    generation_step_delay_seconds: float = 0.3
    # A render started while the generation worker is still rewriting the
    # project would be discarded at the compare-and-save, so it waits for the
    # worker up to this long before refusing with a retryable 409.
    render_settle_seconds: float = Field(default=60.0, ge=0.0, le=600.0)
    video_format: str = "mp4"
    render_threads: int = Field(default=1, ge=1, le=8)
    render_max_dimension: int | None = Field(default=None, ge=64, le=1920)
    # A hung ffmpeg must never pin the machine: the job is killed past this.
    render_timeout_seconds: float = Field(default=1800.0, ge=30, le=86400)
    uploads_dir: str = "./storage/uploads"

    # --- Compute scheduling (CPU vs GPU) ---------------------------------------
    # The whole policy lives here so a laptop can be tuned without editing code.
    # compute_policy: "auto" (use the GPU when it is free and cool) | "cpu" | "gpu"
    compute_policy: str = "auto"
    # render_encoder: "auto" (a discrete hardware encoder when it really starts)
    # | "nvenc" | "qsv" | "amf" (explicit, incl. laptop iGPUs) | "cpu"
    render_encoder: str = "auto"
    # render_hwaccel: hardware *decode* of source video. "auto" means OFF, and
    # that is measured, not cautious: frames must come back to system memory for
    # this project's CPU filter graph and software encoder, and the round trip
    # made every size slower on the reference laptop (3s 720p 120ms software vs
    # 955ms with -hwaccel cuda). Set "off" explicitly, or name one from
    # `ffmpeg -hwaccels` (cuda, d3d11va, dxva2...) to force it on for a
    # GPU-resident graph. Any failure still falls back to software.
    render_hwaccel: str = "auto"
    # Path to a specific ffmpeg build. Set this to use a build whose NVENC/AMF
    # API matches the installed driver (a newer ffmpeg can demand a newer driver).
    ffmpeg_binary: str | None = None
    # Extra ffmpeg builds to try when the primary one cannot start a hardware
    # encoder. os.pathsep-separated. The governor also probes a bundled
    # imageio-ffmpeg build when that package happens to be installed — one such
    # build targets the older NVENC API and unlocks NVENC on drivers too old for
    # the system ffmpeg, with nothing installed.
    ffmpeg_extra_binaries: str = ""
    # Emergency abort thresholds for a job that is ALREADY running. These sit
    # well outside the admission thresholds on purpose: ordinary load must never
    # kill work, only a machine genuinely in trouble.
    ram_abort_mb: int = Field(default=350, ge=0)
    gpu_abort_temperature_c: int = Field(default=90, ge=50, le=105)
    # How often a running job re-checks machine pressure while it runs.
    render_monitor_seconds: float = Field(default=3.0, ge=0.25, le=60.0)
    # Seconds a hardware profile is trusted before it is probed again.
    profile_ttl_seconds: float = Field(default=15.0, ge=1.0, le=600.0)
    # Heavy jobs (render, transcribe, OCR, vision) never overlap beyond this.
    max_heavy_jobs: int = Field(default=1, ge=1, le=4)
    # Waits longer than this stop waiting for a free machine and proceed anyway.
    heavy_wait_seconds: float = Field(default=900.0, ge=0.0, le=3600.0)
    # Concurrent GPU jobs. One on a laptop: the GPU also drives the display.
    gpu_max_jobs: int = Field(default=1, ge=1, le=4)
    # Above this temperature the GPU is left alone until it cools down.
    gpu_max_temperature_c: int = Field(default=82, ge=40, le=100)
    # Above this utilisation a new GPU job waits rather than piling on.
    gpu_max_utilization_pct: int = Field(default=90, ge=10, le=100)
    # VRAM kept free on top of each job's estimate (desktop compositor, browser).
    gpu_memory_headroom_mb: int = Field(default=600, ge=0, le=8000)
    # How long a job waits for GPU headroom before it honestly falls back to CPU.
    gpu_wait_seconds: float = Field(default=90.0, ge=0.0, le=1800.0)
    gpu_poll_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    # Transcribe a video below this free-RAM level on one thread only.
    ram_min_available_mb: int = Field(default=700, ge=0)
    # Speech-to-text: "auto" uses the GPU when torch reports CUDA, else CPU.
    transcribe_model: str = "base"
    transcribe_device: str = "auto"

    # --- Text-to-speech (AI voiceover) -----------------------------------------
    # engine: "edge" (neural, best quality) | "gtts" (fast fallback) | "off"
    tts_enabled: bool = True
    tts_engine: str = "edge"
    tts_voice: str | None = None
    tts_rate: str = "+0%"

    # --- Resilience (applies to every provider adapter) ----------------------
    http_timeout_seconds: float = 30.0
    http_connect_timeout_seconds: float = 5.0
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 0.5
    retry_max_delay_seconds: float = 30.0
    retry_jitter_ratio: float = 0.2
    circuit_failure_threshold: int = 5
    circuit_success_threshold: int = 2
    circuit_open_timeout_seconds: float = 30.0
    rate_limit_capacity: int = 4
    rate_limit_refill_per_second: float = 2.0


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance for the current process."""
    return Settings()
