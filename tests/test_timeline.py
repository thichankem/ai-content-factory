"""Tests for the video editing engine."""

from __future__ import annotations

import pytest

from content_factory.models import (
    ColorGrade,
    IssueSeverity,
    Keyframe,
    SceneEffect,
    SceneMotion,
    TimelineMarker,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
)
from content_factory.scenes import build_video_project
from content_factory.timeline import (
    ASPECT_PRESETS,
    add_marker,
    bulk_update,
    caption_cues,
    compile_render_plan,
    contrast_ratio,
    delete_scene,
    duplicate_scene,
    evaluate_motion,
    find_scene,
    measure,
    merge_scene,
    move_scene,
    normalize,
    remove_marker,
    report,
    resolution,
    scene_seconds,
    set_keyframes,
    split_scene,
    total_seconds,
    transition_seconds,
)

SCRIPT = (
    "[Hook]\nThe city whispers before it wakes.\n\n"
    "[Turn]\nTrucks and shutters are the only choir.\n\n"
    "[Payoff]\nListen at 5am and you hear who really runs this place."
)


def make_project(**overrides: object) -> VideoProject:
    project = build_video_project(SCRIPT, 30, "en")
    for key, value in overrides.items():
        setattr(project, key, value)
    return project


def scene(**overrides: object) -> VideoScene:
    base: dict[str, object] = {
        "id": "s1",
        "label": "Scene",
        "text": "Hello there friend",
        "duration_seconds": 3.0,
    }
    base.update(overrides)
    return VideoScene(**base)  # type: ignore[arg-type]


# --- normalize ---------------------------------------------------------------


def test_normalize_assigns_unique_ids() -> None:
    project = VideoProject(
        scenes=[
            scene(id="dup"),
            scene(id="dup"),
            scene(id=""),
        ]
    )
    normalize(project)
    ids = [item.id for item in project.scenes]
    assert len(set(ids)) == 3
    assert all(ids)


def test_normalize_sorts_and_dedupes_keyframes() -> None:
    project = VideoProject(
        scenes=[
            scene(
                keyframes=[
                    Keyframe(at=0.8, scale=1.4),
                    Keyframe(at=0.2, scale=1.1),
                    Keyframe(at=0.2, scale=1.9),
                ]
            )
        ]
    )
    normalize(project)
    track = project.scenes[0].keyframes
    assert [frame.at for frame in track] == [0.2, 0.8]
    assert track[0].scale == 1.9


def test_normalize_clears_transition_on_first_scene() -> None:
    project = VideoProject(
        scenes=[scene(id="a", transition=VideoTransition.FADE), scene(id="b")]
    )
    normalize(project)
    assert project.scenes[0].transition == VideoTransition.CUT


def test_normalize_repairs_aspect_and_colours() -> None:
    project = make_project(aspect_ratio="42:1")
    project.scenes[0].background = "not-a-colour"
    project.scenes[0].text_color = "#zzz"
    normalize(project)
    assert project.aspect_ratio == "9:16"
    assert project.scenes[0].background == "#1a1d27"
    assert project.scenes[0].text_color == "#ffffff"


def test_normalize_adds_a_scene_when_empty() -> None:
    project = VideoProject(scenes=[])
    normalize(project)
    assert len(project.scenes) == 1
    assert project.scenes[0].transition == VideoTransition.CUT


def test_normalize_is_idempotent() -> None:
    project = make_project()
    normalize(project)
    first = project.model_dump()
    normalize(project)
    assert project.model_dump() == first


# --- measurement -------------------------------------------------------------


def test_scene_seconds_honours_speed() -> None:
    assert scene_seconds(scene(duration_seconds=6.0, speed=2.0)) == 3.0
    assert scene_seconds(scene(duration_seconds=6.0, speed=1.0)) == 6.0


def test_transition_seconds_is_bounded_by_both_neighbours() -> None:
    previous = scene(id="a", duration_seconds=1.0)
    current = scene(id="b", duration_seconds=12.0, transition=VideoTransition.FADE)
    combined = transition_seconds(current, previous)
    assert combined == pytest.approx(min(0.5, 1.0, 12.0))
    assert transition_seconds(current, None) == 0.0
    cut = scene(id="c", transition=VideoTransition.CUT)
    assert transition_seconds(cut, previous) == 0.0


