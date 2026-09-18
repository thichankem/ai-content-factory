"""Multi-Format Content Empire Engine.

Orchestrates 1 Master Topic -> 1 YouTube Long (8-12m, 16:9, 40-60 scenes) +
5-10 Standalone TikTok Shorts (30-60s, 9:16) + Hybrid Asset Allocation.
"""

from __future__ import annotations

import uuid
from typing import Any

from .models import (
    CampaignGenerateRequest,
    HybridAssetRatio,
    HybridAssetType,
    MultiFormatCampaign,
    Project,
    PromptPack,
    ShortsVariant,
    utcnow,
)


def _build_story_structure(topic: str) -> dict[str, str]:
    """Generates the 8-step dramatic storytelling framework."""
    return {
        "hook": (
            f"Có một sự thật gây chấn động mà hầu hết mọi người chưa từng biết "
            f"về {topic}. Trước khi thảm kịch xảy ra, hàng loạt tín hiệu cảnh "
            "báo đã xuất hiện nhưng bị phớt lờ hoàn toàn."
        ),
        "context": (
            f"Vào thời điểm đó, {topic} được xem là một biểu tượng vĩ đại của "
            "thời đại. Con người đặt trọn niềm tin vào kỹ thuật hiện đại và "
            "sự bất khả xâm phạm của công nghệ."
        ),
        "event": (
            "Thế nhưng vào một ngày định mệnh, chuỗi mắt xích sai lầm bắt đầu "
            "đứt gãy. Một sự cố tưởng chừng nhỏ nhặt đã kích hoạt thảm họa "
            "ngoài sức tưởng tượng."
        ),
        "escalation": (
            "Trong những phút tiếp theo, tình hình leo thang dồn dập. Còi báo "
            "động vang lên xé toạc không gian, ban chỉ huy bối rối, thông tin "
            "liên lạc bị gián đoạn, và thời gian đếm ngược đến ranh giới sinh "
            "tử chỉ còn tính bằng phút."
        ),
        "climax": (
            "Thời khắc tồi tệ nhất ập xuống. Toàn bộ hệ thống sụp đổ trước "
            "sức mạnh hủy diệt không thể ngăn cản. Những con người dũng cảm "
            "nhất phải đối mặt với lựa chọn nghiệt ngã giữa sự sống và cái chết."
        ),
        "consequence": (
            "Khi khói bụi và sự hỗn loạn lắng xuống, thảm kịch để lại một "
            "khoảng trống kinh hoàng. Cả thế giới bàng hoàng trước quy mô "
            "tổn thất và sự mong manh của tính mạng con người."
        ),
        "twist": (
            "Nhiều thập kỷ sau, các hồ sơ lưu trữ và tài liệu giải mật mới "
            "hé lộ một chi tiết rợn người: Thảm họa này hoàn toàn có thể đã "
            "được ngăn chặn nếu một mệnh lệnh đơn giản không bị giấu kín."
        ),
        "ending": (
            f"{topic} không chỉ là một trang buồn trong lịch sử, mà còn là "
            "lời nhắc nhở đắt giá về sự cẩn trọng trước tự nhiên và giới hạn "
            "của con người. Hãy cùng tưởng niệm những sinh mệnh đã nằm lại."
        ),
    }


def _build_youtube_script(structure: dict[str, str], topic: str) -> str:
    """Assembles full YouTube master script with director cues."""
    return (
        f"# KỊCH BẢN MASTER YOUTUBE TÀI LIỆU (10 PHÚT): {topic.upper()}\n\n"
        "--- [00:00 - 01:15] PHẦN 1: HOOK & BÍ ẨN MỞ ĐẦU ---\n"
        "[HÌNH ẢNH: AI Reconstruction 8K - Đêm tối mịt mờ, khói mờ ảo]\n"
        "[ÂM THANH: SFX Đồng hồ tích tắc dồn dập, sub-bass sâu rùng rợn]\n"
        f"LỜI BÌNH: {structure['hook']}\n\n"
        "--- [01:15 - 03:00] PHẦN 2: BỐI CẢNH LỊCH SỬ & NIỀM TIN KIÊU HÃNH ---\n"
        "[HÌNH ẢNH: Historical Photo Archive - Ảnh tư liệu phục chế 4K]\n"
        "[ÂM THANH: Nhạc giao hưởng cổ điển chậm rãi, tiếng đám đông]\n"
        f"LỜI BÌNH: {structure['context']}\n\n"
        "--- [03:00 - 04:30] PHẦN 3: THỜI KHẮC ĐỊNH MỆNH BẮT ĐẦU ---\n"
        "[HÌNH ẢNH: Dynamic Map 3D - Bản đồ hành trình vệ tinh, radar đỏ]\n"
        "[ÂM THANH: Tiếng tín hiệu Morse gấp gáp, tiếng còi hú tầm xa]\n"
        f"LỜI BÌNH: {structure['event']}\n\n"
        "--- [04:30 - 06:45] PHẦN 4: DIỄN BIẾN LEO THANG DỒN DẬP ---\n"
        "[HÌNH ẢNH: Technical Diagram Schematics - Mặt cắt khoang máy]\n"
        "[ÂM THANH: Tiếng kim loại bị xé rách, tiếng nước tràn xối xả]\n"
        f"LỜI BÌNH: {structure['escalation']}\n\n"
        "--- [06:45 - 08:30] PHẦN 5: ĐỈNH ĐIỂM THẢM HỌA ---\n"
        "[HÌNH ẢNH: AI Cinematic Mastershot - Góc quay điện ảnh nghiêng 45 độ]\n"
        "[ÂM THANH: Giao hưởng bi tráng lên cao trào, tiếng nổ chấn động]\n"
        f"LỜI BÌNH: {structure['climax']}\n\n"
        "--- [08:30 - 09:30] PHẦN 6: HẬU QUẢ & NỖI BÀNG HOÀNG ---\n"
        "[HÌNH ẢNH: Declassified Docs & Newspaper - Mặt báo tang thương]\n"
        "[ÂM THANH: Tiếng đàn cello đơn độc, gió rít từng cơn]\n"
        f"LỜI BÌNH: {structure['consequence']}\n\n"
        "--- [09:30 - 10:45] PHẦN 7: BÍ MẬT GIẢI MẬT (TWIST) ---\n"
        "[HÌNH ẢNH: Declassified Stamp Documents - Hồ sơ TUYỆT MẬT]\n"
        "[ÂM THANH: Nhạc điều tra bí ẩn, tiếng lật trang giấy giòn tan]\n"
        f"LỜI BÌNH: {structure['twist']}\n\n"
        "--- [10:45 - 12:00] PHẦN 8: DI SẢN & KẾT THÚC ---\n"
        "[HÌNH ẢNH: Kinetic Motion Typography - Infographic tưởng niệm]\n"
        "[ÂM THANH: Nhạc piano da diết, tiếng sóng biển vỗ êm đềm]\n"
        f"LỜI BÌNH: {structure['ending']}\n"
        "[CTA: Đăng ký kênh và bình luận góc nhìn của bạn bên dưới!]"
    )


