"""Sensitivity and ethical policy linter for historical, disaster, and accident content.

Ensures scripts respect victims and families, avoid gratuitous gore, properly
label historical theories, and protect creator channels against YouTube
demonetization (yellow dollar) and TikTok algorithmic suppression.
"""

from __future__ import annotations

import re

from .models import (
    SensitivityAuditReport,
    SensitivityFinding,
    SensitivitySeverity,
)

# 1. Graphic violence patterns that trigger advertiser-unfriendly classification
_GRAPHIC_VIOLENCE_PATTERNS: tuple[tuple[re.Pattern, str, str], ...] = (
    (
        re.compile(
            r"(máu me|đẫm máu|kinh hoàng đẫm máu|xác người la liệt|xác chết|"
            r"ruột gan|đầu rơi|chặt đầu|xác chết biến dạng|nát bét)",
            re.IGNORECASE,
        ),
        "Mô tả bạo lực/thương tích quá chi tiết có thể bị YouTube hạn chế kiếm tiền.",
        "Thay bằng thuật ngữ tài liệu: 'thiệt hại nhân mạng', 'chấn thương nặng'.",
    ),
    (
        re.compile(
            r"\b(gory|mutilated|beheaded|dismembered|splattered blood|mangled body)\b",
            re.IGNORECASE,
        ),
        "Excessive graphic violence triggers platform demonetization.",
        "Use clinical terms: 'fatalities', 'severe casualties', 'loss of life'.",
    ),
)

# 2. Insensitive / Mocking phrases toward disaster victims
_DISRESPECT_PATTERNS: tuple[tuple[re.Pattern, str, str], ...] = (
    (
        re.compile(
            r"(đáng đời|chết cười|hài hước|ngu ngốc|trò hề|cho chừa)",
            re.IGNORECASE,
        ),
        "Ngôn từ có dấu hiệu thiếu tôn trọng nạn nhân hoặc giễu cợt thảm kịch.",
        "Giữ thái độ khách quan, trang nghiêm và tôn trọng sinh mạng con người.",
    ),
    (
        re.compile(
            r"\b(deserved it|hilarious death|stupid victims|darwin award)\b",
            re.IGNORECASE,
        ),
        "Disrespectful framing of deceased victims violates community guidelines.",
        "Frame objectively with historical empathy and dignified respect.",
    ),
)

# 3. Unverified speculation presented as hard fact
_UNVERIFIED_CONSPIRACY_PATTERNS: tuple[tuple[re.Pattern, str, str], ...] = (
    (
        re.compile(
            r"(chính phủ dàn dựng|chắc chắn bị ám sát|sự thật bị giấu kín|"
            r"chắc chắn rằng đây là âm mưu|âm mưu bị chính phủ che giấu|"
            r"bị chính phủ che giấu)",
            re.IGNORECASE,
        ),
        "Khẳng định thuyết âm mưu chưa kiểm chứng như một sự thật hiển nhiên.",
        "Gắn nhãn: 'Theo một số giả thuyết...', 'Dù chưa có bằng chứng...'",
    ),
    (
        re.compile(
            r"\b(100% inside job|aliens caused|undeniable government plot)\b",
            re.IGNORECASE,
        ),
        "Unproven conspiracy stated as factual certainty.",
        "Qualify: 'According to controversial theories...', 'Historians note...'",
    ),
)


def audit_sensitivity(
    text: str,
    topic: str = "",
    casualties: int | None = None,
) -> SensitivityAuditReport:
    """Audit a script or text for sensitive, graphic, or policy issues."""
    findings: list[SensitivityFinding] = []
    content = text or ""

    # Check graphic violence
    for pattern, msg, sugg in _GRAPHIC_VIOLENCE_PATTERNS:
        matches = pattern.finditer(content)
        for m in matches:
            findings.append(
                SensitivityFinding(
                    category="graphic_violence",
                    severity=SensitivitySeverity.CRITICAL,
                    snippet=m.group(0),
                    message=msg,
                    suggestion=sugg,
                )
            )

    # Check disrespect
    for pattern, msg, sugg in _DISRESPECT_PATTERNS:
        matches = pattern.finditer(content)
        for m in matches:
            findings.append(
                SensitivityFinding(
                    category="victim_respect",
                    severity=SensitivitySeverity.CRITICAL,
                    snippet=m.group(0),
                    message=msg,
                    suggestion=sugg,
                )
            )

    # Check unverified conspiracy
    for pattern, msg, sugg in _UNVERIFIED_CONSPIRACY_PATTERNS:
        matches = pattern.finditer(content)
        for m in matches:
            findings.append(
                SensitivityFinding(
                    category="unverified_conspiracy",
                    severity=SensitivitySeverity.WARNING,
                    snippet=m.group(0),
                    message=msg,
                    suggestion=sugg,
                )
            )

    # Calculate Monetization Safety Score (starts at 100)
    score = 100
    for f in findings:
        if f.severity == SensitivitySeverity.CRITICAL:
            score -= 25
        elif f.severity == SensitivitySeverity.WARNING:
            score -= 10
        else:
            score -= 5
    score = max(0, min(100, score))

    # Disclaimer recommendations for disasters with casualties
    is_disaster = any(
        k in (content + " " + topic).lower()
        for k in (
            "chìm",
            "tai nạn",
            "thảm họa",
            "sinking",
            "disaster",
            "crash",
            "earthquake",
            "động đất",
            "chết",
            "tử nạn",
        )
    )
    disclaimer_needed = is_disaster or (casualties is not None and casualties > 0)
    rec_disclaimer = None
    if disclaimer_needed:
        rec_disclaimer = (
            "⚠️ Video được thực hiện vì mục đích giáo dục lịch sử và tưởng niệm "
            "các nạn nhân. Mọi số liệu và diễn biến được tổng hợp từ các báo cáo "
            "điều tra chính thức."
        )

    return SensitivityAuditReport(
        safety_score=score,
        is_safe_for_monetization=score >= 70,
        findings=findings,
        disclaimer_required=disclaimer_needed,
        recommended_disclaimer=rec_disclaimer,
    )