def test_total_seconds_matches_sum_of_scenes() -> None:
    project = make_project()
    assert total_seconds(project) == round(
        sum(scene_seconds(item) for item in project.scenes), 2
    )


def test_measure_reports_pacing_metrics() -> None:
    stats = measure(make_project())
    assert stats.scene_count == 3
    assert stats.total_seconds == 30.0
    assert stats.words > 0
    assert stats.words_per_minute > 0
    assert 0 < stats.cuts_per_minute < 60
    assert stats.shortest_scene_seconds <= stats.average_scene_seconds
    assert stats.longest_scene_seconds >= stats.average_scene_seconds


def test_resolution_uses_aspect_presets() -> None:
    assert resolution(make_project(aspect_ratio="9:16")) == (1080, 1920)
    assert resolution(make_project(aspect_ratio="16:9")) == ASPECT_PRESETS["16:9"]
    assert resolution(make_project(aspect_ratio="nonsense")) == ASPECT_PRESETS["9:16"]


# --- validation --------------------------------------------------------------


def test_report_flags_an_empty_timeline() -> None:
    result = report(VideoProject(scenes=[]))
    assert result.issues[0].code == "empty_timeline"
    assert result.issues[0].severity == IssueSeverity.ERROR


def test_report_penalizes_findings() -> None:
    clean = report(make_project())
    assert clean.score < 100  # flat look + no markers
    empty = report(VideoProject(scenes=[]))
    assert empty.score < clean.score


