"""Show what the SEO scorer actually says, so the numbers can be judged."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from content_factory.seo import Pack, optimize_pack, score_pack  # noqa: E402

bad = Pack(title="video", description="x")
print(
    "weak pack    :",
    score_pack(bad, "youtube").score,
    score_pack(bad, "tiktok").score,
)

good = Pack(
    title="Tàu Titanic: 5 quyết định khiến nó chìm trong 2 giờ 40 phút",
    description=(
        "Phân tích đầy đủ về thảm hoạ Titanic: thiết kế, cảnh báo bị bỏ qua, "
        "và vì sao 1.500 người không thể thoát. " + "Chi tiết từng mốc thời gian. " * 25
    ),
    tags=tuple(f"tag{i}" for i in range(10)),
    hashtags=("#titanic", "#lichsu", "#khampha"),
    keywords=("tàu titanic chìm", "thảm hoạ titanic"),
    script=(
        "[Hook] Con tàu được cho là không thể chìm.\n"
        "\n[Body] Một tiếng sau nó ở dưới đáy biển."
    ),
    hook="Con tàu được cho là không thể chìm.",
    duration_seconds=600.0,
    aspect_ratio="16:9",
    thumbnail_present=True,
    on_screen_text=("Titanic", "1912", "1.500 người"),
    has_captions=True,
    has_chapters=True,
    chapter_count=5,
    has_end_screen=True,
    playlist="Lịch sử hàng hải",
    sound="background music",
    beat_synced=True,
    bpm=100,
    cuts_per_minute=12.0,
    text_in_safe_zone=True,
    publish_hour=20,
    audience_hours=(19, 20, 21),
    watermark=False,
    comment_prompt=True,
    series_part=1,
    channel="Kenh Su",
    language="vi",
)

report = score_pack(good, "youtube")
print("strong pack  :", report.score, report.grade, "|", report.verdict)
print("  blocking   :", [signal.id for signal in report.blocking])
print("  quick wins :", [(win.signal_id, win.points) for win in report.quick_wins[:5]])
print("  confidence :", report.confidence)
short = score_pack(good, "tiktok")
print("same, tiktok :", short.score, short.grade)
print(
    "  failures   :",
    [signal.id for signal in short.signals if signal.status == "fail"][:6],
)

plan = optimize_pack(bad, "youtube")
print("optimize weak:", plan.before.score, "->", plan.after.score, "gain", plan.gain)
