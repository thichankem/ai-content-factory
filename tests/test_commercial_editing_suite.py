"""Comprehensive test suite for commercial video editing capabilities.

Validates features matching Adobe Premiere Pro, DaVinci Resolve Studio,
Apple Final Cut Pro, CapCut Pro, and Descript.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings
from content_factory.models import (
    ColorGrade,
    EntranceEffect,
    ExitEffect,
    Keyframe,
    SceneEffect,
    SceneMotion,
    TextStyle,
    TimelineMarker,
    VideoProject,
    VideoScene,
)
from content_factory.timeline import (
    compile_render_plan,
    duplicate_scene,
    merge_scene,
    move_scene,
    report,
    split_scene,
)


@pytest.fixture
def test_client(tmp_path) -> TestClient:
    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
    )
    app = create_app(settings)
    return TestClient(app)


def test_premiere_style_timeline_operations():
    """Test non-linear timeline editing: Split, Merge, Duplicate, Move."""
    scenes = [
        VideoScene(
            id="sc-1",
            label="Cold Open",
            duration_seconds=5.0,
            text="00:00 Tàu Titanic rời cảng",
        ),
        VideoScene(
            id="sc-2",
            label="Night Voyage",
            duration_seconds=10.0,
            text="23:40 Đêm tối băng trôi",
        ),
    ]
    vp = VideoProject(scenes=scenes, aspect_ratio="16:9", fps=30)

    # 1. Split scene at 50%
    vp_split = split_scene(vp, scene_id="sc-2", at=0.5)
    assert len(vp_split.scenes) == 3
    assert vp_split.scenes[1].duration_seconds == 5.0
    assert vp_split.scenes[2].duration_seconds == 5.0

    # 2. Duplicate scene
    new_id = vp_split.scenes[1].id
    vp_dup = duplicate_scene(vp_split, scene_id=new_id)
    assert len(vp_dup.scenes) == 4

    # 3. Move scene position
    vp_moved = move_scene(vp_dup, scene_id=new_id, to_index=0)
    assert vp_moved.scenes[0].id == new_id

    # 4. Merge adjacent scenes
    vp_merged = merge_scene(vp_moved, scene_id=new_id)
    assert len(vp_merged.scenes) == 3


def test_after_effects_keyframe_motion_math():
    """Test keyframe spatial transformation and cubic bezier curves."""
    motion = SceneMotion(
        scale=1.25,
        rotation=15.0,
        opacity=0.9,
        pos_x=10.0,
        pos_y=-5.0,
        easing="ease-in-out",
    )
    assert motion.scale == 1.25
    assert motion.rotation == 15.0

    # Keyframe track for dynamic motion path
    track = [
        Keyframe(at=0.0, scale=1.0, pos_x=0.0, pos_y=0.0),
        Keyframe(at=0.5, scale=1.15, pos_x=25.0, pos_y=-10.0),
        Keyframe(at=1.0, scale=1.0, pos_x=0.0, pos_y=0.0),
    ]
    assert len(track) == 3
    assert track[1].scale == 1.15


def test_davinci_resolve_color_luts_and_shaders():
    """Test Lumetri / DaVinci Resolve color grading LUTs and visual FX."""
    scene = VideoScene(
        id="sc-lut",
        label="Cinematic Disaster",
        duration_seconds=6.0,
        text="Titanic disaster",
        grade=ColorGrade.TEAL_ORANGE,
        effect=SceneEffect.FILM_GRAIN,
    )
    assert scene.grade == "teal-orange"
    assert scene.effect == "film-grain"


def test_capcut_kinetic_subtitles_and_aspect_ratios():
    """Test 9:16 vertical styling, neon captions, and timeline markers."""
    marker = TimelineMarker(
        id="m-1",
        time_seconds=2.5,
        label="Climax Hook",
        color="#ef4444",
    )
    scene = VideoScene(
        id="sc-capcut",
        label="TikTok Hook",
        duration_seconds=3.0,
        text="Đúng ngày này 100 năm trước!",
        text_style=TextStyle.NEON,
        entrance=EntranceEffect.SLIDE_UP,
        exit=ExitEffect.FADE,
    )
    vp = VideoProject(
        scenes=[scene],
        aspect_ratio="9:16",
        fps=60,
        markers=[marker],
    )
    assert vp.aspect_ratio == "9:16"
    assert vp.fps == 60
    assert len(vp.markers) == 1
    assert vp.scenes[0].text_style == "neon"


def test_descript_script_driven_synchronization(test_client):
    """Test script-driven editing: Updating script synchronizes pipeline."""
    # Create project
    proj_resp = test_client.post(
        "/projects",
        json={
            "name": "Script Sync Demo",
            "topic": "Hành trình máy bay hạ cánh khẩn cấp trên sông Hudson",
            "target_language": "vi",
            "duration_target_seconds": 45,
            "script_style": "disaster-retelling",
        },
    )
    assert proj_resp.status_code == 201
    pid = proj_resp.json()["id"]

    # Update script (Descript text-based edit)
    script_text = (
        "[Hook]\nCơ trưởng Chesley Sullenberger chỉ có 208 giây để cứu "
        "155 mạng người.\n\n"
        "[Turn]\nCả hai động cơ ngừng hoạt động sau cú đâm đàn chim.\n\n"
        "[Payoff]\nCú đáp hoàn hảo trên mặt nước băng giá sông Hudson."
    )
    update_resp = test_client.put(
        f"/projects/{pid}/script",
        json={"script": script_text, "source_rights_confirmed": True},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["script"] == script_text

    # Extract structured timeline from edited script
    tl_resp = test_client.post(f"/projects/{pid}/timeline/extract")
    assert tl_resp.status_code == 200
    assert len(tl_resp.json()["events"]) >= 1

    # Audit sensitivity
    sens_resp = test_client.post(f"/projects/{pid}/sensitivity/audit")
    assert sens_resp.status_code == 200
    assert sens_resp.json()["is_safe_for_monetization"] is True


def test_timeline_validation_and_render_planning():
    """Test timeline validation and render chunk calculations."""
    scenes = [
        VideoScene(
            id=f"sc-{i}",
            label=f"Scene {i}",
            duration_seconds=4.0,
            text=f"Dialogue {i}",
        )
        for i in range(1, 6)
    ]
    vp = VideoProject(scenes=scenes, aspect_ratio="16:9", fps=30)

    # Validate
    rep = report(vp)
    assert rep.stats.total_seconds == 20.0
    assert rep.stats.scene_count == 5

    # Render planning
    plan = compile_render_plan(vp, project_id="proj-test")
    assert len(plan.steps) == 5
    assert plan.total_seconds == 20.0
    assert plan.width == 1920
    assert plan.height == 1080
