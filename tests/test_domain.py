"""Tests for the application service (domain workflow)."""

from __future__ import annotations

import asyncio

import pytest

from content_factory.config import Settings
from content_factory.models import (
    ApprovalCreate,
    ApprovalStage,
    ApprovalVerdict,
    ProjectCreate,
    ProjectStatus,
    PublishCreate,
    ScriptUpdate,
)
from content_factory.providers import ProviderUnavailableError
from content_factory.service import (
    ContentFactoryService,
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)


def make_project(service: ContentFactoryService):
    return service.create_project(
        ProjectCreate(
            name="Demo",
            topic="A topic",
            target_language="vi",
            duration_target_seconds=45,
        )
    )


def approve_script(service: ContentFactoryService, project_id: str) -> None:
    service.update_script(
        project_id, ScriptUpdate(script="t", source_rights_confirmed=True)
    )
    service.approve(
        project_id,
        ApprovalCreate(stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.APPROVED),
    )


def test_create_project_defaults(service: ContentFactoryService) -> None:
    project = make_project(service)
    assert project.status == ProjectStatus.DRAFT
    assert project.script is None
    assert project.source_rights_confirmed is False
    assert project.approvals == []
    assert project.progress is None
    assert project.video is None


def test_get_project_not_found(service: ContentFactoryService) -> None:
    with pytest.raises(NotFoundError):
        service.get_project("missing")


def test_update_script_moves_draft_to_review(service: ContentFactoryService) -> None:
    project = make_project(service)
    updated = service.update_script(
        project.id, ScriptUpdate(script="Final text", source_rights_confirmed=True)
    )
    assert updated.status == ProjectStatus.SCRIPT_REVIEW
    assert updated.script == "Final text"
    assert updated.source_rights_confirmed is True


def test_regenerate_script_keeps_review_status(service: ContentFactoryService) -> None:
    project = make_project(service)
    service.update_script(project.id, ScriptUpdate(script="v1"))
    again = service.update_script(project.id, ScriptUpdate(script="v2"))
    assert again.status == ProjectStatus.SCRIPT_REVIEW
    assert again.script == "v2"


def test_update_script_rejected_after_approval(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    with pytest.raises(StateConflictError):
        service.update_script(project.id, ScriptUpdate(script="nope"))


def test_generate_script_without_providers_degrades(
    service: ContentFactoryService,
) -> None:
    project = make_project(service)
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(service.generate_script(project.id))


def test_generate_script_runs_research_when_missing(
    settings: Settings, service: ContentFactoryService
) -> None:
    from content_factory.providers import ProviderChain, ProviderTier, TemplateProvider

    service._providers = ProviderChain(
        settings.model_copy(update={"template_enabled": True}),
        providers={ProviderTier.LOCAL: TemplateProvider()},
    )
    project = make_project(service)
    result = asyncio.run(service.generate_script(project.id))
    assert result.research is not None
    assert result.research.sources
    assert result.research.key_facts
    assert "Evidence" in (result.script or "")
    assert result.provider_used == "template"


def test_generate_script_reuses_existing_research(
    settings: Settings,
    service: ContentFactoryService,
) -> None:
    from content_factory.providers import ProviderChain, ProviderTier, TemplateProvider

    service._providers = ProviderChain(
        settings.model_copy(update={"template_enabled": True}),
        providers={ProviderTier.LOCAL: TemplateProvider()},
    )
    project = make_project(service)
    project.research = service._research.research(project.topic)
    service._store.save(project)
    first = asyncio.run(service.generate_script(project.id))
    second = asyncio.run(service.generate_script(project.id))
    assert first.research is not None
    assert second.research is not None
    assert first.research.generated_at == second.research.generated_at


def test_research_method_populates_bundle(service: ContentFactoryService) -> None:
    project = make_project(service)
    researched = asyncio.run(service.research(project.id))
    assert researched.research is not None
    assert researched.research.sources
    assert researched.status == ProjectStatus.DRAFT


def test_approve_requires_confirmed_rights(service: ContentFactoryService) -> None:
    project = make_project(service)
    service.update_script(project.id, ScriptUpdate(script="t"))
    with pytest.raises(RightsNotConfirmedError):
        service.approve(
            project.id,
            ApprovalCreate(
                stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.APPROVED
            ),
        )


def test_approve_rejected_stays_in_review(service: ContentFactoryService) -> None:
    project = make_project(service)
    service.update_script(
        project.id, ScriptUpdate(script="t", source_rights_confirmed=True)
    )
    result = service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.REJECTED),
    )
    assert result.status == ProjectStatus.SCRIPT_REVIEW
    assert result.approvals[-1].verdict == ApprovalVerdict.REJECTED


