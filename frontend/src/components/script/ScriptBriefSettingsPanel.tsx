"use client";

import React, { useState } from "react";
import { ScriptBriefSettings } from "@/types/studio";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  SlidersHorizontal,
  Upload,
  Link2,
  Youtube,
  FileText,
  Sparkles,
  RotateCcw,
  Save,
  Check,
  Video,
  FileSpreadsheet,
  AlertTriangle,
  Flame,
  Film,
  Target,
  Users,
  ShieldCheck,
  Ban,
  Globe,
  Loader2,
} from "lucide-react";

export const DEFAULT_BRIEF_SETTINGS: ScriptBriefSettings = {
  topic: "Mẹo nấu cơm không bị nhão cho người mới bắt đầu",
  uniqueAngle: "Không dùng đốt ngón tay đo nước như truyền thống, mà dùng tỷ lệ khối lượng nước chuẩn 1:1.15 và thêm 1 giọt dầu mè giúp hạt cơm tơi xốp bóng bẩy.",
  platform: "tiktok",
  targetDuration: "60s",
  aspectRatio: "9:16",
  audienceAgeGender: "Gen Z & người mới đi làm (18-28 tuổi), tự nấu ăn một mình",
  audienceKnowledge: "Đã biết cắm nồi cơm điện cơ bản nhưng thường xuyên bị thất bại",
  audiencePainPoint: "Nấu cơm hôm nhão như cháo, hôm sống sượng, rất ngại nấu ăn tại nhà",
  audienceDesire: "Nấu bát cơm dẻo thơm chuẩn nhà hàng Nhật, nhanh gọn không cần kinh nghiệm",
  videoGoal: "education",
  callToAction: "Thả tim và lưu ngay video này lại để bữa tối nay áp dụng thử ngay nhé!",
  tone: "casual",
  includeMemeSlang: true,
  slangKeywords: "chuẩn đét, bao ngon, siêu bánh cuốn, bí thuật",
  hookType: "counter_intuitive",
  structurePacing: "hook_body_climax_cta",
  includeVisualCues: true,
  formatType: "voiceover_broll",
  specificFactsAndData: "Tỷ lệ nước chuẩn: 1 chén gạo ST25 = 1.15 chén nước. Vo gạo tối đa 2 lần để không mất cám vitamin B1. Ngâm 10 phút trước khi bấm nút Cook.",
  referenceLinksAndDocs: "https://culinary-science.org/rice-water-ratio; Sách 'Khoa Học Nấu Ăn Trong Căn Bếp'",
  benchmarkCreatorOrChannel: "@KhoaiLangThang (thân thiện mộc mạc), @NinhTito (hình ảnh đồ ăn bắt mắt)",
  benchmarkScriptExample: "3 giây đầu cận cảnh thìa cơm tơi xốp bốc khói nghi ngút, giọng trầm ấm đặt câu hỏi gây tò mò.",
  benchmarkMediaUrl: "https://tiktok.com/@cooking_pro/video/123456789",
  negativeConstraints: "Không chê bai cách nấu truyền thống của phụ huynh, không dùng từ sáo rỗng 'Hôm nay mình sẽ hướng dẫn...', tránh quảng cáo nhãn hiệu gạo cụ thể.",
  forbiddenWords: "nhất thế giới, cam kết 100%, lừa đảo, chữa bách bệnh",
};

