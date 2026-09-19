"""Shared service context: settings, stores, the lifecycle state machine
and the background production worker.

Heavy engines (provider chain, research, federated search, document library,
media library, re-cook pipeline, TTS, image/voice studio, presets) are built
lazily on first use behind a double-checked lock: constructing a service is
cheap, and a code path that never touches an engine never pays to build it.
Domain mixins reach the engines through ``self._<engine>``, so laziness is
transparent to them; tests may still assign a fake to the same attribute.
"""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path
from typing import Any

from .. import script_engine
from ..config import Settings
from ..documents import FederatedSearcher, build_providers
from ..image_voice_service import ImageVoiceStudio
from ..library import DocumentLibrary
from ..media import MediaLibrary
from ..models import (
    Chunk,
    KBDocument,
    KnowledgeBase,
    MediaKind,
    Project,
    ProjectStatus,
    ScriptDocument,
    VideoAsset,
    VideoProject,
    WorkflowRun,
)
from ..presets import PresetLibrary
from ..providers import ProviderChain
from ..rag import KnowledgeRetriever
from ..recook import RecookPipeline
from ..research import ResearchEngine
from ..resources import ResourceGovernor
from ..scenes import build_video_project
from ..state import StateMachineError, assert_transition
from ..store import Store
from ..tts import TTSEngine
from .errors import (
    NotFoundError,
    StateConflictError,
)