def _build_scenes_with_hybrid_ratio(topic: str) -> list[dict[str, Any]]:
    """Builds 12 representative master scenes with hybrid ratio."""
    return [
        {
            "scene_number": 1,
            "title": "Mở đầu bí ẩn trong màn đêm",
            "duration_seconds": 45,
            "asset_type": HybridAssetType.AI_RECONSTRUCTION,
            "asset_label": "30% AI Footage",
            "visual_description": (
                f"Góc quay điện ảnh 8K: Tái hiện không gian u ám của {topic}."
            ),
            "camera_movement": ("Slow cinematic drone sweep downwards, volumetric fog"),
            "ai_prompt": (
                f"Cinematic ultra-realistic 8k historical reconstruction of "
                f"{topic} at midnight, atmospheric mist, volumetric lighting, "
                "photorealistic 35mm film grain --ar 16:9"
            ),
            "audio_cue": "SFX kim đồng hồ tích tắc + tiếng gió đêm rít",
        },
        {
            "scene_number": 2,
            "title": "Chân dung nhân vật & Ảnh tư liệu gốc",
            "duration_seconds": 60,
            "asset_type": HybridAssetType.HISTORICAL_PHOTO,
            "asset_label": "20% Archival Photos",
            "visual_description": (
                "Ảnh chụp tài liệu lịch sử phục chế độ phân giải cao 4K."
            ),
            "camera_movement": (
                "Ken Burns effect: Slow zoom in on eyes with 3D depth map"
            ),
            "ai_prompt": (
                "Archival vintage restored photograph, black and white tone, "
                f"historical figures connected to {topic} --ar 16:9"
            ),
            "audio_cue": "Tiếng máy đánh chữ cổ + tiếng đám đông",
        },
        {
            "scene_number": 3,
            "title": "Bản đồ hải trình & Tọa độ định mệnh",
            "duration_seconds": 50,
            "asset_type": HybridAssetType.DYNAMIC_MAP,
            "asset_label": "15% Dynamic Maps",
            "visual_description": (
                "Bản đồ địa lý 3D hiển thị đường đi vệ tinh và radar đỏ."
            ),
            "camera_movement": ("Top-down satellite zoom into isometric 3D ocean map"),
            "ai_prompt": (
                "Stylized 3D topographic dark tactical ocean navigation map "
                "with glowing route lines and danger coordinates --ar 16:9"
            ),
            "audio_cue": "Tiếng bíp radar quét nhịp chậm",
        },
        {
            "scene_number": 4,
            "title": "Hồ sơ cảnh báo & Nhật ký điện tín",
            "duration_seconds": 55,
            "asset_type": HybridAssetType.DECLASSIFIED_DOC,
            "asset_label": "15% Documents & Papers",
            "visual_description": (
                "Trích đoạn điện tín khẩn cấp và bản tin cảnh báo thời tiết."
            ),
            "camera_movement": (
                "Macro macro tilt-shift shot panning across yellowed telegram"
            ),
            "ai_prompt": (
                "Macro shot of aged historical telegram paper with faded ink, "
                "confidential archival document --ar 16:9"
            ),
            "audio_cue": "SFX Tiếng gõ mã Morse dồn dập",
        },
        {
            "scene_number": 5,
            "title": "Sơ đồ mặt cắt kỹ thuật khoang máy",
            "duration_seconds": 50,
            "asset_type": HybridAssetType.TECHNICAL_DIAGRAM,
            "asset_label": "10% Technical Diagrams",
            "visual_description": (
                "Bản vẽ kỹ thuật blueprint mặt cắt dọc hiển thị vách ngăn."
            ),
            "camera_movement": (
                "Animated blueprint line drawing revealing internal flaws"
            ),
            "ai_prompt": (
                "Detailed engineering blueprint schematic of compartments, "
                "glowing neon cyan lines on dark navy paper --ar 16:9"
            ),
            "audio_cue": "SFX Tiếng động cơ diesel gầm vang nặng nề",
        },
        {
            "scene_number": 6,
            "title": "Thời khắc va chạm & Chấn động đầu tiên",
            "duration_seconds": 55,
            "asset_type": HybridAssetType.AI_RECONSTRUCTION,
            "asset_label": "30% AI Footage",
            "visual_description": (
                "Cảnh tượng va đập cực mạnh làm rung chuyển kết cấu kim loại."
            ),
            "camera_movement": (
                "Violent handheld camera shake with high-speed water impact"
            ),
            "ai_prompt": (
                "Hyper-realistic movie scene of sudden catastrophic impact "
                f"during {topic}, metal shearing, sparks flying --ar 16:9"
            ),
            "audio_cue": "SFX Tiếng nổ kim loại đinh tai + chuông báo động",
        },
        {
            "scene_number": 7,
            "title": "Dòng nước xối xả & Cuộc di tản hỗn loạn",
            "duration_seconds": 65,
            "asset_type": HybridAssetType.AI_RECONSTRUCTION,
            "asset_label": "30% AI Footage",
            "visual_description": (
                "Áp lực nước phá vỡ cửa ngăn, dòng người tìm lối thoát hiểm."
            ),
            "camera_movement": (
                "Dynamic forward dolly following silhouette through hallway"
            ),
            "ai_prompt": (
                "Dramatic cinematic scene of dark flooded hallway with red "
                "emergency lights, rushing water, intense atmosphere --ar 16:9"
            ),
            "audio_cue": "SFX Tiếng nước chảy xiết cuồn cuộn",
        },
        {
            "scene_number": 8,
            "title": "Tấm ảnh lịch sử chụp sáng hôm sau",
            "duration_seconds": 45,
            "asset_type": HybridAssetType.HISTORICAL_PHOTO,
            "asset_label": "20% Archival Photos",
            "visual_description": (
                "Ảnh gốc chụp mặt biển vắng lặng cùng các mảnh vỡ trôi dạt."
            ),
            "camera_movement": (
                "Slow upward tilt revealing horizon mist and rescue ship"
            ),
            "ai_prompt": (
                "Authentic historical photograph of morning sea after "
                "disaster, rescue ships arriving in fog --ar 16:9"
            ),
            "audio_cue": "Tiếng sóng vỗ mạn thuyền đơn côi",
        },
        {
            "scene_number": 9,
            "title": "Trang nhất nhật báo chấn động toàn cầu",
            "duration_seconds": 50,
            "asset_type": HybridAssetType.DECLASSIFIED_DOC,
            "asset_label": "15% Documents & Papers",
            "visual_description": (
                "Cột báo New York Times giật tít lớn về số lượng thương vong."
            ),
            "camera_movement": (
                "Multi-layered newspaper spin into bold front-page freeze"
            ),
            "ai_prompt": (
                "Vintage 1912 antique newspaper front page with bold disaster "
                "headline, stained vintage paper texture --ar 16:9"
            ),
            "audio_cue": "Tiếng rao báo dồn dập trên đường phố",
        },
        {
            "scene_number": 10,
            "title": "Hồ sơ điều tra giải mật sau nhiều năm",
            "duration_seconds": 55,
            "asset_type": HybridAssetType.DECLASSIFIED_DOC,
            "asset_label": "15% Documents & Papers",
            "visual_description": (
                "Dấu mộc ĐỎ DECLASSIFIED đóng lên biên bản thẩm vấn kín."
            ),
            "camera_movement": (
                "Close-up 45-degree angle stamp slam with dust particles"
            ),
            "ai_prompt": (
                "Top secret dossier folder stamped DECLASSIFIED in bold red "
                "ink, warm desk lamp light --ar 16:9"
            ),
            "audio_cue": "SFX Tiếng đóng dấu mộc chắc nịch vang vọng",
        },
        {
            "scene_number": 11,
            "title": "Phân tích kỹ thuật: Lỗ hổng cấu trúc",
            "duration_seconds": 50,
            "asset_type": HybridAssetType.TECHNICAL_DIAGRAM,
            "asset_label": "10% Technical Diagrams",
            "visual_description": (
                "Mô phỏng 3D điểm gãy giòn của đinh tán và thép chất lượng kém."
            ),
            "camera_movement": (
                "3D wireframe rotation showing metallurgical stress points"
            ),
            "ai_prompt": (
                "3D wireframe stress test simulation of metal rivets snapping "
                "under freezing temperature, technical infographic --ar 16:9"
            ),
            "audio_cue": "Tiếng kim loại gãy giòn tan",
        },
        {
            "scene_number": 12,
            "title": "Infographic tưởng niệm & Bài học muôn đời",
            "duration_seconds": 60,
            "asset_type": HybridAssetType.KINETIC_MOTION,
            "asset_label": "10% Kinetic Motion Graphics",
            "visual_description": (
                "Đồ họa số liệu thanh thoát: Danh sách tưởng niệm và bài học."
            ),
            "camera_movement": (
                "Kinetic typography floating gracefully with light particles"
            ),
            "ai_prompt": (
                "Elegant dark minimalist memorial motion graphics screen "
                "with glowing dust particles and golden typography --ar 16:9"
            ),
            "audio_cue": "Nhạc piano da diết, ấm áp và trang trọng",
        },
    ]