export const BRIEF_PRESETS: Array<{ id: string; label: string; brief: ScriptBriefSettings }> = [
  {
    id: "cooking-hack",
    label: "🍚 Mẹo Nấu Ăn Viral 60s",
    brief: DEFAULT_BRIEF_SETTINGS,
  },
  {
    id: "history-mystery",
    label: "✈️ Bí Ẩn Hàng Không 10m",
    brief: {
      topic: "Vì sao các chuyến bay thương mại không bao giờ bay thẳng qua Thái Bình Dương?",
      uniqueAngle: "Trái Đất hình cầu cong (Great Circle) khiến đường bay vòng lên cực Bắc ngắn hơn hàng ngàn dặm so với đường thẳng trên bản đồ phẳng 2D Mercator.",
      platform: "youtube_long",
      targetDuration: "10m",
      aspectRatio: "16:9",
      audienceAgeGender: "Khán giả tò mò khoa học, công nghệ, hàng không (20-45 tuổi)",
      audienceKnowledge: "Biết nhìn bản đồ phẳng và thắc mắc sao máy bay lại bay đường vòng kỳ lạ",
      audiencePainPoint: "Nhìn bản đồ phẳng thấy phi lý, dễ tin vào các thuyết âm mưu",
      audienceDesire: "Hiểu bản chất địa lý cầu, quy tắc cứu nạn ETOPS và an toàn bay quốc tế",
      videoGoal: "viral_debate",
      callToAction: "Đăng ký kênh và bấm chuông để khám phá những bí ẩn hàng không tiếp theo!",
      tone: "dramatic",
      includeMemeSlang: false,
      slangKeywords: "",
      hookType: "curiosity_gap",
      structurePacing: "hook_body_climax_cta",
      includeVisualCues: true,
      formatType: "cinematic_storytelling",
      specificFactsAndData: "Quy chuẩn ETOPS-180: máy bay 2 động cơ luôn phải cách sân bay dự phòng tối đa 180 phút bay. Khoảng cách đường cong trắc địa rút ngắn 2,400 km.",
      referenceLinksAndDocs: "Cục Hàng không Liên bang FAA Advisory Circular 120-42B; Bản đồ định vị FlightRadar24",
      benchmarkCreatorOrChannel: "Vox Borders, RealLifeLore, Kurzgesagt, Khám Phá Thế Giới",
      benchmarkScriptExample: "Mở đầu với hình ảnh radar máy bay rẽ ngoặt bất thường giữa biển, âm nhạc căng thẳng.",
      benchmarkMediaUrl: "https://youtube.com/watch?v=sample_aviation_route",
      negativeConstraints: "Không quy kết hãng bay lừa dối, không nhắc đến tai nạn máy bay cụ thể gây hoang mang, dùng thuật ngữ hàng không chính xác.",
      forbiddenWords: "tam giác quỷ, người ngoài hành tinh, bí mật bị che giấu",
    },
  },
  {
    id: "tech-review",
    label: "📱 Review Công Nghệ 60s",
    brief: {
      topic: "Đánh giá chi tiết pin và camera thực tế của siêu phẩm điện thoại mới sau 30 ngày",
      uniqueAngle: "Bỏ qua các thông số quảng cáo trên giấy, test thực tế độ tụt pin khi quay 4K ngoài trời nắng 38 độ C.",
      platform: "shorts",
      targetDuration: "60s",
      aspectRatio: "9:16",
      audienceAgeGender: "Yêu thích công nghệ, đang phân vân có nên nâng cấp máy (18-35 tuổi)",
      audienceKnowledge: "Đã xem quảng cáo giới thiệu của hãng nhưng chưa tin",
      audiencePainPoint: "Sợ tin vào reviewer nhận tiền quảng cáo, mua về dùng bị nóng máy tụt pin",
      audienceDesire: "Lời khuyên thật 100%, ưu nhược điểm rõ ràng trước khi chi 30 triệu",
      videoGoal: "conversion",
      callToAction: "Bình luận chiếc máy bạn đang dùng để mình làm bài so sánh tiếp theo nhé!",
      tone: "serious",
      includeMemeSlang: true,
      slangKeywords: "quá nhiệt, bóp hiệu năng, hẹo pin, đáng đồng tiền",
      hookType: "fatal_mistake",
      structurePacing: "problem_agitate_solution",
      includeVisualCues: true,
      formatType: "talking_head",
      specificFactsAndData: "Pin 5000mAh onscreen thực tế 5h42p khi bật 120Hz. Nhiệt độ mặt lưng đạt 43.5°C khi quay video liên tục 12 phút.",
      referenceLinksAndDocs: "Bảng đo Geekbench 6 & 3DMark Wildlife Extreme Stress Test",
      benchmarkCreatorOrChannel: "MKBHD, Duy Thẩm, Vật Vờ Studio",
      benchmarkScriptExample: "Cầm máy thật trên tay, zoom cận cảnh thông số nhiệt kế hồng ngoại.",
      benchmarkMediaUrl: "https://youtube.com/shorts/sample_tech_benchmark",
      negativeConstraints: "Không dìm hàng vô căn cứ, không dùng từ ngữ quảng cáo tài trợ một chiều, nêu đủ 2 điểm khen và 2 điểm chê.",
      forbiddenWords: "tuyệt phẩm hoàn hảo, không có đối thủ, mua ngay kẻo lỡ",
    },
  },
  {
    id: "finance-growth",
    label: "💰 Tài Chính Đầu Tư 3m",
    brief: {
      topic: "Quy tắc 3 hũ tiền giúp người trẻ tiết kiệm 100 triệu đầu tiên trong 12 tháng",
      uniqueAngle: "Không ép bản thân nhịn ăn nhịn uống kham khổ, mà tự động trích 20% thu nhập ngay khi nhận lương vào quỹ đầu tư thụ động.",
      platform: "tiktok",
      targetDuration: "3m",
      aspectRatio: "9:16",
      audienceAgeGender: "Nhân viên văn phòng 22-30 tuổi, thu nhập 10-25 triệu/tháng",
      audienceKnowledge: "Biết khái niệm tiết kiệm nhưng cuối tháng luôn thấy tài khoản về 0",
      audiencePainPoint: "Tiền lương trôi qua ngón tay, không biết tiền đi đâu, không có quỹ khẩn cấp",
      audienceDesire: "Có số tiền phòng thân vững chắc, tự tin đầu tư tích lũy an toàn",
      videoGoal: "education",
      callToAction: "Bình luận 'TÀI CHÍNH' để nhận bảng tính Excel tự động phân bổ thu nhập miễn phí nhé!",
      tone: "inspiring",
      includeMemeSlang: true,
      slangKeywords: "cháy túi, tài chính healthy, tự do tài chính, đầu tư kỷ luật",
      hookType: "curiosity_gap",
      structurePacing: "problem_agitate_solution",
      includeVisualCues: true,
      formatType: "talking_head",
      specificFactsAndData: "Công thức phân bổ: 50% nhu cầu thiết yếu, 30% sở thích linh hoạt, 20% tiết kiệm đầu tư. Lãi kép 8%/năm sau 10 năm tạo ra tài sản gấp đôi.",
      referenceLinksAndDocs: "Sách 'Người Giàu Có Nhất Thành Babylon'; Dữ liệu thống kê thu nhập bình quân Tổng cục Thống kê",
      benchmarkCreatorOrChannel: "An Is Here, Thái Phạm, Shark Thái Vân Linh",
      benchmarkScriptExample: "Mở đầu với hình ảnh tin nhắn biến động số dư ngân hàng và câu hỏi đánh trúng tâm lý.",
      benchmarkMediaUrl: "",
      negativeConstraints: "Không hô hào làm giàu nhanh, không lôi kéo đa cấp hoặc sàn tiền số mờ ám, giải thích thực tế.",
      forbiddenWords: "làm giàu không khó, cam kết x10 tài khoản, kiếm 100 triệu dễ dàng",
    },
  },
];

