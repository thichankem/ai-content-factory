"""Benchmark the AI Content Factory backend operations.

Measures the hot paths: scene parsing, video project build, research,
script generation (template provider), library indexing, and full-text
search. Prints a table of averages over ``N`` runs.

Usage:
    python scripts/benchmark.py [--runs N]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from content_factory.config import Settings  # noqa: E402
from content_factory.library import DocumentLibrary  # noqa: E402
from content_factory.models import ProjectCreate, VideoProject  # noqa: E402
from content_factory.scenes import build_video_project  # noqa: E402
from content_factory.service import ContentFactoryService  # noqa: E402

_SCRIPT = """
# Hook
This video reveals the secret.

# Evidence
Night footage proves the digital crime.

# Payoff
Subscribe for more tech mysteries.
"""

SCRIPT_6 = "\n".join(
    f"[{name}]\n" + " ".join([f"Sample sentence {i} about {name}." for i in range(4)])
    for name in ("Hook", "Context", "Evidence", "Turn", "Payoff", "CTA")
)

SCRIPT_30 = "\n".join(
    f"[Scene {i}]\n" + " ".join([f"Sentence {j} of scene {i}." for j in range(6)])
    for i in range(30)
)


def bench(label: str, fn, runs: int) -> float:
    samples: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    average = statistics.mean(samples)
    print(f"{label:<46} {average * 1000:9.2f} ms")
    return average


def make_service(tmp: Path) -> ContentFactoryService:
    settings = Settings(
        template_enabled=True,
        money_printer_enabled=False,
        strong_llm_enabled=False,
        documents_web_enabled=False,
        retry_max_attempts=1,
        retry_base_delay_seconds=0.0,
        retry_max_delay_seconds=0.0,
        retry_jitter_ratio=0.0,
        library_dir=str(tmp / "library"),
        library_db_path=str(tmp / "library" / ".index.db"),
    )
    return ContentFactoryService(settings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark backend operations")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    runs = max(1, args.runs)

    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(Path(tmp))
        project = service.create_project(
            ProjectCreate(
                name="Bench",
                topic="morning light circadian rhythm",
                duration_target_seconds=45,
            )
        )

        print(f"Benchmarking with {runs} runs each")
        print("-" * 60)
        bench(
            "build_video_project (6 scenes)",
            lambda: build_video_project(SCRIPT_6, 45, "vi"),
            runs,
        )
        bench(
            "build_video_project (30 scenes)",
            lambda: build_video_project(SCRIPT_30, 120, "vi"),
            runs,
        )
        bench(
            "service.create_project",
            lambda: service.create_project(
                ProjectCreate(name="X", topic="topic", duration_target_seconds=45)
            ),
            runs,
        )
        bench(
            "service.research (offline)",
            lambda: _run(service.research(project.id)),
            runs,
        )
        bench(
            "service.generate_script (template)",
            lambda: _run(service.generate_script(project.id)),
            runs,
        )
        bench(
            "tts.mp3_duration (mutagen)",
            lambda: _mp3_duration_sample(),
            runs,
        )
        bench(
            "smart.auto_fit_durations",
            lambda: _smart_auto_fit(),
            runs,
        )
        bench(
            "smart.beat_sync (120 bpm)",
            lambda: _smart_beat_sync(),
            runs,
        )
        bench(
            "smart.suggest_all",
            lambda: _smart_suggest(),
            runs,
        )
        bench(
            "smart.polish_text",
            lambda: _smart_polish(),
            runs,
        )

        style = service.presets.resolve("viral-short")
        bench(
            "script_engine.plan_script (6 sections)",
            lambda: _plan_script(style),
            runs,
        )
        bench(
            "script_engine.lint_script (30 scenes)",
            lambda: _lint_script(style),
            runs,
        )
        bench(
            "script_engine.copy_risk scan",
            lambda: _copy_risk_scan(style),
            runs,
        )
        bench(
            "agent_bridge.render_brief",
            lambda: _render_brief(project, style),
            runs,
        )
        bench(
            "timeline.report (6 scenes)",
            lambda: _timeline_report(),
            runs,
        )
        bench(
            "timeline.compile_render_plan",
            lambda: _timeline_plan(),
            runs,
        )
        bench(
            "workflow.normalize_workflow",
            lambda: _workflow_normalize(),
            runs,
        )
        bench(
            "workflow.checklist (9 blocks)",
            lambda: _workflow_checklist(),
            runs,
        )
        bench(
            "workflow.topological_order",
            lambda: _workflow_order(),
            runs,
        )

        library = DocumentLibrary(
            str(Path(tmp) / "lib"), str(Path(tmp) / "lib" / ".index.db")
        )
        pdf_path = _make_pdf(Path(tmp))
        bench("library.index_file (PDF)", lambda: library.index_file(pdf_path), runs)
        bench("library.search (BM25)", lambda: library.search("attention"), runs)
        bench("library.stats", lambda: library.stats(), runs)

        library.close()
        service._library.close()

        print("-" * 60)
        print("Done.")

    return 0


def _workflow_normalize():
    from content_factory import workflow

    return workflow.normalize_workflow(workflow.default_workflow())


def _workflow_checklist():
    from content_factory import workflow

    return workflow.checklist(workflow.default_workflow())


def _workflow_order():
    from content_factory import workflow

    return workflow.topological_order(workflow.default_workflow())


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def _mp3_duration_sample() -> float:
    from content_factory.tts import mp3_duration

    # A tiny valid MP3 header is enough for mutagen to parse a duration.
    return mp3_duration(b"\xff\xfb\x90\x64" + b"\x00" * 8192)


def _smart_project() -> VideoProject:
    from content_factory.scenes import build_video_project
    from content_factory.smart import apply_ai_assist

    project = build_video_project(_SCRIPT, 30, "en")
    apply_ai_assist(project, fit=True, beat=True, bpm=120)
    return project


def _smart_auto_fit() -> float:
    from content_factory.scenes import build_video_project
    from content_factory.smart import auto_fit_durations

    project = build_video_project(_SCRIPT, 30, "en")
    auto_fit_durations(project, target_total=30.0)
    return project.scenes[0].duration_seconds


def _smart_beat_sync() -> float:
    from content_factory.scenes import build_video_project
    from content_factory.smart import beat_sync

    project = build_video_project(_SCRIPT, 30, "en")
    beat_sync(project, 120)
    return project.scenes[0].duration_seconds


def _smart_suggest() -> str:
    from content_factory.smart import suggest_all

    scene = _smart_project().scenes[0]
    return suggest_all(scene)["filter"]


def _smart_polish() -> str:
    from content_factory.smart import polish_text

    return polish_text("this video reveals the secret")


def _plan_script(style) -> float:
    from content_factory.script_engine import plan_script

    return plan_script(
        SCRIPT_6, language="vi", target_seconds=45, style=style
    ).estimated_seconds


def _lint_script(style) -> int:
    """Lint the 30-scene script: the worst realistic case for the linter."""
    from content_factory.script_engine import lint_script

    return len(lint_script(SCRIPT_30, language="vi", style=style))


def _copy_risk_scan(style) -> int:
    from content_factory.models import ResearchBundle, ResearchSource
    from content_factory.script_engine import lint_script

    research = ResearchBundle(
        sources=[
            ResearchSource(
                id="bench",
                title="Bench source",
                url="https://example.test",
                source_type="article",
                summary=(
                    "Attention is a scarce resource and the first three seconds "
                    "decide whether a viewer stays or swipes away entirely."
                ),
                highlights=[
                    "Sudden movement or an unresolved image interrupts scrolling."
                ],
            )
        ]
    )
    return len(lint_script(SCRIPT_6, language="vi", style=style, research=research))


def _render_brief(project, style) -> int:
    from content_factory.agent_bridge import render_brief

    return len(render_brief(project, style=style))


def _timeline_report() -> int:
    from content_factory.scenes import build_video_project
    from content_factory.timeline import report

    cut = build_video_project(SCRIPT_6, 45, "en")
    return report(cut, target_seconds=45).score


def _timeline_plan() -> int:
    from content_factory.scenes import build_video_project
    from content_factory.timeline import compile_render_plan

    cut = build_video_project(SCRIPT_6, 45, "en")
    return len(compile_render_plan(cut, "bench").steps)


def _make_pdf(tmp: Path) -> Path:
    import pymupdf

    path = tmp / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Attention mechanisms in deep learning models.")
    doc.save(str(path))
    doc.close()
    return path


if __name__ == "__main__":
    sys.exit(main())
