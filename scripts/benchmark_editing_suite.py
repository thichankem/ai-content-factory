"""Benchmark commercial video editing and specialized pipeline capabilities.

Measures throughput and latency across:
- Non-linear timeline editing (Split, Merge, Duplicate, Move, Bulk Update)
- Motion & Keyframe cubic-bezier evaluation (After Effects style)
- Color grading, shaders, and video validation rules (DaVinci / Premiere style)
- Kinetic subtitle cues and render plan compilation (CapCut / Descript style)
- Procedural graphics generation (SVG route maps & comparative infographics)
- Sensitivity auditing & multi-source fact reconciliation
- Historical events and 'On This Day' query performance

Usage:
    python scripts/benchmark_editing_suite.py [--runs N]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from content_factory.map_generator import (  # noqa: E402
    generate_infographic_svg,
    generate_route_map_svg,
)
from content_factory.models import (  # noqa: E402
    ColorGrade,
    FactClaim,
    InfographicSpec,
    Keyframe,
    MapRoutePoint,
    MapRouteSpec,
    SceneEffect,
    TextStyle,
    VideoProject,
    VideoScene,
)
from content_factory.on_this_day import (  # noqa: E402
    get_events_for_date,
    search_historical_events,
)
from content_factory.research import (  # noqa: E402
    extract_structured_timeline,
    reconcile_facts,
)
from content_factory.sensitivity import audit_sensitivity  # noqa: E402
from content_factory.timeline import (  # noqa: E402
    bulk_update,
    compile_render_plan,
    duplicate_scene,
    evaluate_motion,
    merge_scene,
    move_scene,
    report,
    split_scene,
)


def create_sample_project(scene_count: int = 10) -> VideoProject:
    scenes = [
        VideoScene(
            id=f"sc-{i}",
            label=f"Scene {i + 1}",
            duration_seconds=5.0,
            text=f"Phân cảnh {i + 1}: diễn biến sự kiện lịch sử.",
            narration=f"Lời bình phân cảnh {i + 1} tại thời điểm này.",
            grade=ColorGrade.TEAL_ORANGE if i % 2 == 0 else ColorGrade.NOIR,
            effect=SceneEffect.FILM_GRAIN if i % 3 == 0 else SceneEffect.NONE,
            text_style=TextStyle.NEON if i % 2 == 1 else TextStyle.NORMAL,
        )
        for i in range(scene_count)
    ]
    return VideoProject(scenes=scenes, aspect_ratio="16:9", fps=30)


def bench(label: str, fn, runs: int) -> float:
    samples: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    average = statistics.mean(samples)
    ops_per_sec = 1.0 / average if average > 0 else float("inf")
    print(f"{label:<52} {average * 1000:8.3f} ms | {ops_per_sec:10.1f} ops/s")
    return average


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Video Editing Suite")
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()
    runs = max(5, args.runs)

    print("=" * 80)
    print("AI CONTENT FACTORY - COMMERCIAL EDITING SUITE BENCHMARK")
    print(f"Iterations per test: {runs}")
    print("=" * 80)

    # 1. Timeline Non-Linear Operations (Premiere Pro / Final Cut Pro style)
    print("\n--- [1] Timeline Non-Linear Operations ---")
    vp_split = create_sample_project(10)
    bench(
        "Split Scene (slot recalculation & bisect)",
        lambda: split_scene(vp_split.model_copy(deep=True), "sc-5", 0.5),
        runs,
    )

    vp_dup = create_sample_project(10)
    bench(
        "Duplicate Scene (deep-copy & timeline splice)",
        lambda: duplicate_scene(vp_dup.model_copy(deep=True), "sc-3"),
        runs,
    )

    vp_move = create_sample_project(10)
    bench(
        "Move Scene (re-indexing & order shift)",
        lambda: move_scene(vp_move.model_copy(deep=True), "sc-8", 2),
        runs,
    )

    vp_merge = create_sample_project(10)
    bench(
        "Merge Scene (adjacent dialogue & duration join)",
        lambda: merge_scene(vp_merge.model_copy(deep=True), "sc-4"),
        runs,
    )

    vp_50 = create_sample_project(50)
    scene_ids_50 = [s.id for s in vp_50.scenes]
    bench(
        "Bulk Update Look (50 scenes, grades/effects)",
        lambda: bulk_update(
            vp_50.model_copy(deep=True),
            scene_ids_50,
            {"grade": ColorGrade.VINTAGE, "speed": 1.25},
        ),
        runs,
    )

    # 2. Keyframe Motion Math (After Effects style)
    print("\n--- [2] Keyframe Motion & Spatial Animation (After Effects) ---")
    scene_with_keys = VideoScene(
        id="sc-motion",
        label="Animated Drone Flyover",
        duration_seconds=5.0,
        text="Flyover shot",
        keyframes=[
            Keyframe(at=0.0, scale=1.0, rotation=0.0, pos_x=0.0, pos_y=0.0),
            Keyframe(at=0.3, scale=1.2, rotation=5.0, pos_x=15.0, pos_y=-10.0),
            Keyframe(at=0.7, scale=1.35, rotation=-3.0, pos_x=30.0, pos_y=5.0),
            Keyframe(at=1.0, scale=1.0, rotation=0.0, pos_x=0.0, pos_y=0.0),
        ],
    )

    def evaluate_1000_frames():
        for i in range(100):
            evaluate_motion(scene_with_keys, i / 100.0)

    bench(
        "Evaluate Motion Track (100 sample points, Bezier)",
        evaluate_1000_frames,
        runs,
    )

    # 3. Timeline QA Measurement & Render Compilation
    print("\n--- [3] Timeline QA & Render Plan Compilation ---")
    vp_qa = create_sample_project(25)
    bench(
        "Timeline Linting & WCAG Contrast Report (25 scenes)",
        lambda: report(vp_qa, target_seconds=125),
        runs,
    )

    bench(
        "Compile Render Plan (25 scenes, cues, audio mix)",
        lambda: compile_render_plan(vp_qa, project_id="bench-proj"),
        runs,
    )

    # 4. Procedural Graphics Generation (Map & Infographic)
    print("\n--- [4] Procedural Graphics Engine (SVG Rendering) ---")
    route_spec = MapRouteSpec(
        title="Titanic Final Voyage (April 1912)",
        map_type="nautical",
        points=[
            MapRoutePoint(label="Southampton", x=80.0, y=28.0, timestamp="10/04/1912"),
            MapRoutePoint(label="Cherbourg", x=76.0, y=34.0, timestamp="10/04/1912"),
            MapRoutePoint(label="Queenstown", x=70.0, y=26.0, timestamp="11/04/1912"),
            MapRoutePoint(
                label="Iceberg Collision",
                x=35.0,
                y=65.0,
                timestamp="14/04 23:40",
            ),
            MapRoutePoint(label="New York (Dest)", x=20.0, y=55.0),
        ],
        show_danger_zone=True,
        danger_label="Vị trí va chạm tảng băng",
        danger_x=35.0,
        danger_y=65.0,
    )
    bench(
        "Procedural Nautical Route Map (SVG generation)",
        lambda: generate_route_map_svg(route_spec),
        runs,
    )

    info_spec = InfographicSpec(
        title="Maritime Disaster Casualties Comparison",
        subtitle="So sánh số lượng thương vong các thảm họa hàng hải",
        labels=[
            "Wilhelm Gustloff (1945)",
            "Doña Paz (1987)",
            "Titanic (1912)",
            "Halifax Explosion (1917)",
        ],
        values=[9400.0, 4386.0, 1517.0, 1782.0],
        unit="người",
    )
    bench(
        "Comparative Infographic Bar Chart (SVG generation)",
        lambda: generate_infographic_svg(info_spec),
        runs,
    )

    # 5. Policy & Sensitive Content Analysis
    print("\n--- [5] Sensitivity Audit & Fact Reconciliation ---")
    test_script = (
        "[Hook]\nĐúng 23h40 ngày 14/4/1912, tàu Titanic va chạm tảng băng trôi.\n\n"
        "[Climax]\nNước tràn khoang kín, con tàu gãy đôi và chìm xuống biển sâu.\n"
        "Hơn 1.500 người đã thiệt mạng trong làn nước lạnh giá âm 2 độ C.\n\n"
        "[Analysis]\nBài học lớn nhất trong lịch sử an toàn hàng hải thế giới."
    )
    bench(
        "Sensitivity Audit (regex linter & scoring)",
        lambda: audit_sensitivity(test_script),
        runs,
    )

    claims = [
        FactClaim(
            claim_type="casualties",
            value="1517 người",
            sources=["US Senate Inquiry (1912)", "British Board of Trade (1912)"],
            discrepancy_notes="Đồng thuận cao giữa 2 cuộc điều tra chính thức.",
        ),
        FactClaim(
            claim_type="date",
            value="14/04/1912 - 15/04/1912",
            sources=["Maritime Historical Archives"],
            discrepancy_notes="Thời điểm xảy ra va chạm và chìm tàu.",
        ),
    ]
    bench(
        "Fact Reconciliation (multi-source consensus)",
        lambda: reconcile_facts(claims),
        runs,
    )

    # 6. Structured Timeline & History DB Queries
    print("\n--- [6] Structured Timeline & Historical Queries ---")
    bench(
        "Extract Structured Timeline from Script",
        lambda: extract_structured_timeline(test_script),
        runs,
    )

    bench(
        "Query 'On This Day' (April 14 events)",
        lambda: get_events_for_date(4, 14),
        runs,
    )

    bench(
        "Fuzzy Search Historical Database ('Titanic')",
        lambda: search_historical_events("Titanic"),
        runs,
    )

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