def test_report_flags_short_scene_and_frantic_pacing() -> None:
    project = VideoProject(
        scenes=[scene(id=f"s{index}", duration_seconds=0.6) for index in range(6)]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "scene_too_short" in codes
    assert "frantic_pacing" in codes


def test_report_flags_long_text_and_overflowing_narration() -> None:
    project = VideoProject(
        scenes=[
            scene(
                id="a",
                text="A " * 200,
                narration="word " * 40,
                duration_seconds=2.0,
            )
        ]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "text_overflows_scene" in codes
    assert "narration_overflows_scene" in codes


def test_report_flags_low_contrast_and_flat_look() -> None:
    project = VideoProject(
        scenes=[scene(id="a", text_color="#101010", background="#101010")]
    )
    issues = report(project).issues
    codes = {issue.code for issue in issues}
    assert "low_text_contrast" in codes
    assert "flat_look" in codes


def test_report_reports_partial_flat_look() -> None:
    project = VideoProject(
        scenes=[
            scene(id="a"),
            scene(id="b", filter=VideoFilter.WARM),
        ]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "flat_look_partial" in codes
    assert "flat_look" not in codes


def test_report_flags_empty_scene() -> None:
    project = VideoProject(scenes=[scene(id="a", text="", narration="")])
    codes = {issue.code for issue in report(project).issues}
    assert "empty_scene" in codes


def test_report_flags_transition_longer_than_neighbour() -> None:
    project = VideoProject(
        scenes=[
            scene(id="a", duration_seconds=3.0, transition=VideoTransition.FADE),
            scene(
                id="b",
                duration_seconds=1.0,
                transition=VideoTransition.DISSOLVE,
            ),
        ]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "transition_too_long" in codes


def test_report_flags_narration_underfilling_the_cut() -> None:
    project = VideoProject(
        scenes=[scene(id="a", text="Short.", narration="Short.", duration_seconds=50.0)]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "narration_underfills" in codes


def test_report_flags_duration_drift_against_target() -> None:
    project = make_project()
    codes = {issue.code for issue in report(project, target_seconds=120).issues}
    assert "duration_drift" in codes


def test_report_flags_out_of_range_marker_and_missing_markers() -> None:
    project = VideoProject(
        scenes=[scene(id="a")],
        markers=[TimelineMarker(id="m1", time_seconds=999.0, label="far")],
    )
    codes = {issue.code for issue in report(project).issues}
    assert "marker_out_of_range" in codes
    assert "no_markers" not in codes


def test_report_flags_speed_extreme() -> None:
    project = VideoProject(scenes=[scene(id="a", duration_seconds=1.0, speed=2.0)])
    codes = {issue.code for issue in report(project).issues}
    assert "speed_extreme" in codes


def test_contrast_ratio_extremes() -> None:
    assert contrast_ratio("#ffffff", "#000000") == 21.0
    assert contrast_ratio("#ffffff", "#ffffff") == 1.0
    assert contrast_ratio("#fff", "#000") == 21.0
    assert contrast_ratio("bogus", "#000000") >= 1.0


def test_report_flags_opening_transition_on_a_raw_project() -> None:
    project = VideoProject(
        scenes=[scene(id="a", transition=VideoTransition.FADE), scene(id="b")]
    )
    codes = {issue.code for issue in report(project).issues}
    assert "opening_transition" in codes


# --- structural edits --------------------------------------------------------


def test_split_scene_preserves_total_duration() -> None:
    project = make_project()
    before = total_seconds(project)
    target = project.scenes[0].id
    split_scene(project, target, 0.5)
    assert len(project.scenes) == 4
    assert project.scenes[1].label.endswith("(b)")
    assert total_seconds(project) == pytest.approx(before, abs=0.05)
    assert project.scenes[1].transition == VideoTransition.CUT


def test_split_scene_keeps_both_halves_non_empty_on_odd_input() -> None:
    project = VideoProject(
        scenes=[
            scene(id="a", text="one two three four", narration="one two three four")
        ]
    )
    split_scene(project, "a", 0.5)
    assert project.scenes[0].text == "one two"
    assert project.scenes[1].text == "three four"


def test_merge_scene_reverses_a_split() -> None:
    project = make_project()
    original_text = project.scenes[0].text
    before = total_seconds(project)
    split_scene(project, project.scenes[0].id, 0.5)
    merge_scene(project, project.scenes[0].id)
    assert len(project.scenes) == 3
    assert project.scenes[0].text == original_text
    assert total_seconds(project) == pytest.approx(before, abs=0.05)


def test_merge_scene_rejects_the_last_scene() -> None:
    project = make_project()
    with pytest.raises(ValueError):
        merge_scene(project, project.scenes[-1].id)


def test_duplicate_scene_inserts_a_clone() -> None:
    project = make_project()
    duplicate_scene(project, project.scenes[0].id)
    assert len(project.scenes) == 4
    assert project.scenes[1].label.endswith("copy")
    assert project.scenes[1].id != project.scenes[0].id


def test_delete_scene_removes_it() -> None:
    project = make_project()
    target = project.scenes[1].id
    delete_scene(project, target)
    assert len(project.scenes) == 2
    assert all(item.id != target for item in project.scenes)


def test_delete_scene_refuses_to_empty_the_timeline() -> None:
    project = VideoProject(scenes=[scene(id="only")])
    with pytest.raises(ValueError):
        delete_scene(project, "only")


def test_move_scene_reorders() -> None:
    project = make_project()
    labels = [item.label for item in project.scenes]
    move_scene(project, project.scenes[2].id, 0)
    assert [item.label for item in project.scenes] == [labels[2], labels[0], labels[1]]
    move_scene(project, project.scenes[0].id, 99)
    assert [item.label for item in project.scenes][-1] == labels[2]


def test_unknown_scene_id_raises_key_error() -> None:
    project = make_project()
    with pytest.raises(KeyError):
        find_scene(project, "nope")
    for operation in (
        lambda: split_scene(project, "nope"),
        lambda: duplicate_scene(project, "nope"),
        lambda: move_scene(project, "nope", 0),
        lambda: delete_scene(project, "nope"),
    ):
        with pytest.raises(KeyError):
            operation()


def test_bulk_update_applies_only_known_fields() -> None:
    project = make_project()
    ids = [item.id for item in project.scenes[:2]]
    bulk_update(
        project,
        ids,
        {
            "filter": VideoFilter.WARM,
            "grade": ColorGrade.TEAL_ORANGE,
            "text_color": "#fafafa",
            "not_a_field": "ignored",
            "id": "hijacked",
        },
    )
    for item in project.scenes[:2]:
        assert item.filter == VideoFilter.WARM
        assert item.grade == ColorGrade.TEAL_ORANGE
        assert item.text_color == "#fafafa"
        assert item.id in ids


def test_bulk_update_coerces_enum_values() -> None:
    project = make_project()
    ids = [item.id for item in project.scenes]
    bulk_update(project, ids, {"grade": "noir", "transition": "wipe"})
    assert isinstance(project.scenes[0].grade, ColorGrade)
    assert project.scenes[0].grade == ColorGrade.NOIR
    # normalize() keeps the opening scene on a hard cut, the rest get the wipe.
    assert project.scenes[0].transition == VideoTransition.CUT
    assert project.scenes[1].transition == VideoTransition.WIPE
    assert isinstance(project.scenes[1].transition, VideoTransition)


def test_bulk_update_rejects_invalid_values() -> None:
    project = make_project()
    ids = [item.id for item in project.scenes]
    with pytest.raises(ValueError):
        bulk_update(project, ids, {"grade": "banana"})


def test_bulk_update_rejects_empty_patch_and_unknown_ids() -> None:
    project = make_project()
    with pytest.raises(ValueError):
        bulk_update(project, [project.scenes[0].id], {"id": "x"})
    with pytest.raises(KeyError):
        bulk_update(project, ["missing"], {"filter": VideoFilter.WARM})


def test_set_keyframes_replaces_the_track() -> None:
    project = make_project()
    set_keyframes(
        project,
        project.scenes[0].id,
        [Keyframe(at=1.0, scale=1.5), Keyframe(at=0.0, scale=1.0)],
    )
    assert [frame.at for frame in project.scenes[0].keyframes] == [0.0, 1.0]


def test_markers_can_be_added_and_removed() -> None:
    project = make_project()
    add_marker(project, 5.0, "hook beat", "#ff0000")
    assert project.markers[0].label == "hook beat"
    marker_id = project.markers[0].id
    remove_marker(project, marker_id)
    assert project.markers == []
    with pytest.raises(KeyError):
        remove_marker(project, marker_id)


def test_marker_time_is_clamped_to_the_timeline() -> None:
    project = make_project()
    add_marker(project, 9999.0, "far")
    assert project.markers[0].time_seconds == total_seconds(project)


# --- motion ------------------------------------------------------------------


def test_evaluate_motion_without_any_track_is_neutral() -> None:
    values = evaluate_motion(scene(), 0.5)
    assert values == {
        "scale": 1.0,
        "rotation": 0.0,
        "opacity": 1.0,
        "pos_x": 0.0,
        "pos_y": 0.0,
    }


def test_evaluate_motion_animates_scene_motion() -> None:
    animated = scene(motion=SceneMotion(scale=1.5, opacity=0.5, easing="linear"))
    start = evaluate_motion(animated, 0.0)
    middle = evaluate_motion(animated, 0.5)
    end = evaluate_motion(animated, 1.0)
    assert start["scale"] == pytest.approx(1.0)
    assert middle["scale"] == pytest.approx(1.25)
    assert end["scale"] == pytest.approx(1.5)
    assert end["opacity"] == pytest.approx(0.5)


def test_evaluate_motion_interpolates_keyframes() -> None:
    tracked = scene(
        keyframes=[
            Keyframe(at=0.0, scale=1.0, pos_x=0.0),
            Keyframe(at=1.0, scale=2.0, pos_x=100.0, easing="linear"),
        ]
    )
    assert evaluate_motion(tracked, 0.0)["scale"] == pytest.approx(1.0)
    assert evaluate_motion(tracked, 0.25)["scale"] == pytest.approx(1.25)
    assert evaluate_motion(tracked, 0.5)["pos_x"] == pytest.approx(50.0)
    assert evaluate_motion(tracked, 1.0)["scale"] == pytest.approx(2.0)
    # Outside the track it clamps to the nearest keyframe.
    assert evaluate_motion(tracked, -1.0)["scale"] == pytest.approx(1.0)
    assert evaluate_motion(tracked, 5.0)["scale"] == pytest.approx(2.0)


def test_evaluate_motion_prefers_keyframes_over_motion() -> None:
    both = scene(
        motion=SceneMotion(scale=1.9, easing="linear"),
        keyframes=[Keyframe(at=0.0, scale=1.1), Keyframe(at=1.0, scale=1.1)],
    )
    assert evaluate_motion(both, 1.0)["scale"] == pytest.approx(1.1)


# --- captions and render plan ------------------------------------------------


def test_caption_cues_stay_inside_their_scene() -> None:
    project = make_project()
    plan = compile_render_plan(project, "demo")
    assert plan.subtitles
    for step in plan.steps:
        cues = [cue for cue in plan.subtitles if cue.scene_id == step.scene_id]
        for cue in cues:
            assert step.start_seconds - 0.01 <= cue.start_seconds
            assert cue.end_seconds <= step.end_seconds + 0.01


def test_caption_cues_split_long_narration() -> None:
    long_scene = scene(
        id="long",
        text="",
        narration=" ".join(f"word{i}" for i in range(40)),
        duration_seconds=20.0,
    )
    project = VideoProject(scenes=[long_scene])
    plan = compile_render_plan(project)
    assert len(plan.subtitles) > 1
    assert plan.subtitles[0].index == 0
    assert all(cue.text for cue in plan.subtitles)


def test_caption_cues_are_one_per_scene_when_captions_are_off() -> None:
    project = make_project(captions=False)
    plan = compile_render_plan(project)
    assert len(plan.subtitles) == len(plan.steps)


def test_caption_cues_helper_matches_the_plan() -> None:
    project = make_project()
    steps = compile_render_plan(project).steps
    assert caption_cues(project, steps) == compile_render_plan(project).subtitles


def test_render_plan_has_absolute_slots_and_transitions() -> None:
    project = make_project()
    plan = compile_render_plan(project, "p1")
    assert plan.project_id == "p1"
    assert (plan.width, plan.height) == (1080, 1920)
    assert plan.fps == 30
    cursor = 0.0
    for step in plan.steps:
        assert step.start_seconds == pytest.approx(cursor, abs=0.01)
        cursor = step.end_seconds
    assert plan.total_seconds == pytest.approx(total_seconds(project), abs=0.01)
    assert plan.steps[0].transition_in == VideoTransition.CUT
    assert plan.steps[0].transition_seconds == 0.0
    assert plan.steps[1].transition_seconds > 0


def test_render_plan_exposes_keyframes_and_source_in() -> None:
    project = make_project()
    project.scenes[0].trim_start = 1.5
    project.scenes[0].keyframes = [Keyframe(at=0.0), Keyframe(at=1.0, scale=1.4)]
    plan = compile_render_plan(project)
    assert plan.steps[0].source_in_seconds == 1.5
    assert len(plan.steps[0].keyframes) == 2


def test_render_plan_wires_narration_urls_and_audio_layers() -> None:
    project = make_project()
    scene_id = project.scenes[0].id
    plan = compile_render_plan(project, "p1", {scene_id: "/audio/0.mp3"})
    assert plan.steps[0].narration_url == "/audio/0.mp3"
    voiceover = next(layer for layer in plan.audio if layer.kind == "voiceover")
    assert voiceover.enabled is True
    music = next(layer for layer in plan.audio if layer.kind == "music")
    assert music.enabled is False
    assert music.bpm is None


def test_render_plan_warns_for_unknown_aspect_ratio() -> None:
    project = make_project(aspect_ratio="42:1")
    plan = compile_render_plan(project, "p1")
    assert plan.width == 1080
    assert any("42:1" in warning for warning in plan.warnings), plan.warnings


def test_render_plan_warns_when_no_scene_has_an_image() -> None:
    plan = compile_render_plan(make_project())
    assert any("source image" in warning for warning in plan.warnings), plan.warnings


def test_render_plan_has_no_visual_warning_when_images_exist() -> None:
    project = make_project()
    project.scenes[0].image_url = "/library/photos/sky.jpg"
    plan = compile_render_plan(project)
    assert not any("source image" in warning for warning in plan.warnings)


def test_render_plan_marks_look_effects() -> None:
    project = make_project()
    project.scenes[0].effect = SceneEffect.GLITCH
    project.scenes[0].grade = ColorGrade.NOIR
    project.scenes[0].filter = VideoFilter.CONTRAST
    plan = compile_render_plan(project)
    assert plan.steps[0].effect == SceneEffect.GLITCH
    assert plan.steps[0].grade == ColorGrade.NOIR
