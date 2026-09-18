"""On This Day (Lịch sử ngày này năm xưa) Engine.

Curated knowledge base of historical disasters, maritime accidents, aviation
mysteries, and technological catastrophes. Powers evergreen content ideation
and automated anniversary topic recommendation.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from .models import OnThisDayEvent

_HISTORICAL_EVENTS: tuple[OnThisDayEvent, ...] = (
    OnThisDayEvent(
        day=28,
        month=1,
        year=1986,
        title="Thảm họa tàu con thoi Challenger",
        category="aviation",
        summary=(
            "Tàu con thoi Challenger phát nổ chỉ 73 giây sau khi phóng "
            "từ Mũi Canaveral, khiến toàn bộ 7 phi hành gia thiệt mạng "
            "do lỗi vòng đệm O-ring trong thời tiết băng giá."
        ),
        casualties_estimate="7 phi hành gia",
        suggested_angle="73 giây định mệnh và lời cảnh báo bị NASA phớt lờ",
        keywords=[
            "challenger",
            "nasa",
            "space",
            "o-ring",
            "phi hành gia",
            "tàu con thoi",
        ],
    ),
    OnThisDayEvent(
        day=1,
        month=2,
        year=2003,
        title="Thảm họa tàu con thoi Columbia",
        category="aviation",
        summary=(
            "Tàu con thoi Columbia nát vụn khi tái nhập khí quyển Trái Đất "
            "do một miếng xốp cách nhiệt va vào cánh trái lúc cất cánh."
        ),
        casualties_estimate="7 phi hành gia",
        suggested_angle="Miếng xốp định mệnh rơi lúc cất cánh mà không ai sửa chữa",
        keywords=["columbia", "nasa", "khí quyển", "phi hành đoàn"],
    ),
    OnThisDayEvent(
        day=8,
        month=3,
        year=2014,
        title="Bí ẩn chuyến bay Malaysia Airlines MH370",
        category="aviation",
        summary=(
            "Chiếc Boeing 777 chở 239 người biến mất không dấu vết trên hành trình "
            "Kuala Lumpur - Bắc Kinh, trở thành bí ẩn hàng không lớn nhất thế kỷ 21."
        ),
        casualties_estimate="239 người mất tích",
        suggested_angle="37 phút im lặng và cú bẻ lái bất thường vào Ấn Độ Dương",
        keywords=["mh370", "malaysia airlines", "mất tích", "ấn độ dương", "radar"],
    ),
    OnThisDayEvent(
        day=27,
        month=3,
        year=1977,
        title="Thảm họa sân bay Tenerife (Hai chiếc Boeing 747 va chạm)",
        category="aviation",
        summary=(
            "Hai siêu máy bay Boeing 747 của KLM và Pan Am đâm vào nhau trên "
            "đường băng dày đặc sương mù tại Tenerife, cướp đi 583 sinh mạng."
        ),
        casualties_estimate="583 người thiệt mạng",
        suggested_angle="Sương mù mù mịt và câu nói định mệnh của cơ trưởng KLM",
        keywords=["tenerife", "klm", "pan am", "boeing 747", "va chạm", "sương mù"],
    ),
    OnThisDayEvent(
        day=14,
        month=4,
        year=1912,
        title="Vụ chìm tàu RMS Titanic",
        category="maritime",
        summary=(
            "Con tàu 'không thể chìm' Titanic va chạm tảng băng trôi lúc 23:40 "
            "và chìm xuống đáy Bắc Đại Tây Dương sau 2 giờ 40 phút."
        ),
        casualties_estimate="1,517 người thiệt mạng",
        suggested_angle="6 bức điện tín cảnh báo băng trôi bị bỏ quên trong túi áo",
        keywords=["titanic", "iceberg", "băng trôi", "bắc đại tây dương", "smith"],
    ),
    OnThisDayEvent(
        day=18,
        month=4,
        year=1906,
        title="Đại động đất và Hỏa hoạn San Francisco 1906",
        category="seismic",
        summary=(
            "Trận động đất mạnh 7.9 độ Richter phá hủy đứt gãy San Andreas "
            "gây ra hỏa hoạn thiêu rụi 80% thành phố San Francisco."
        ),
        casualties_estimate="Hơn 3,000 người thiệt mạng",
        suggested_angle=(
            "Khi ngọn lửa tàn phá San Francisco còn dữ dội hơn cơn động đất"
        ),
        keywords=["san francisco", "động đất", "richter", "san andreas", "hỏa hoạn"],
    ),
    OnThisDayEvent(
        day=26,
        month=4,
        year=1986,
        title="Thảm họa nhà máy hạt nhân Chornobyl",
        category="disaster",
        summary=(
            "Lò phản ứng số 4 phát nổ trong một bài thử nghiệm an toàn sai quy trình, "
            "phát tán lượng bụi phóng xạ gấp 400 lần bom Hiroshima."
        ),
        casualties_estimate="Hàng chục ngàn người phơi nhiễm",
        suggested_angle="Lò phản ứng số 4: 50 giây trước khi thế giới thay đổi mãi mãi",
        keywords=[
            "chornobyl",
            "chernobyl",
            "hạt nhân",
            "phóng xạ",
            "lò phản ứng",
            "pripyat",
        ],
    ),
    OnThisDayEvent(
        day=6,
        month=5,
        year=1937,
        title="Thảm họa khinh khí cầu LZ 129 Hindenburg",
        category="aviation",
        summary=(
            "Chiếc khinh khí cầu khổng lồ của Đức bốc cháy thành quả cầu lửa "
            "trong chưa đầy 34 giây khi đang neo đậu tại New Jersey."
        ),
        casualties_estimate="36 người thiệt mạng",
        suggested_angle="34 giây thiêu rụi biểu tượng kiêu hãnh của bầu trời nước Đức",
        keywords=["hindenburg", "khinh khí cầu", "zeppeline", "new jersey", "cháy"],
    ),
    OnThisDayEvent(
        day=30,
        month=6,
        year=1908,
        title="Sự kiện nổ thiên thạch Tunguska ở Siberia",
        category="disaster",
        summary=(
            "Vụ nổ trên không tương đương 15 megaton TNT san phẳng 80 triệu cây rừng "
            "trên diện tích 2,150 km² mà không để lại bất kỳ hố va chạm nào."
        ),
        casualties_estimate="Không ghi nhận thương vong trực tiếp",
        suggested_angle=(
            "Vụ nổ tương đương 1,000 quả bom nguyên tử không để lại dấu vết"
        ),
        keywords=["tunguska", "siberia", "thiên thạch", "nổ trên không", "vũ trụ"],
    ),
    OnThisDayEvent(
        day=12,
        month=8,
        year=2000,
        title="Thảm họa tàu ngầm hạt nhân Kursk K-141",
        category="maritime",
        summary=(
            "Vụ nổ ngư lôi thử nghiệm khiến tàu ngầm nguyên tử tối tân của Nga "
            "chìm sâu 108m dưới biển Barents, 23 thủy thủ sống sót trong khoang số 9."
        ),
        casualties_estimate="118 thủy thủ thiệt mạng",
        suggested_angle=(
            "23 người sống sót trong bóng tối khoang số 9 và bức thư vĩnh biệt"
        ),
        keywords=["kursk", "tàu ngầm", "biển barents", "k-141", "ngư lôi", "nga"],
    ),
    OnThisDayEvent(
        day=24,
        month=8,
        year=79,
        title="Núi lửa Vesuvius chôn vùi thành phố Pompeii",
        category="seismic",
        summary=(
            "Cột tro bụi khổng lồ cao 33km đổ sụp chôn vùi toàn bộ thành phố La Mã "
            "Pompeii "
            "và Herculaneum dưới lớp đá bọt dày hàng mét chỉ trong một đêm."
        ),
        casualties_estimate="Khoảng 15,000 - 20,000 người",
        suggested_angle="24 giờ cuối cùng của thành phố xa hoa bậc nhất Đế chế La Mã",
        keywords=["pompeii", "vesuvius", "núi lửa", "la mã", "tro bụi"],
    ),
    OnThisDayEvent(
        day=1,
        month=9,
        year=1923,
        title="Đại thảm họa động đất Kanto (Nhật Bản)",
        category="seismic",
        summary=(
            "Trận động đất 7.9 Richter xảy ra đúng giờ nấu trưa gây ra cơn lốc lửa "
            "thiêu rụi toàn bộ Tokyo và Yokohama trong sự hoảng loạn tột cùng."
        ),
        casualties_estimate="Hơn 142,000 người thiệt mạng",
        suggested_angle=(
            "Cơn lốc lửa hủy diệt nuốt chửng 38,000 người trong 15 phút tại Tokyo"
        ),
        keywords=["kanto", "động đất", "tokyo", "yokohama", "lốc lửa", "nhật bản"],
    ),
    OnThisDayEvent(
        day=6,
        month=12,
        year=1917,
        title="Đại vụ nổ cảng Halifax (Canada)",
        category="maritime",
        summary=(
            "Tàu chở thuốc nổ SS Mont-Blanc va chạm tàu SS Imo tại cảng Halifax "
            "tạo ra vụ nổ nhân tạo phi hạt nhân lớn nhất lịch sử loài người."
        ),
        casualties_estimate="Gần 2,000 người thiệt mạng",
        suggested_angle=(
            "Cú va chạm định mệnh tạo nên sóng thần và quả cầu lửa hủy diệt cảng"
        ),
        keywords=["halifax", "mont-blanc", "thuốc nổ", "vụ nổ", "canada"],
    ),
    OnThisDayEvent(
        day=26,
        month=12,
        year=2004,
        title="Đại thảm họa Sóng thần Ấn Độ Dương (Boxing Day)",
        category="seismic",
        summary=(
            "Trận siêu động đất 9.1 Richter ngoài khơi Sumatra giải phóng năng lượng "
            "khổng lồ, tạo ra những bức tường sóng thần cao 30m càn quét 14 quốc gia."
        ),
        casualties_estimate="Khoảng 227,898 người thiệt mạng",
        suggested_angle=(
            "Bức tường nước 30 mét ập đến khi cả bờ biển Ấn Độ Dương đang nghỉ lễ"
        ),
        keywords=[
            "sóng thần",
            "tsunami",
            "ấn độ dương",
            "sumatra",
            "indonesia",
            "boxing day",
        ],
    ),
)


def get_events_for_date(month: int, day: int) -> list[OnThisDayEvent]:
    """Retrieve historical disaster/accident events matching a specific date."""
    return [ev for ev in _HISTORICAL_EVENTS if ev.month == month and ev.day == day]


def get_events_for_today() -> list[OnThisDayEvent]:
    """Retrieve historical events matching today's calendar date."""
    now = datetime.datetime.now()
    matched = get_events_for_date(now.month, now.day)
    if not matched:
        # Fallback to closest notable historical milestones for evergreen ideation
        return list(_HISTORICAL_EVENTS[:3])
    return matched


def search_historical_events(query: str) -> list[OnThisDayEvent]:
    """Fuzzy search historical disasters by name, keyword, or category."""
    if not query:
        return list(_HISTORICAL_EVENTS)
    q = query.strip().lower()
    matched: list[OnThisDayEvent] = []
    for ev in _HISTORICAL_EVENTS:
        kw_str = " ".join(ev.keywords)
        text = f"{ev.title} {ev.summary} {kw_str} {ev.suggested_angle}".lower()
        if q in text:
            matched.append(ev)
    return matched


def list_all_events() -> Sequence[OnThisDayEvent]:
    """Return the entire dataset of curated events."""
    return _HISTORICAL_EVENTS