def test_full_approval_flow(service: ContentFactoryService) -> None:
    project = make_project(service)
    service.update_script(
        project.id, ScriptUpdate(script="t", source_rights_confirmed=True)
    )
    approved = service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.APPROVED),
    )
    assert approved.status == ProjectStatus.SCRIPT_APPROVED
    assert approved.approvals[-1].stage == ApprovalStage.SCRIPT


def test_start_generation_requires_approval(service: ContentFactoryService) -> None:
    project = make_project(service)
    with pytest.raises(StateConflictError):
        service.start_generation(project.id)


def test_start_and_complete_generation(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    generating = service.start_generation(project.id)
    assert generating.status == ProjectStatus.GENERATING
    assert generating.progress == 0
    done = service.complete_generation(project.id)
    assert done.status == ProjectStatus.VIDEO_REVIEW
    assert done.progress == 100
    assert done.video is not None
    assert done.video.thumbnail_url == f"/projects/{project.id}/thumbnail"


def test_fail_generation(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    service.start_generation(project.id)
    failed = service.fail_generation(project.id, RuntimeError("renderer crashed"))
    assert failed.status == ProjectStatus.FAILED
    assert "renderer crashed" in (failed.error or "")


def test_retry_generation_after_failure(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    service.start_generation(project.id)
    service.fail_generation(project.id, RuntimeError("boom"))
    retried = service.start_generation(project.id)
    assert retried.status == ProjectStatus.GENERATING
    assert retried.error is None


def test_video_approval_flow(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    service.start_generation(project.id)
    service.complete_generation(project.id)
    approved = service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.VIDEO, verdict=ApprovalVerdict.APPROVED),
    )
    assert approved.status == ProjectStatus.VIDEO_APPROVED
    assert approved.approvals[-1].stage == ApprovalStage.VIDEO


def test_video_approval_requires_video_review(service: ContentFactoryService) -> None:
    project = make_project(service)
    with pytest.raises(StateConflictError):
        service.approve(
            project.id,
            ApprovalCreate(stage=ApprovalStage.VIDEO, verdict=ApprovalVerdict.APPROVED),
        )


def test_video_rejection_allows_rerender(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    service.start_generation(project.id)
    service.complete_generation(project.id)
    rejected = service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.VIDEO, verdict=ApprovalVerdict.REJECTED),
    )
    assert rejected.status == ProjectStatus.VIDEO_REVIEW
    rerendered = service.start_generation(project.id)
    assert rerendered.status == ProjectStatus.GENERATING


def test_publish_requires_approval(service: ContentFactoryService) -> None:
    project = make_project(service)
    with pytest.raises(StateConflictError):
        service.publish(project.id, PublishCreate(platforms=["youtube"]))


def test_publish_flow(service: ContentFactoryService) -> None:
    project = make_project(service)
    approve_script(service, project.id)
    service.start_generation(project.id)
    service.complete_generation(project.id)
    service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.VIDEO, verdict=ApprovalVerdict.APPROVED),
    )
    published = service.publish(
        project.id, PublishCreate(platforms=["youtube", "tiktok"])
    )
    assert published.status == ProjectStatus.PUBLISHED
    assert published.platforms == ["youtube", "tiktok"]
    assert published.published_at is not None