class ServiceContext:
    """Shared service context: settings, stores, the lifecycle state machine.

    Cheap state (the store, worker registry, workflow runs, knowledge-engine
    maps) is built eagerly; every heavyweight engine is lazy — see the
    ``_build_once`` properties below.
    """

    @property
    def settings(self) -> Settings:
        """The runtime settings this service was built with."""
        return self._settings

    def __init__(self, settings: Settings, store: Store | None = None) -> None:
        self._settings = settings
        self._store = store or Store()
        self._workers: set[threading.Thread] = set()
        self._workflow_runs: dict[str, WorkflowRun] = {}
        self._workflow_lock = threading.Lock()
        # RAGFlow-style knowledge engine state (cheap; built eagerly).
        self._kbs: dict[str, KnowledgeBase] = {}
        self._kb_documents: dict[str, KBDocument] = {}
        self._chunks: dict[str, Chunk] = {}
        self._retriever = KnowledgeRetriever()
        # Compute governor: decides GPU vs CPU per job and serializes heavy work.
        # Cheap to build (the hardware probe only happens on first use).
        self._governor = ResourceGovernor(settings)
        # Lazy-engine caches, built on first access under ``_init_lock``.
        self._init_lock = threading.Lock()
        # The provider chain only assembles configuration objects (no I/O);
        # it stays eager so tests can swap it wholesale.
        self._providers = ProviderChain(settings)
        self._research_cache: ResearchEngine | None = None
        self._searcher_cache: FederatedSearcher | None = None
        self._library_cache: DocumentLibrary | None = None
        self._media_cache: MediaLibrary | None = None
        self._recook_cache: RecookPipeline | None = None
        self._tts_cache: TTSEngine | None = None
        self._studio_cache: ImageVoiceStudio | None = None
        self._presets_cache: PresetLibrary | None = None

    @property
    def store(self) -> Store:
        return self._store

    # --- Lazy engines ---------------------------------------------------------
    #
    # Built on first access (double-checked locking), so background threads —
    # the generation worker and voiceover synthesis — can reach them safely.

    @property
    def _research(self) -> ResearchEngine:
        if self._research_cache is None:
            with self._init_lock:
                if self._research_cache is None:
                    self._research_cache = ResearchEngine(
                        max_sources=self._settings.research_max_sources
                    )
        return self._research_cache

    @property
    def _searcher(self) -> FederatedSearcher:
        if self._searcher_cache is None:
            with self._init_lock:
                if self._searcher_cache is None:
                    self._searcher_cache = FederatedSearcher(
                        build_providers(self._settings)
                    )
        return self._searcher_cache

    @property
    def _library(self) -> DocumentLibrary:
        if self._library_cache is None:
            with self._init_lock:
                if self._library_cache is None:
                    self._library_cache = DocumentLibrary(
                        self._settings.library_dir, self._settings.library_db_path
                    )
        return self._library_cache

    @property
    def _media(self) -> MediaLibrary:
        if self._media_cache is None:
            with self._init_lock:
                if self._media_cache is None:
                    self._media_cache = MediaLibrary(
                        self._settings.media_dir,
                        chunk_bytes=self._settings.stream_chunk_bytes,
                        max_bytes=self._settings.upload_max_bytes,
                        governor=self._governor,
                        transcribe_model=self._settings.transcribe_model,
                        transcribe_device=self._settings.transcribe_device,
                        storage=self._build_media_storage(),
                    )
        return self._media_cache

    def _build_media_storage(self) -> Any:
        """Pick the media storage backend from settings (S3 when configured)."""
        from ..cloud import build_media_storage

        return build_media_storage(
            local_root=Path(self._settings.media_dir) / "files",
            s3_bucket=self._settings.s3_bucket or None,
            s3_endpoint=self._settings.s3_endpoint or None,
            s3_region=self._settings.s3_region or None,
            s3_access_key=self._settings.s3_access_key or None,
            s3_secret_key=self._settings.s3_secret_key or None,
            s3_prefix=self._settings.s3_prefix,
        )

    @property
    def _recook(self) -> RecookPipeline:
        if self._recook_cache is None:
            with self._init_lock:
                if self._recook_cache is None:
                    self._recook_cache = RecookPipeline(self._settings, self._media)
        return self._recook_cache

    @property
    def _tts(self) -> TTSEngine:
        if self._tts_cache is None:
            with self._init_lock:
                if self._tts_cache is None:
                    self._tts_cache = TTSEngine(self._settings)
        return self._tts_cache

    @property
    def _studio(self) -> ImageVoiceStudio:
        if self._studio_cache is None:
            with self._init_lock:
                if self._studio_cache is None:
                    self._studio_cache = ImageVoiceStudio(self._settings.library_dir)
        return self._studio_cache

    @property
    def _presets(self) -> PresetLibrary:
        if self._presets_cache is None:
            with self._init_lock:
                if self._presets_cache is None:
                    self._presets_cache = PresetLibrary(self._settings.presets_dir)
        return self._presets_cache

    @property
    def governor(self) -> ResourceGovernor:
        """The compute governor shared by every heavy job in this service."""
        return self._governor

    @property
    def providers(self) -> ProviderChain:
        return self._providers

    @property
    def presets(self) -> PresetLibrary:
        return self._presets

    def get_project(self, project_id: str) -> Project:
        project = self._store.get(project_id)
        if project is None:
            raise NotFoundError(f"No project '{project_id}'.")
        return project

    def complete_generation(self, project_id: str) -> Project:
        """Finish production: build the editable video project and enter review."""
        project = self.get_project(project_id)
        self._transition(project, ProjectStatus.VIDEO_REVIEW)
        project.progress = 100
        project.video_project = self._rebuild_video_project(project)
        self._attach_source_footage(project)
        project.video = VideoAsset(
            asset_url=f"/projects/{project.id}/video",
            thumbnail_url=f"/projects/{project.id}/thumbnail",
            duration_seconds=project.duration_target_seconds,
            format=self._settings.video_format,
            size_bytes=project.duration_target_seconds * 250_000,
        )
        project.error = None
        return self._store.save(project)

    def fail_generation(self, project_id: str, error: Exception) -> Project:
        """Mark production as failed with the underlying error."""
        project = self.get_project(project_id)
        self._transition(project, ProjectStatus.FAILED)
        project.error = str(error)
        return self._store.save(project)

    def _rebuild_video_project(self, project: Project) -> VideoProject:
        """Rebuild the timeline from the script, reusing the previous scene ids.

        Every rebuild goes through here so a scene keeps its id for the life of
        the project: an agent or the UI caches those ids, and a rebuild that
        renamed them all turned the next edit into a 404.
        """
        return build_video_project(
            project.script,
            project.duration_target_seconds,
            project.target_language,
            previous=project.video_project,
        )

    def _attach_source_footage(self, project: Project) -> None:
        """Turn on the music bed for a re-cooked project.

        The visual layer is supplied at render time from the source video (see
        ``_background_video_for``), so here we only flag that a soundtrack is
        wanted. Source rights are never auto-confirmed.
        """
        if project.video_project is None or not project.source_media_id:
            return
        try:
            item = self._media.require(project.source_media_id)
        except KeyError:
            return
        if item.kind == MediaKind.VIDEO:
            project.video_project.background_music = True

    def _transition(self, project: Project, target: ProjectStatus) -> None:
        try:
            assert_transition(project.status, target)
        except StateMachineError as exc:
            raise StateConflictError(str(exc)) from exc
        project.status = target

    # --- Generation worker ---------------------------------------------------

    def _spawn_worker(self, project_id: str) -> None:
        self._register_worker(
            threading.Thread(
                target=self._produce,
                args=(project_id,),
                name=f"generation-{project_id}",
                daemon=True,
            )
        )

    def _register_worker(self, thread: threading.Thread) -> None:
        """Track a background worker, pruning finished threads first.

        Without the prune the registry grows by one dead thread per job for
        the life of the process.
        """
        self._workers = {t for t in self._workers if t.is_alive()}
        self._workers.add(thread)
        thread.start()

    def wait_for_workers(
        self, timeout: float = 60.0, *, project_id: str | None = None
    ) -> bool:
        """Wait for background workers to settle; ``False`` if the deadline passes.

        A heavy operation that mutates a project — the render export above all
        — cannot run while the generation worker is still rewriting that same
        project: the compare-and-save at the end of a render rejects the export
        ("Project changed during rendering"), and the caller loses the whole
        render. Waiting for the worker first turns a guaranteed loss into a
        short pause. ``project_id`` narrows the wait to that project's worker.
        """
        deadline = time.monotonic() + max(0.0, timeout)
        name = f"generation-{project_id}" if project_id else None
        while True:
            pending = [
                thread
                for thread in self._workers
                if thread.is_alive() and (name is None or thread.name == name)
            ]
            if not pending:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            for thread in pending:
                thread.join(timeout=remaining)

    def _produce(self, project_id: str) -> None:
        """Background loop simulating rendering progress, then finalizing."""
        steps = max(1, self._settings.generation_steps)
        delay = max(0.0, self._settings.generation_step_delay_seconds)
        try:
            for step in range(1, steps + 1):
                time.sleep(delay)
                project = self.get_project(project_id)
                project.progress = int(step / steps * 100)
                self._store.save(project)
            self.complete_generation(project_id)
        except Exception as exc:  # noqa: BLE001 - a failed generation must still be marked failed on the project
            with contextlib.suppress(Exception):
                self.fail_generation(project_id, exc)

    def _refresh_analysis(self, project: Project) -> None:
        """Recompute the stored timing plan, lint findings and script document.

        All three are derived from the same analysis pass, so they are refreshed
        together and can never disagree about what the script says.
        """
        if not project.script:
            project.script_plan = None
            project.script_issues = []
            project.script_document = None
            return
        analysis = script_engine.analyze_script(
            project.script,
            language=project.target_language,
            target_seconds=project.duration_target_seconds,
            style=self._presets.resolve(project.script_style),
            research=project.research,
        )
        project.script_plan = analysis.plan
        project.script_issues = analysis.issues
        project.script_document = ScriptDocument(
            topic=project.topic,
            style=project.script_style,
            raw_script=project.script,
            sections=list(analysis.plan.sections),
            timing_plan=analysis.plan,
            language=analysis.plan.language,
            target_seconds=analysis.plan.target_seconds,
            estimated_seconds=analysis.plan.estimated_seconds,
        )