interface ScriptBriefSettingsPanelProps {
  brief: ScriptBriefSettings;
  onBriefChange: (brief: ScriptBriefSettings) => void;
  onGenerateScript: () => void;
  isProcessing?: boolean;
}

export function ScriptBriefSettingsPanel({
  brief,
  onBriefChange,
  onGenerateScript,
  isProcessing = false,
}: ScriptBriefSettingsPanelProps) {
  const [savedNotice, setSavedNotice] = useState(false);
  const [activeAccordion, setActiveAccordion] = useState<number | null>(null);

  const handleApplyPreset = (p: (typeof BRIEF_PRESETS)[0]) => {
    onBriefChange(p.brief);
  };

  /**
   * Note the picked dossier file in the brief.
   *
   * The file is **not** read and **not** uploaded — this panel only drafts text.
   * The handler used to announce "Đã nạp thành công dữ liệu từ file" and write
   * "Dữ liệu nghiên cứu thực tế đã được nạp" into the brief while doing neither;
   * the only thing it ever knew was the filename and the byte count. It now
   * records exactly that, and points at the route that does ingest for real.
   */
  const handleDossierFilePicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    onBriefChange({
      ...brief,
      specificFactsAndData:
        brief.specificFactsAndData +
        `\n[Tài liệu tham chiếu: ${file.name} (${(file.size / 1024).toFixed(1)} KB)] — mới chỉ ghi nhận tên file vào brief; nội dung chưa được đọc. Dán nội dung vào đây, hoặc nhập qua External Ingest (POST /projects/{id}/external/import) để AI dùng được.`,
    });
  };

  /**
   * Note the picked benchmark video in the brief.
   *
   * Nothing is transcribed here. The handler used to announce that Whisper was
   * analysing the video and then paste a *fabricated* extraction — "nhịp cắt
   * 1.2s, giọng đọc năng lượng cao" — for a file it had never opened. It now
   * records the filename and says the transcription has not run.
   */
  const handleBenchmarkVideoPicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    onBriefChange({
      ...brief,
      benchmarkScriptExample: `[Video tham chiếu: ${file.name}] — chưa bóc tách. Chạy phiên âm (STT) cho tư liệu này trong Media Library rồi dán kịch bản nhận được vào đây.`,
    });
  };

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto pr-1">
      {/* Top Presets Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-nle-panel border border-nle-border p-2.5 rounded-xl shrink-0">
        <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-none">
          <span className="text-[11px] text-gray-400 font-semibold shrink-0">Mẫu đề bài:</span>
          {BRIEF_PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleApplyPreset(p)}
              className="px-2.5 py-1 rounded-lg bg-nle-surface hover:bg-nle-border text-[11px] text-gray-300 hover:text-white border border-nle-border transition-colors shrink-0"
            >
              {p.label}
            </button>
          ))}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onBriefChange(DEFAULT_BRIEF_SETTINGS)}
          className="text-[11px] h-7 px-2 border-nle-border text-gray-400 hover:text-white shrink-0"
        >
          <RotateCcw className="w-3 h-3 mr-1" />
          Mặc định
        </Button>
      </div>

      {/* 10-Dimension Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* ========================================================================= */}
        {/* 1. CHỦ ĐỀ & GÓC NHÌN */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-nle-cyan/20 text-nle-cyan flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                01
              </div>
              <span>Chủ Đề & Góc Nhìn / Insight</span>
            </CardTitle>
            <Badge variant="cyan" className="text-[10px]">Cốt lõi</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Chủ đề cụ thể (không nói chung chung, ví dụ: "mẹo nấu cơm không bị nhão cho người mới"):
              </label>
              <input
                type="text"
                value={brief.topic}
                onChange={(e) => onBriefChange({ ...brief, topic: e.target.value })}
                placeholder="Nhập chủ đề cụ thể, rõ ràng..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Góc nhìn / Insight muốn khai thác (có gì mới, gây tranh cãi, hay bất ngờ không?):
              </label>
              <textarea
                rows={3}
                value={brief.uniqueAngle}
                onChange={(e) => onBriefChange({ ...brief, uniqueAngle: e.target.value })}
                placeholder="Góc nhìn mới mẻ, phản trực giác hoặc giải pháp độc lạ..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan resize-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 2. NỀN TẢNG & ĐỊNH DẠNG */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-amber-400/20 text-amber-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                02
              </div>
              <span>Nền Tảng, Thời Lượng & Tỷ Lệ Khung</span>
            </CardTitle>
            <Badge variant="amber" className="text-[10px]">Quy chuẩn</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2.5 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">Nền tảng xuất bản:</label>
              <div className="grid grid-cols-4 gap-1.5">
                {([
                  { id: "tiktok", label: "TikTok" },
                  { id: "shorts", label: "YT Shorts" },
                  { id: "reels", label: "Reels" },
                  { id: "youtube_long", label: "YouTube Dài" },
                ] as const).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, platform: item.id })}
                    className={`p-1.5 rounded text-center border transition-all text-xs font-medium ${
                      brief.platform === item.id
                        ? "bg-amber-400/20 border-amber-400 text-amber-300 font-bold"
                        : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                  Thời lượng mong muốn:
                </label>
                <div className="flex gap-1">
                  {["15s", "30s", "60s", "3m", "10m"].map((dur) => (
                    <button
                      key={dur}
                      type="button"
                      onClick={() => onBriefChange({ ...brief, targetDuration: dur })}
                      className={`flex-1 py-1 rounded text-center border text-[11px] ${
                        brief.targetDuration === dur
                          ? "bg-nle-cyan text-black font-bold border-nle-cyan"
                          : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                      }`}
                    >
                      {dur}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                  Tỷ lệ khung hình:
                </label>
                <div className="flex gap-1">
                  {([
                    { id: "9:16", label: "9:16 Dọc" },
                    { id: "16:9", label: "16:9 Ngang" },
                    { id: "1:1", label: "1:1" },
                  ] as const).map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => onBriefChange({ ...brief, aspectRatio: r.id })}
                      className={`flex-1 py-1 rounded text-center border text-[11px] ${
                        brief.aspectRatio === r.id
                          ? "bg-nle-cyan text-black font-bold border-nle-cyan"
                          : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 3. ĐỐI TƯỢNG KHÁN GIẢ */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-emerald-400/20 text-emerald-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                03
              </div>
              <span>Đối Tượng Khán Giả Mục Tiêu</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30">Persona</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Độ tuổi, giới tính, sở thích:
              </label>
              <input
                type="text"
                value={brief.audienceAgeGender}
                onChange={(e) => onBriefChange({ ...brief, audienceAgeGender: e.target.value })}
                placeholder="Ví dụ: Gen Z, người đi làm 18-28 tuổi, thích tự nấu ăn nhanh..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Họ đã biết gì rồi:
              </label>
              <input
                type="text"
                value={brief.audienceKnowledge}
                onChange={(e) => onBriefChange({ ...brief, audienceKnowledge: e.target.value })}
                placeholder="Ví dụ: Đã biết bấm nút nồi cơm cơ bản nhưng chưa biết tỷ lệ nước..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Nỗi đau / Vấn đề gặp phải:
                </label>
                <textarea
                  rows={2}
                  value={brief.audiencePainPoint}
                  onChange={(e) => onBriefChange({ ...brief, audiencePainPoint: e.target.value })}
                  placeholder="Họ đang bực bội, bất an vì điều gì..."
                  className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Khao khát / Mong muốn:
                </label>
                <textarea
                  rows={2}
                  value={brief.audienceDesire}
                  onChange={(e) => onBriefChange({ ...brief, audienceDesire: e.target.value })}
                  placeholder="Họ muốn đạt kết quả gì nhanh chóng..."
                  className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500 resize-none"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 4. MỤC TIÊU VIDEO & CTA */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-nle-violet/20 text-nle-violet flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                04
              </div>
              <span>Mục Tiêu Video & Kêu Gọi Hành Động (CTA)</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-nle-violet border-nle-violet/30">Chuyển đổi</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">Mục tiêu chính:</label>
              <div className="grid grid-cols-3 gap-1">
                {([
                  { id: "education", label: "Giáo dục / Mẹo" },
                  { id: "entertainment", label: "Giải trí" },
                  { id: "conversion", label: "Bán hàng / Review" },
                  { id: "follow", label: "Tăng Follow" },
                  { id: "viral_debate", label: "Viral / Tranh cãi" },
                ] as const).map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, videoGoal: g.id })}
                    className={`py-1 px-1 rounded text-center border text-[11px] font-medium truncate ${
                      brief.videoGoal === g.id
                        ? "bg-nle-violet/30 border-nle-violet text-white font-bold"
                        : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Hành động muốn người xem làm sau khi xem (like, mua hàng, follow, comment...):
              </label>
              <input
                type="text"
                value={brief.callToAction}
                onChange={(e) => onBriefChange({ ...brief, callToAction: e.target.value })}
                placeholder="Ví dụ: Lưu lại video, bình luận góc nhìn của bạn, bấm theo dõi..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 5. GIỌNG ĐIỆU & PHONG CÁCH */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-rose-400/20 text-rose-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                05
              </div>
              <span>Giọng Điệu, Phong Cách & Trend / Meme</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-rose-400 border-rose-500/30">Tone</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">Tông giọng:</label>
              <div className="grid grid-cols-3 gap-1">
                {([
                  { id: "casual", label: "Thân mật bạn bè" },
                  { id: "humorous", label: "Hài hước / Meme" },
                  { id: "serious", label: "Nghiêm túc / Uy tín" },
                  { id: "dramatic", label: "Kịch tính / Ly kỳ" },
                  { id: "inspiring", label: "Truyền cảm hứng" },
                  { id: "provocative", label: "Kích thích tranh luận" },
                ] as const).map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, tone: t.id })}
                    className={`py-1 rounded text-center border text-[11px] ${
                      brief.tone === t.id
                        ? "bg-rose-500/30 border-rose-400 text-white font-bold"
                        : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center space-x-2 pt-1">
              <input
                type="checkbox"
                id="meme-toggle"
                checked={brief.includeMemeSlang}
                onChange={(e) => onBriefChange({ ...brief, includeMemeSlang: e.target.checked })}
                className="rounded border-nle-border bg-nle-panel text-nle-cyan focus:ring-0 cursor-pointer"
              />
              <label htmlFor="meme-toggle" className="text-xs text-gray-300 cursor-pointer">
                Cho phép chèn trend, meme, tiếng lóng (Slang) giới trẻ
              </label>
            </div>
            {brief.includeMemeSlang && (
              <input
                type="text"
                value={brief.slangKeywords}
                onChange={(e) => onBriefChange({ ...brief, slangKeywords: e.target.value })}
                placeholder="Từ lóng gợi ý: chuẩn đét, bánh cuốn, bí thuật, đỉnh nóc..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            )}
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 6. CẤU TRÚC MONG MUỐN & VISUAL CUE */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-sky-400/20 text-sky-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                06
              </div>
              <span>Cấu Trúc Hook & Gợi Ý Hình Ảnh (Visual Cue)</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-sky-400 border-sky-500/30">Giữ chân 3s</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Hook mở đầu (3 giây đầu cực quan trọng trên TikTok):
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {([
                  { id: "counter_intuitive", label: "Phản trực giác / Ngược đời" },
                  { id: "fatal_mistake", label: "Sai lầm chết người" },
                  { id: "curiosity_gap", label: "Khoảng trống tò mò (Why?)" },
                  { id: "shocking_stat", label: "Số liệu gây sốc" },
                ] as const).map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, hookType: h.id })}
                    className={`p-1.5 rounded text-left border text-[11px] truncate ${
                      brief.hookType === h.id
                        ? "bg-sky-400/20 border-sky-400 text-sky-300 font-bold"
                        : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                    }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Cấu trúc phân đoạn:
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {([
                  { id: "hook_body_climax_cta", label: "Hook – Nội dung chính – Cao trào – CTA" },
                  { id: "problem_agitate_solution", label: "PAS: Vấn đề – Xoáy sâu – Giải pháp" },
                ] as const).map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, structurePacing: s.id })}
                    className={`p-1 rounded text-left border text-[10px] truncate ${
                      brief.structurePacing === s.id
                        ? "bg-sky-400/20 border-sky-400 text-sky-300 font-bold"
                        : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              <input
                type="checkbox"
                id="cue-toggle"
                checked={brief.includeVisualCues}
                onChange={(e) => onBriefChange({ ...brief, includeVisualCues: e.target.checked })}
                className="rounded border-nle-border bg-nle-panel text-nle-cyan focus:ring-0 cursor-pointer"
              />
              <label htmlFor="cue-toggle" className="text-xs text-gray-300 cursor-pointer">
                Kèm gợi ý hình ảnh/cảnh quay đi kèm lời thoại (kịch bản "voice + visual cue")
              </label>
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 7. NHÂN VẬT & HÌNH THỨC THỂ HIỆN */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-indigo-400/20 text-indigo-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                07
              </div>
              <span>Nhân Vật / Hình Thức Thể Hiện</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-indigo-400 border-indigo-500/30">Format</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-1.5">
              {([
                { id: "talking_head", label: "Một người nói trực diện camera (On-cam)" },
                { id: "voiceover_broll", label: "Voiceover + B-roll tư liệu" },
                { id: "two_person_dialogue", label: "Hội thoại 2 người (Podcast/Q&A)" },
                { id: "cinematic_storytelling", label: "Dạng storytelling / phim tài liệu" },
                { id: "pov_demo", label: "Góc nhìn thứ nhất (POV/Thực hành)" },
              ] as const).map((fmt) => (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => onBriefChange({ ...brief, formatType: fmt.id })}
                  className={`p-1.5 rounded text-left border text-[11px] truncate ${
                    brief.formatType === fmt.id
                      ? "bg-indigo-400/20 border-indigo-400 text-indigo-300 font-bold"
                      : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
                  }`}
                >
                  {fmt.label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 8. DỮ LIỆU CỤ THỂ (FILE PDF, WEB, YOUTUBE SCRIPT - TRÁNH AI BỊA) */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-emerald-400/20 text-emerald-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                08
              </div>
              <span>Dữ Liệu Cụ Thể (Tránh AI Bịa Đặt)</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30">Grounding</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Số liệu, tên sản phẩm, câu chuyện cá nhân, trích dẫn...:
              </label>
              <textarea
                rows={2}
                value={brief.specificFactsAndData}
                onChange={(e) => onBriefChange({ ...brief, specificFactsAndData: e.target.value })}
                placeholder="Nhập số liệu chính xác để AI không bịa..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500 resize-none font-mono"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Link trang web / YouTube script nguồn:
                </label>
                <div className="flex items-center space-x-1">
                  <input
                    type="text"
                    value={brief.referenceLinksAndDocs}
                    onChange={(e) => onBriefChange({ ...brief, referenceLinksAndDocs: e.target.value })}
                    placeholder="https://... hoặc script link"
                    className="flex-1 bg-nle-panel border border-nle-border rounded p-1 text-[11px] text-white"
                  />
                  <Globe className="w-3.5 h-3.5 text-nle-cyan shrink-0" />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Đính kèm file PDF / Word / Text:
                </label>
                <label className="flex items-center justify-center space-x-1 p-1 rounded bg-nle-panel border border-dashed border-nle-border hover:border-nle-cyan cursor-pointer text-gray-400 hover:text-white transition-colors">
                  <Upload className="w-3 h-3 text-nle-cyan" />
                  <span className="text-[11px]">Ghi tên file PDF/Doc vào brief...</span>
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt,.md"
                    onChange={handleDossierFilePicked}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 9. VÍ DỤ THAM KHẢO & VIDEO MẪU */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-fuchsia-400/20 text-fuchsia-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                09
              </div>
              <span>Ví Dụ Tham Khảo & Video Mẫu</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-fuchsia-400 border-fuchsia-500/30">Benchmark</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Kênh/video bạn thích phong cách để AI bắt chước tông giọng:
              </label>
              <input
                type="text"
                value={brief.benchmarkCreatorOrChannel}
                onChange={(e) => onBriefChange({ ...brief, benchmarkCreatorOrChannel: e.target.value })}
                placeholder="Ví dụ: Kênh @KhoaiLangThang, @NinhTito, @Vox, @MKBHD..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Link YouTube / TikTok mẫu để lấy script:
                </label>
                <div className="flex items-center space-x-1">
                  <input
                    type="text"
                    value={brief.benchmarkMediaUrl}
                    onChange={(e) => onBriefChange({ ...brief, benchmarkMediaUrl: e.target.value })}
                    placeholder="https://youtube.com/watch?v=..."
                    className="flex-1 bg-nle-panel border border-nle-border rounded p-1 text-[11px] text-white"
                  />
                  <Youtube className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                  Upload video tham khảo (bóc tách kịch bản):
                </label>
                <label className="flex items-center justify-center space-x-1 p-1 rounded bg-nle-panel border border-dashed border-nle-border hover:border-nle-cyan cursor-pointer text-gray-400 hover:text-white transition-colors">
                  <Video className="w-3 h-3 text-fuchsia-400" />
                  <span className="text-[11px]">Ghi tên video MP4 vào brief...</span>
                  <input
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    onChange={handleBenchmarkVideoPicked}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Đoạn script mẫu dán trực tiếp (để AI học nhịp câu):
              </label>
              <textarea
                rows={1}
                value={brief.benchmarkScriptExample}
                onChange={(e) => onBriefChange({ ...brief, benchmarkScriptExample: e.target.value })}
                placeholder="Dán đoạn văn mẫu yêu thích..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500 resize-none font-mono"
              />
            </div>
          </CardContent>
        </Card>

        {/* ========================================================================= */}
        {/* 10. ĐIỀU CẦN TRÁNH */}
        {/* ========================================================================= */}
        <Card className="border-nle-border bg-nle-surface/80 shadow-md">
          <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <div className="w-5 h-5 rounded bg-rose-500/20 text-rose-400 flex items-center justify-center mr-2 text-[11px] font-mono font-bold">
                10
              </div>
              <span>Điều Cần Tránh (Negative Constraints)</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] text-rose-400 border-rose-500/30">An toàn</Badge>
          </CardHeader>
          <CardContent className="p-3 space-y-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Không nhắc đối thủ, tránh sáo rỗng, tránh nội dung nhạy cảm:
              </label>
              <textarea
                rows={2}
                value={brief.negativeConstraints}
                onChange={(e) => onBriefChange({ ...brief, negativeConstraints: e.target.value })}
                placeholder="Không nhắc đối thủ A, không dùng câu sáo rỗng 'Chào mừng các bạn quay trở lại...'..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500 resize-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-0.5">
                Từ cấm / Không dùng từ ngữ nào đó:
              </label>
              <input
                type="text"
                value={brief.forbiddenWords}
                onChange={(e) => onBriefChange({ ...brief, forbiddenWords: e.target.value })}
                placeholder="Từ ngữ nhạy cảm cần tránh hoàn toàn..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Action Execution Bar */}
      <div className="bg-nle-panel border border-nle-border rounded-xl p-3 flex items-center justify-between shrink-0 shadow-lg mt-auto">
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSavedNotice(true);
              setTimeout(() => setSavedNotice(false), 2000);
            }}
            className="text-xs border-nle-border text-gray-300 hover:text-white h-8"
          >
            {savedNotice ? <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" /> : <Save className="w-3.5 h-3.5 mr-1 text-nle-cyan" />}
            {savedNotice ? "Đã lưu đề bài!" : "Lưu Đề Bài Mẫu"}
          </Button>
        </div>

        <Button
          variant="neon"
          size="default"
          onClick={onGenerateScript}
          disabled={isProcessing}
          className="px-5 font-bold text-xs h-9 shadow-lg shadow-nle-cyan/20"
        >
          {isProcessing ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-2" />
          )}
          🚀 AI Soạn Thảo Kịch Bản Chuẩn Từ 10 Tiêu Chí Này
        </Button>
      </div>
    </div>
  );
}