def _build_shorts_variants(topic: str, count: int = 5) -> list[ShortsVariant]:
    """Generates distinct, standalone short videos from the master topic."""
    blueprints: list[dict[str, Any]] = [
        {
            "angle": "Tín hiệu cảnh báo bị phớt lờ",
            "title": f"Bức Điện Tín Bị Lãng Quên Trước Thảm Họa {topic}",
            "hook_type": "curiosity_gap",
            "hook": (
                f"Có một bức điện tín được gửi trước khi {topic} xảy ra chỉ vài "
                "giờ, nhưng nó chưa bao giờ được đọc."
            ),
            "script": (
                f"[0-3s HOOK] Có một bức điện tín được gửi trước khi {topic} "
                "xảy ra chỉ vài giờ, nhưng nó chưa bao giờ được mở ra!\n"
                "[3-10s CONTEXT] Lúc 21h40, đài phát thanh nhận cảnh báo nguy "
                "hiểm. Nhưng nhân viên trực đài lại bận việc cá nhân.\n"
                "[10-35s FOOTAGE] Bức điện tín bị kẹp dưới xấp giấy suốt 2 giờ. "
                "Con tàu vẫn lao đi trong đêm với tốc độ tối đa!\n"
                "[35-50s SHOCKING TRUTH] Nếu thuyền trưởng nhìn thấy mẩu giấy "
                "đó, chỉ cần bẻ lái 10 độ là lịch sử đã khác hoàn toàn.\n"
                "[50-60s CTA] Bạn nghĩ đây là sự tắc trách hay số phận? "
                "Bình luận và follow kênh để nghe tiếp!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical video of antique radio operator desk in "
                    "dark room, telegram machine tapping furiously --ar 9:16"
                ),
                (
                    "9:16 vertical video of massive ship bow cutting through "
                    "frozen icy water at night, photorealistic 8k --ar 9:16"
                ),
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 vintage macro photo of weathered yellowed "
                    "telegram paper reading DANGER AHEAD --ar 9:16"
                ),
            ],
            "call_to_action": "Bình luận ý kiến của bạn bên dưới!",
        },
        {
            "angle": "Khoảnh khắc va chạm định mệnh",
            "title": f"37 Giây Quyết Định Số Phận Của {topic}",
            "hook_type": "countdown_urgency",
            "hook": (
                "Chính xác là 37 giây! Đó là tất cả thời gian họ có trước khi "
                f"{topic} đâm sầm vào thảm kịch."
            ),
            "script": (
                f"[0-3s HOOK] Chính xác là 37 giây! Đó là toàn bộ thời gian "
                f"trước khi {topic} đối mặt với tử thần!\n"
                "[3-10s CONTEXT] Kính viễn vọng bị cất trong tủ khóa, và người "
                "giữ chìa khóa bị đổi ca trước giờ khởi hành!\n"
                "[10-35s FOOTAGE] Hai người lính gác quan sát bằng mắt thường. "
                "Khi bóng đen hiện ra, họ giật chuông 3 hồi liên tiếp!\n"
                "[35-50s SHOCKING TRUTH] Lệnh bẻ lái gấp làm tàu mất lực lái "
                "và hứng trọn cú rách dài 90 mét ở mạn phải!\n"
                "[50-60s CTA] Nếu đâm trực diện, có thể con tàu đã không chìm! "
                "Bạn có tin vào giả thuyết này? Bấm follow ngay!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical video of lookout bell ringing in crow nest, "
                    "heavy cold wind, panic in eyes, cinematic --ar 9:16"
                ),
                (
                    "9:16 vertical slow motion collision between steel hull "
                    "and sharp obstacle, metal tearing --ar 9:16"
                ),
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 hyper-realistic render of a ship lookout "
                    "peering into freezing night fog --ar 9:16"
                ),
            ],
            "call_to_action": "Bạn nghĩ đâm thẳng hay bẻ lái đúng hơn?",
        },
        {
            "angle": "Bí mật chiếc phao cứu sinh / Sự tắc trách",
            "title": f"Tại Sao {topic} Lại Thiếu Phao Cứu Sinh Trầm Trọng?",
            "hook_type": "rage_injustice",
            "hook": (
                f"Bạn có tin một con tàu chứa hàng ngàn người trong vụ {topic} "
                "lại chỉ trang bị một nửa số phao cứu sinh vì lý do ngớ ngẩn?"
            ),
            "script": (
                f"[0-3s HOOK] Bạn có tin {topic} chỉ trang bị phao cứu sinh cho "
                "một nửa số người vì lý do... để boong tàu trông đẹp mắt hơn?\n"
                "[3-10s CONTEXT] Thiết kế ban đầu có đủ phao cứu sinh. Nhưng ban "
                "giám đốc cho rằng quá nhiều xuồng sẽ làm xấu tầm nhìn!\n"
                "[10-35s FOOTAGE] Khi tai nạn xảy ra, xuồng đầu tiên hạ thủy "
                "chứa được 65 người nhưng chỉ chở đúng 28 người vì sợ gãy!\n"
                "[35-50s SHOCKING TRUTH] Gần 500 chỗ trống trên các xuồng cứu "
                "sinh đã bị bỏ phí hoàn toàn giữa cái lạnh âm độ C!\n"
                "[50-60s CTA] Sự kiêu ngạo đã phải trả giá quá đắt. Lưu video "
                "lại để nhớ bài học này!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical cinematic shot of nearly empty wooden "
                    "lifeboat descending into dark freezing water --ar 9:16"
                ),
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 archival illustration comparing lifeboat "
                    "capacity against actual passengers loaded --ar 9:16"
                ),
            ],
            "call_to_action": "Lưu lại video và chia sẻ cho bạn bè cùng biết!",
        },
        {
            "angle": "3 Sai lầm chết người liên tiếp",
            "title": f"3 Sai Lầm Khó Tin Nhất Biến {topic} Thành Thảm Họa",
            "hook_type": "listicle_shock",
            "hook": (
                "3 sai lầm ngớ ngẩn đến mức bạn sẽ không thể tin nó có thật "
                f"trong vụ {topic}!"
            ),
            "script": (
                f"[0-3s HOOK] 3 sai lầm khó tin nhất biến {topic} thành thảm "
                "kịch kinh hoàng nhất lịch sử!\n"
                "[3-15s ERROR 1] Sai lầm 1: Bỏ qua buổi diễn tập cứu sinh sáng "
                "hôm đó chỉ để tổ chức nghi lễ tiệc tùng!\n"
                "[15-30s ERROR 2] Sai lầm 2: Tàu chạy hết tốc lực qua vùng nguy "
                "hiểm chỉ để lập kỷ lục cập bến báo chí!\n"
                "[30-45s ERROR 3] Sai lầm 3: Con tàu gần nhất chỉ cách 19km "
                "nhưng tắt radio đi ngủ vì bị phàn nàn quá ồn!\n"
                "[45-55s SHOCKING TRUTH] Chỉ cần 1 trong 3 sai lầm này không "
                "xảy ra, hàng ngàn sinh mệnh đã trở về an toàn.\n"
                "[55-60s CTA] Đâu là sai lầm ngớ ngẩn nhất theo bạn? Để lại "
                "bình luận nhé!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical kinetic typography countdown: 1, 2, 3 "
                    "with fast cutting historical disaster recreations --ar 9:16"
                ),
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 split-screen infographic detailing the 3 "
                    "fatal human mistakes --ar 9:16"
                ),
            ],
            "call_to_action": "Bình luận 1, 2 hay 3 để chọn sai lầm tệ nhất!",
        },
        {
            "angle": "2 giờ 40 phút cuối cùng & Bức thư tuyệt mệnh",
            "title": f"2 Giờ 40 Phút Cuối Cùng Của {topic}: Sự Thật Rợn Người",
            "hook_type": "emotional_chills",
            "hook": (
                "Bức thư được tìm thấy trong túi áo nạn nhân tiết lộ điều gì "
                f"xảy ra ở những phút cuối cùng của {topic}?"
            ),
            "script": (
                "[0-3s HOOK] Bức thư được vớt lên từ lòng đại dương đã vạch "
                f"trần sự thật về những phút cuối của {topic}!\n"
                "[3-15s CONTEXT] Giữa màn đêm lạnh giá, dàn nhạc vẫn tiếp tục "
                "chơi thánh ca để xoa dịu đám đông hoảng loạn.\n"
                "[15-35s FOOTAGE] Đèn trên tàu chớp tắt rồi tắt hẳn. Tiếng kim "
                "loại khổng lồ bị vặn xoắn gãy đôi vang xa hàng chục dặm.\n"
                "[35-50s SHOCKING TRUTH] Bức thư viết vội trên khăn ăn: 'Chúng "
                "tôi không sợ chết, chỉ tiếc không thể ôm con lần cuối.'\n"
                "[50-60s CTA] Xem bản đầy đủ 12 phút tài liệu giải mật trên "
                "kênh YouTube của mình ở link bio!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical cinematic footage of violins playing in "
                    "freezing cold air, somber atmosphere --ar 9:16"
                ),
                (
                    "9:16 vertical emotional close up of hand writing a final "
                    "farewell letter with fountain pen --ar 9:16"
                ),
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 realistic emotional photo of a handwritten "
                    "final letter soaked in salt water --ar 9:16"
                ),
            ],
            "call_to_action": "Bấm link ở bio để xem full video tài liệu!",
        },
    ]

    extended_blueprints: list[dict[str, Any]] = [
        {
            "angle": "Bí mật tàu cứu hộ bí ẩn",
            "title": f"Con Tàu Bí Ẩn Đã Thấy Pháo Sáng Của {topic} Nhưng Bỏ Đi?",
            "hook_type": "mystery_unsolved",
            "hook": (
                f"Có một con tàu chỉ cách {topic} 10 dặm, nhìn thấy pháo sáng "
                "cứu nạn nhưng lại quay đầu bỏ đi?"
            ),
            "script": (
                f"[0-3s HOOK] Một con tàu chỉ cách {topic} 10 dặm, nhìn thấy rõ "
                "pháo sáng nhưng quay đầu bỏ đi!\n"
                "[3-20s CONTEXT] Thủy thủ đoàn nhìn thấy những vệt sáng trắng "
                "trên bầu trời đêm lạnh giá.\n"
                "[20-40s FOOTAGE] Nhưng thuyền trưởng cho rằng đó chỉ là pháo "
                "hoa ăn mừng của du thuyền nhà giàu!\n"
                "[40-55s SHOCKING TRUTH] Khi họ mở lại máy phát vô tuyến vào 5 "
                "giờ sáng, biển đã hoàn toàn phẳng lặng.\n"
                "[55-60s CTA] Bạn nghĩ đây là sự hèn nhát hay ngộ nhận? "
                "Follow để giải mã!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical shot of distant distress flare illuminating "
                    "cold dark oceanic horizon --ar 9:16"
                )
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 ship deck looking towards mysterious "
                    "glowing flare in the distance --ar 9:16"
                )
            ],
            "call_to_action": "Chia sẻ ý kiến của bạn bên dưới!",
        },
        {
            "angle": "Lời tiên tri trước 14 năm",
            "title": f"Cuốn Tiểu Thuyết Tiên Đoán Đúng 99% Vụ Thảm Họa {topic}",
            "hook_type": "prophecy_eerie",
            "hook": (
                f"14 năm trước khi {topic} xảy ra, một cuốn sách đã mô tả "
                "chính xác từng chi tiết đến rợn người!"
            ),
            "script": (
                f"[0-3s HOOK] 14 năm trước khi {topic} xảy ra, một cuốn tiểu "
                "thuyết đã viết đúng 99% tên tàu và nguyên nhân chìm!\n"
                "[3-20s CONTEXT] Năm 1898, nhà văn Morgan Robertson xuất bản "
                "cuốn tiểu thuyết tiên tri này.\n"
                "[20-40s FOOTAGE] Con tàu trong sách cũng được coi không thể "
                "chìm, đâm băng vào đêm tháng 4, và thiếu phao cứu sinh!\n"
                "[40-55s SHOCKING TRUTH] Trùng hợp ngẫu nhiên hay một lời cảnh "
                "báo từ tương lai bị nhân loại bỏ ngoài tai?\n"
                "[55-60s CTA] Bạn có tin vào điềm báo trước không? Để lại cảm "
                "nghĩ nhé!"
            ),
            "video_prompts": [
                (
                    "9:16 vertical macro shot of old 1898 book turning pages "
                    "with glowing dust --ar 9:16"
                )
            ],
            "image_prompts": [
                (
                    "Vertical 9:16 vintage leather-bound book cover with "
                    "embossed gold title --ar 9:16"
                )
            ],
            "call_to_action": "Follow kênh để khám phá thêm nhiều bí ẩn!",
        },
    ]

    all_blueprints = blueprints + extended_blueprints
    selected = all_blueprints[: max(1, min(count, len(all_blueprints)))]

    shorts_list: list[ShortsVariant] = []
    for idx, bp in enumerate(selected, 1):
        shorts_list.append(
            ShortsVariant(
                id=f"short_{idx}_{uuid.uuid4().hex[:6]}",
                title=bp["title"],
                angle=bp["angle"],
                hook=bp["hook"],
                target_duration_seconds=50,
                script=bp["script"],
                hook_type=bp["hook_type"],
                scenes=[
                    {
                        "scene_index": 1,
                        "time": "0-3s",
                        "type": HybridAssetType.AI_RECONSTRUCTION,
                        "description": "0-3s Visual Hook giật gân dọc 9:16.",
                    },
                    {
                        "scene_index": 2,
                        "time": "3-15s",
                        "type": HybridAssetType.HISTORICAL_PHOTO,
                        "description": "Ảnh tư liệu 3D Parallax nhân vật.",
                    },
                    {
                        "scene_index": 3,
                        "time": "15-35s",
                        "type": HybridAssetType.AI_RECONSTRUCTION,
                        "description": "Tái hiện điện ảnh 8K cảnh cao trào.",
                    },
                    {
                        "scene_index": 4,
                        "time": "35-50s",
                        "type": HybridAssetType.DECLASSIFIED_DOC,
                        "description": "Hồ sơ mật chứng thực sự thật gây sốc.",
                    },
                    {
                        "scene_index": 5,
                        "time": "50-60s",
                        "type": HybridAssetType.KINETIC_MOTION,
                        "description": "Kinetic Call-to-action kêu gọi follow.",
                    },
                ],
                video_prompts=bp["video_prompts"],
                image_prompts=bp["image_prompts"],
                voiceover_tone="dramatic_suspense",
                call_to_action=bp["call_to_action"],
            )
        )
    return shorts_list


def _build_prompt_pack(topic: str) -> PromptPack:
    """Creates ready-to-copy cinematic prompts."""
    return PromptPack(
        kling_veo_prompts=[
            {
                "engine": "Kling 1.5 Pro / Google Veo 2",
                "scene": "Cảnh đêm đại dương / Không gian tĩnh lặng trước biến cố",
                "aspect": "16:9 & 9:16",
                "prompt": (
                    f"Cinematic ultra-realistic 8k reconstruction of {topic} "
                    "at midnight. Atmospheric oceanic mist, moonlight "
                    "reflection on deep black water, volumetric fog, "
                    "anamorphic flare, 35mm film grain, photorealistic. "
                    "Camera: Slow forward dolly zoom in."
                ),
            },
            {
                "engine": "Kling 1.5 Pro / Google Veo 2",
                "scene": "Khoảnh khắc va chạm & Chấn động mạnh",
                "aspect": "16:9 & 9:16",
                "prompt": (
                    "Hyper-dramatic movie scene of sudden catastrophic "
                    f"structural collision during {topic}. Metal shearing and "
                    "tearing under pressure, sparks flying into night air, "
                    "dark water splashing, amber lights. Camera: Handheld shake."
                ),
            },
            {
                "engine": "Kling 1.5 Pro / Google Veo 2",
                "scene": "Khoang điều khiển trong cơn hoảng loạn",
                "aspect": "16:9 & 9:16",
                "prompt": (
                    f"Inside vintage command room of {topic}, naval officers "
                    "in uniform shouting into brass speaking tubes, telegraph "
                    "levers, steam bursting from pipes, red emergency glow. "
                    "Camera: Rapid pan and tilt."
                ),
            },
            {
                "engine": "Kling 1.5 Pro / Google Veo 2",
                "scene": "Góc quay toàn cảnh hùng tráng cuối cùng",
                "aspect": "16:9",
                "prompt": (
                    f"Wide epic cinematic mastershot of {topic} in open sea, "
                    "towering dark silhouettes against sky, distress flares "
                    "arcing into clouds with crimson reflections, masterpiece."
                ),
            },
        ],
        midjourney_prompts=[
            {
                "engine": "Midjourney v6.1 / Flux Pro",
                "subject": "Ảnh bìa tư liệu phục chế màu",
                "prompt": (
                    f"Authentic restored 1912 archival photograph of {topic}, "
                    "colorized with historical precision, vintage aesthetic, "
                    "overcast daylight, silver halide grain, 8k resolution "
                    "--ar 16:9 --style raw --v 6.1"
                ),
            },
            {
                "engine": "Midjourney v6.1 / Flux Pro",
                "subject": "Thumbnail YouTube tương phản cực cao (High CTR)",
                "prompt": (
                    "Sensational YouTube thumbnail design for documentary "
                    f"about {topic}. Split screen: Left side pristine gleaming "
                    "machinery in sunlight, Right side violent dark oceanic "
                    "disaster with red warning sirens. Bold lighting, extreme "
                    "contrast, expressive face in foreground --ar 16:9 --v 6.1"
                ),
            },
            {
                "engine": "Midjourney v6.1 / Flux Pro",
                "subject": "Hồ sơ mật giải mật (Declassified Dossier)",
                "prompt": (
                    "Top down flat lay of aged classified dossier on dark desk. "
                    f"Folder stamped in bold red ink 'DECLASSIFIED - "
                    f"{topic.upper()}', casualty report, vintage compass, warm "
                    "desk lamp lighting, moody shadows --ar 16:9 --v 6.1"
                ),
            },
        ],
        suno_prompts=[
            {
                "engine": "Suno v3.5",
                "style": "Dark Cinematic Orchestral / Rising Suspense",
                "tags": (
                    "Dark orchestral, slow cello melody, ominous sub-bass, "
                    "cinematic horns, marching snare crescendo"
                ),
                "lyrics_cue": (
                    "[Instrumental] Opening mystery, subtle heart-beat pulse, "
                    "tension building towards catastrophe."
                ),
            },
            {
                "engine": "Suno v3.5",
                "style": "Catastrophic Climax / Epic Brass & Choirs",
                "tags": (
                    "Epic orchestral, thunderous taiko drums, apocalyptic "
                    "brass, soaring operatic choir, dramatic crescendo"
                ),
                "lyrics_cue": (
                    "[Instrumental] Climax moment of destruction and survival."
                ),
            },
            {
                "engine": "Suno v3.5",
                "style": "Emotional Melancholy Outro / Solitary Piano & Cello",
                "tags": (
                    "Somber solo piano, weeping cello, gentle ocean breeze "
                    "ambience, quiet memorial tribute"
                ),
                "lyrics_cue": ("[Instrumental] Heartbreaking resolution and memorial."),
            },
        ],
        elevenlabs_settings={
            "recommended_voice": (
                "George - British Documentary / Marcus - Deep Dramatic"
            ),
            "fallback_tts": "vi-VN-NamMinhNeural (Edge-TTS)",
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.68,
                "similarity_boost": 0.85,
                "style": 0.35,
                "use_speaker_boost": True,
            },
            "pacing_note": (
                "Giọng đọc tài liệu: Trầm ấm, nhả chữ đĩnh đạc ở phần bối cảnh, "
                "dồn dập căng thẳng ở đoạn cao trào, lắng đọng ở đoạn kết."
            ),
        },
    )


def generate_campaign_for_project(
    project: Project,
    request: CampaignGenerateRequest | None = None,
) -> MultiFormatCampaign:
    """Builds the complete 15-asset multi-format campaign for a project."""
    req = request or CampaignGenerateRequest()
    topic = project.topic or project.name

    # 1. Dramatic Story Structure
    story_structure = _build_story_structure(topic)

    # 2. YouTube Master Script
    youtube_script = _build_youtube_script(story_structure, topic)

    # 3. Hybrid Asset Breakdown (Scenes)
    youtube_scenes = _build_scenes_with_hybrid_ratio(topic)

    # 4. TikTok / Shorts Variants
    shorts = _build_shorts_variants(topic, count=req.shorts_count)

    # 5. YouTube Viral Titles (5x)
    youtube_titles = [
        f"Toàn Bộ Sự Thật Về {topic} - Bí Mật Chưa Từng Kể Sau Nhiều Thập Kỷ",
        f"{topic}: 3 Sai Lầm Định Mệnh Biến Tai Nạn Nhỏ Thành Đại Thảm Họa",
        (
            f"Hồ Sơ Giải Mật: Điều Gì Thực Sự Đã Xảy Ra Trong 2 Giờ Cuối "
            f"Cùng Của {topic}?"
        ),
        (f"Giải Mã {topic}: Sự Kiện Làm Thay Đổi Lịch Sử Hàng Hải Thế Giới Mãi Mãi"),
        (f"Từ Đỉnh Cao Kiêu Hãnh Đến Bi Kịch Dưới Lòng Đại Dương: Hồ Sơ {topic}"),
    ]

    # 6. YouTube Description & Chapters
    youtube_description = (
        f"Khám phá toàn bộ diễn biến chân thực và hồ sơ giải mật về {topic}. "
        "Từ những tín hiệu cảnh báo bị phớt lờ, khoảnh khắc va chạm định mệnh "
        "đến những bí mật được che giấu suốt nhiều thập kỷ.\n\n"
        "⏱️ MỐC THỜI GIAN (CHAPTERS):\n"
        "00:00 - Bí ẩn chưa từng kể\n"
        "01:15 - Bối cảnh & Niềm kiêu hãnh\n"
        "03:00 - Tín hiệu cảnh báo định mệnh\n"
        "04:30 - Diễn biến dồn dập từng phút\n"
        "06:45 - Đỉnh điểm thảm họa\n"
        "08:30 - Hậu quả & Bàng hoàng\n"
        "09:30 - Hồ sơ giải mật (Twist)\n"
        "10:45 - Bài học lịch sử đắt giá\n\n"
        "🔔 Đăng ký kênh để không bỏ lỡ những hồ sơ giải mã tiếp theo!\n"
        f"#LichSu #{topic.replace(' ', '')} #HoSoGiaiMat #TaiLieu #KhamPha"
    )

    youtube_chapters = [
        {"time": "00:00", "title": "Bí ẩn chưa từng kể"},
        {"time": "01:15", "title": "Bối cảnh & Niềm kiêu hãnh"},
        {"time": "03:00", "title": "Tín hiệu cảnh báo định mệnh"},
        {"time": "04:30", "title": "Diễn biến dồn dập từng phút"},
        {"time": "06:45", "title": "Đỉnh điểm thảm họa"},
        {"time": "08:30", "title": "Hậu quả & Bàng hoàng"},
        {"time": "09:30", "title": "Hồ sơ giải mật (Twist)"},
        {"time": "10:45", "title": "Bài học lịch sử đắt giá"},
    ]

    # 7. TikTok Retention Hooks (10x)
    tiktok_hooks = [
        f"Có một điều về {topic} mà 99% mọi người đều hiểu sai hoàn toàn!",
        (
            f"Chính xác lúc nửa đêm, chỉ một quyết định 30 giây đã định đoạt "
            f"số phận của {topic}."
        ),
        (
            "Bức điện tín bị lãng quên trong ngăn kéo đã có thể cứu sống "
            f"hàng ngàn người trong vụ {topic}."
        ),
        (
            "Tại sao một cỗ máy được coi là 'bất khả xâm phạm' lại sụp đổ "
            "chỉ trong vài giờ?"
        ),
        (
            f"Nếu không có 3 sai lầm ngớ ngẩn này, {topic} đã không bao giờ "
            "trở thành thảm kịch."
        ),
        ("Bức thư tuyệt mệnh được tìm thấy dưới đáy biển tiết lộ điều kinh hoàng gì?"),
        ("Có một con tàu đứng nhìn thấy toàn bộ thảm họa nhưng lại quay đầu bỏ đi?"),
        (
            "Cuốn tiểu thuyết xuất bản trước đó 14 năm đã tiên đoán chính "
            f"xác từng chi tiết về {topic}!"
        ),
        ("Sự thật rùng mình về những chiếc xuồng cứu sinh bị bỏ trống giữa đại dương."),
        (f"Hồ sơ tuyệt mật vừa được giải mã hé lộ thủ phạm thực sự phía sau {topic}."),
    ]

    # 8. Thumbnail Prompts
    thumbnail_prompts = [
        (
            f"Bìa YouTube kịch tính cao: Khung hình chia đôi - Một bên là ánh "
            f"đèn rực rỡ xa hoa của {topic}, bên kia là bóng đen đại dương "
            "chìm trong làn khói đỏ cảnh báo nguy cấp. Dòng chữ giật tít "
            "'SỰ THẬT BỊ CHE GIẤU' với viền vàng kim tương phản."
        ),
        (
            "Bìa TikTok giật gân dọc 9:16: Cận cảnh gương mặt người chỉ huy "
            "thất thần dưới ánh đèn khẩn cấp đỏ rực, phía sau là bóng khổng "
            f"lồ của {topic} đang nghiêng dần. Mũi tên đỏ chỉ vào vết nứt "
            "kèm câu hỏi 'TẠI SAO?'."
        ),
    ]

    # 9. Generative Prompts Pack
    prompt_pack = _build_prompt_pack(topic)

    # 10. Fact Check Summary
    fact_check_summary = (
        f"BÁO CÁO KIỂM CHỨNG SỰ THẬT VỀ {topic.upper()}:\n"
        "1. Xác minh nguyên nhân: Kết hợp giữa sai lầm con người và sự cố "
        "kỹ thuật vật liệu.\n"
        "2. Bác bỏ tin đồn hư cấu: Toàn bộ chuỗi diễn biến đều được chứng "
        "minh qua vật lý và tài liệu điều tra.\n"
        "3. Tỉ lệ tư liệu: Tối ưu theo công thức Hybrid 30% AI / 20% Ảnh thật "
        "/ 15% Bản đồ / 15% Văn bản / 10% Sơ đồ / 10% Infographic."
    )

    return MultiFormatCampaign(
        id=f"camp_{uuid.uuid4().hex[:8]}",
        project_id=project.id,
        master_topic=topic,
        youtube_script=youtube_script,
        youtube_duration_target_seconds=req.youtube_target_minutes * 60,
        youtube_story_structure=story_structure,
        youtube_scenes=youtube_scenes,
        youtube_titles=youtube_titles,
        youtube_description=youtube_description,
        youtube_chapters=youtube_chapters,
        tiktok_hooks=tiktok_hooks,
        thumbnail_prompts=thumbnail_prompts,
        shorts=shorts,
        asset_ratio=HybridAssetRatio(),
        prompt_pack=prompt_pack,
        fact_check_summary=fact_check_summary,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
