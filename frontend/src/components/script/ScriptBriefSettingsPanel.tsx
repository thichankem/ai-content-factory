"use client";

import React, { useState } from "react";
import { ScriptBriefSettings, AttachedFile, AttachedWebPage } from "@/types/studio";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
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
  Globe,
  Loader2,
  Trash2,
  Plus,
  ExternalLink,
} from "lucide-react";

export const DEFAULT_BRIEF_SETTINGS: ScriptBriefSettings = {
  topic: "Mẹo nấu cơm không bị nhão cho người mới bắt đầu",
  uniqueAngle:
    "Không dùng đốt ngón tay đo nước như truyền thống, mà dùng tỷ lệ khối lượng nước chuẩn 1:1.15 và thêm 1 giọt dầu mè giúp hạt cơm tơi xốp bóng bẩy.",
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
  specificFactsAndData:
    "Tỷ lệ nước chuẩn: 1 chén gạo ST25 = 1.15 chén nước. Vo gạo tối đa 2 lần để không mất cám vitamin B1. Ngâm 10 phút trước khi bấm nút Cook.",
  referenceLinksAndDocs: "https://culinary-science.org/rice-water-ratio; Sách 'Khoa Học Nấu Ăn Trong Căn Bếp'",
  attachedFiles: [
    { id: "f-init-1", name: "Cong-thuc-ti-le-nuoc-ST25.pdf", size: 348160, type: "pdf" },
  ],
  attachedPages: [
    { id: "p-init-1", url: "https://culinary-science.org/rice-water-ratio", note: "Nghiên cứu tỷ lệ nước chuẩn" },
  ],
  benchmarkCreatorOrChannel: "@KhoaiLangThang (thân thiện mộc mạc), @NinhTito (hình ảnh đồ ăn bắt mắt)",
  benchmarkScriptExample:
    "3 giây đầu cận cảnh thìa cơm tơi xốp bốc khói nghi ngút, giọng trầm ấm đặt câu hỏi gây tò mò.",
  benchmarkMediaUrl: "https://tiktok.com/@cooking_pro/video/123456789",
  negativeConstraints:
    "Không chê bai cách nấu truyền thống của phụ huynh, không dùng từ sáo rỗng 'Hôm nay mình sẽ hướng dẫn...', tránh quảng cáo nhãn hiệu gạo cụ thể.",
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
      uniqueAngle:
        "Trái Đất hình cầu cong (Great Circle) khiến đường bay vòng lên cực Bắc ngắn hơn hàng ngàn dặm so với đường thẳng trên bản đồ phẳng 2D Mercator.",
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
      specificFactsAndData:
        "Quy chuẩn ETOPS-180: máy bay 2 động cơ luôn phải cách sân bay dự phòng tối đa 180 phút bay. Khoảng cách đường cong trắc địa rút ngắn 2,400 km.",
      referenceLinksAndDocs: "Cục Hàng không Liên bang FAA Advisory Circular 120-42B; Bản đồ định vị FlightRadar24",
      attachedFiles: [
        { id: "f-faa-doc", name: "FAA-Advisory-Circular-120-42B.pdf", size: 1048576, type: "pdf" },
      ],
      attachedPages: [
        { id: "p-flight-radar", url: "https://www.flightradar24.com/data/flights/pacific-routes", note: "Bản đồ luồng bay thực tế" },
      ],
      benchmarkCreatorOrChannel: "Vox Borders, RealLifeLore, Kurzgesagt, Khám Phá Thế Giới",
      benchmarkScriptExample:
        "Mở đầu với hình ảnh radar máy bay rẽ ngoặt bất thường giữa biển, âm nhạc căng thẳng.",
      benchmarkMediaUrl: "https://youtube.com/watch?v=sample_aviation_route",
      negativeConstraints:
        "Không quy kết hãng bay lừa dối, không nhắc đến tai nạn máy bay cụ thể gây hoang mang, dùng thuật ngữ hàng không chính xác.",
      forbiddenWords: "tam giác quỷ, người ngoài hành tinh, bí mật bị che giấu",
    },
  },
  {
    id: "tech-review",
    label: "📱 Review Công Nghệ 60s",
    brief: {
      topic: "Đánh giá chi tiết pin và camera thực tế của siêu phẩm điện thoại mới sau 30 ngày",
      uniqueAngle:
        "Bỏ qua các thông số quảng cáo trên giấy, test thực tế độ tụt pin khi quay 4K ngoài trời nắng 38 độ C.",
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
      specificFactsAndData:
        "Pin 5000mAh onscreen thực tế 5h42p khi bật 120Hz. Nhiệt độ mặt lưng đạt 43.5°C khi quay video liên tục 12 phút.",
      referenceLinksAndDocs: "Bảng đo Geekbench 6 & 3DMark Wildlife Extreme Stress Test",
      attachedFiles: [
        { id: "f-geekbench", name: "Stress-Test-Benchmark-Data.xlsx", size: 524288, type: "xlsx" },
      ],
      attachedPages: [
        { id: "p-gsmarena", url: "https://www.gsmarena.com/battery-test-v2.php3", note: "Bảng xếp hạng pin GSM" },
      ],
      benchmarkCreatorOrChannel: "MKBHD, Duy Thẩm, Vật Vờ Studio",
      benchmarkScriptExample: "Cầm máy thật trên tay, zoom cận cảnh thông số nhiệt kế hồng ngoại.",
      benchmarkMediaUrl: "https://youtube.com/shorts/sample_tech_benchmark",
      negativeConstraints:
        "Không dìm hàng vô căn cứ, không dùng từ ngữ quảng cáo tài trợ một chiều, nêu đủ 2 điểm khen và 2 điểm chê.",
      forbiddenWords: "tuyệt phẩm hoàn hảo, không có đối thủ, mua ngay kẻo lỡ",
    },
  },
  {
    id: "finance-growth",
    label: "💰 Tài Chính Đầu Tư 3m",
    brief: {
      topic: "Quy tắc 3 hũ tiền giúp người trẻ tiết kiệm 100 triệu đầu tiên trong 12 tháng",
      uniqueAngle:
        "Không ép bản thân nhịn ăn nhịn uống kham khổ, mà tự động trích 20% thu nhập ngay khi nhận lương vào quỹ đầu tư thụ động.",
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
      specificFactsAndData:
        "Công thức phân bổ: 50% nhu cầu thiết yếu, 30% sở thích linh hoạt, 20% tiết kiệm đầu tư. Lãi kép 8%/năm sau 10 năm tạo ra tài sản gấp đôi.",
      referenceLinksAndDocs: "Sách 'Người Giàu Có Nhất Thành Babylon'; Dữ liệu thống kê thu nhập bình quân Tổng cục Thống kê",
      attachedFiles: [
        { id: "f-budget", name: "Bang-tinh-thu-nhap-3-hu-tien.xlsx", size: 214000, type: "xlsx" },
      ],
      attachedPages: [
        { id: "p-gso", url: "https://www.gso.gov.vn/khao-sat-muc-song-dan-cu", note: "Thống kê mức sống GSO" },
      ],
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
  const [newPageUrl, setNewPageUrl] = useState("");
  const [newPageNote, setNewPageNote] = useState("");

  const handleApplyPreset = (p: (typeof BRIEF_PRESETS)[0]) => {
    onBriefChange(p.brief);
  };

  // Multiple File Upload Handler
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const currentFiles = brief.attachedFiles || [];
    const newAdded: AttachedFile[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split(".").pop()?.toLowerCase() || "file";
      newAdded.push({
        id: `f-${Date.now()}-${i}`,
        name: file.name,
        size: file.size,
        type: ext,
      });
    }

    onBriefChange({
      ...brief,
      attachedFiles: [...currentFiles, ...newAdded],
    });
    e.target.value = "";
  };

  const handleRemoveFile = (fileId: string) => {
    const currentFiles = brief.attachedFiles || [];
    onBriefChange({
      ...brief,
      attachedFiles: currentFiles.filter((f) => f.id !== fileId),
    });
  };

  // Multiple Web Page Add Handler
  const handleAddWebPage = () => {
    if (!newPageUrl.trim()) return;
    const currentPages = brief.attachedPages || [];
    onBriefChange({
      ...brief,
      attachedPages: [
        ...currentPages,
        {
          id: `p-${Date.now()}`,
          url: newPageUrl.trim(),
          note: newPageNote.trim() || undefined,
        },
      ],
    });
    setNewPageUrl("");
    setNewPageNote("");
  };

  const handleRemoveWebPage = (pageId: string) => {
    const currentPages = brief.attachedPages || [];
    onBriefChange({
      ...brief,
      attachedPages: currentPages.filter((p) => p.id !== pageId),
    });
  };

  // Video Reference upload simulation
  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      onBriefChange({
        ...brief,
        benchmarkScriptExample: `[Trích xuất từ video: ${file.name}] Cấu trúc nhịp cắt 1.5s, voiceover dồn dập, b-roll minh họa chân thực.`,
      });
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 overflow-y-auto px-2 py-1 pr-3 scrollbar-thin scrollbar-thumb-nle-border">
      {/* 1 CỘT DUY NHẤT TOÀN DIỆN - KHÔNG CHIA 2 CỘT */}
      <div className="flex flex-col space-y-4 max-w-4xl mx-auto w-full pb-10">
        {/* TOP PRESETS & RESET BAR */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 bg-nle-panel border border-nle-border p-3 rounded-xl shadow-sm">
          <div className="flex items-center space-x-2 overflow-x-auto scrollbar-none">
            <span className="text-xs text-gray-300 font-semibold shrink-0">🎯 Mẫu đề bài sẵn:</span>
            {BRIEF_PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => handleApplyPreset(p)}
                className="px-3 py-1.5 rounded-lg bg-nle-surface hover:bg-nle-border text-xs text-gray-200 hover:text-white border border-nle-border transition-colors shrink-0 font-medium"
              >
                {p.label}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onBriefChange(DEFAULT_BRIEF_SETTINGS)}
            className="text-xs h-8 px-3 border-nle-border text-gray-400 hover:text-white shrink-0"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Khôi phục mặc định
          </Button>
        </div>

        {/* 1. CHỦ ĐỀ & GÓC NHÌN */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-nle-cyan/20 text-nle-cyan flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                01
              </div>
              <span>Chủ Đề & Góc Nhìn / Insight</span>
            </CardTitle>
            <Badge variant="cyan" className="text-xs font-medium">Cốt lõi nội dung</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Chủ đề cụ thể <span className="text-gray-400 font-normal">(không nói chung chung, ví dụ: "mẹo nấu cơm không bị nhão cho người mới"):</span>
              </label>
              <input
                type="text"
                value={brief.topic}
                onChange={(e) => onBriefChange({ ...brief, topic: e.target.value })}
                placeholder="Nhập chủ đề cụ thể, rõ ràng, có điểm neo ngữ cảnh..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Góc nhìn / Insight muốn khai thác <span className="text-gray-400 font-normal">(có gì mới, gây tranh cãi, hay bất ngờ không?):</span>
              </label>
              <textarea
                rows={3}
                value={brief.uniqueAngle}
                onChange={(e) => onBriefChange({ ...brief, uniqueAngle: e.target.value })}
                placeholder="Góc nhìn mới mẻ, phản trực giác hoặc giải pháp độc lạ mà khán giả chưa từng nghĩ tới..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan resize-none leading-relaxed"
              />
            </div>
          </CardContent>
        </Card>

        {/* 2. NỀN TẢNG & ĐỊNH DẠNG */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-amber-400/20 text-amber-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                02
              </div>
              <span>Nền Tảng, Thời Lượng & Tỷ Lệ Khung Hình</span>
            </CardTitle>
            <Badge variant="amber" className="text-xs font-medium">Quy chuẩn kỹ thuật</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-2">Nền tảng xuất bản:</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: "tiktok", label: "🎵 TikTok (Dọc)" },
                  { id: "shorts", label: "🔴 YouTube Shorts" },
                  { id: "reels", label: "📸 Facebook / IG Reels" },
                  { id: "youtube_long", label: "🎬 YouTube Dài (Ngang)" },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, platform: item.id as any })}
                    className={`py-2 px-3 rounded-lg text-center border transition-all text-xs font-medium ${
                      brief.platform === item.id
                        ? "bg-amber-400/20 border-amber-400 text-amber-300 font-bold shadow-sm"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-200 mb-2">
                  Thời lượng mong muốn:
                </label>
                <div className="flex gap-1.5">
                  {["15s", "30s", "60s", "3m", "10m"].map((dur) => (
                    <button
                      key={dur}
                      type="button"
                      onClick={() => onBriefChange({ ...brief, targetDuration: dur })}
                      className={`flex-1 py-1.5 rounded-lg text-center border text-xs font-medium transition-colors ${
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
                <label className="block text-xs font-semibold text-gray-200 mb-2">
                  Tỷ lệ khung hình minh họa:
                </label>
                <div className="flex gap-1.5">
                  {[
                    { id: "9:16", label: "9:16 Dọc" },
                    { id: "16:9", label: "16:9 Ngang" },
                    { id: "1:1", label: "1:1 Vuông" },
                  ].map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => onBriefChange({ ...brief, aspectRatio: r.id as any })}
                      className={`flex-1 py-1.5 rounded-lg text-center border text-xs font-medium transition-colors ${
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

        {/* 3. ĐỐI TƯỢNG KHÁN GIẢ */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-emerald-400/20 text-emerald-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                03
              </div>
              <span>Đối Tượng Khán Giả Mục Tiêu (Persona)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-emerald-400 border-emerald-500/30">Chân dung người xem</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Độ tuổi, giới tính, sở thích:
              </label>
              <input
                type="text"
                value={brief.audienceAgeGender}
                onChange={(e) => onBriefChange({ ...brief, audienceAgeGender: e.target.value })}
                placeholder="Ví dụ: Gen Z & người mới đi làm 18-28 tuổi, sống một mình, thích nấu ăn nhanh..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Họ đã biết gì rồi <span className="text-gray-400 font-normal">(để tránh nói lại kiến thức hiển nhiên):</span>
              </label>
              <input
                type="text"
                value={brief.audienceKnowledge}
                onChange={(e) => onBriefChange({ ...brief, audienceKnowledge: e.target.value })}
                placeholder="Ví dụ: Đã biết bấm nút nồi cơm nhưng chưa biết tỷ lệ nước chuẩn xác..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                  Nỗi đau / Vấn đề đang gặp phải:
                </label>
                <textarea
                  rows={2}
                  value={brief.audiencePainPoint}
                  onChange={(e) => onBriefChange({ ...brief, audiencePainPoint: e.target.value })}
                  placeholder="Họ bực bội, chán nản hoặc lo lắng vì điều gì..."
                  className="w-full bg-nle-panel border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 resize-none focus:outline-none focus:border-nle-cyan"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                  Khao khát / Kết quả mong muốn:
                </label>
                <textarea
                  rows={2}
                  value={brief.audienceDesire}
                  onChange={(e) => onBriefChange({ ...brief, audienceDesire: e.target.value })}
                  placeholder="Họ muốn đạt kết quả gì nhanh chóng, không tốn công sức..."
                  className="w-full bg-nle-panel border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 resize-none focus:outline-none focus:border-nle-cyan"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 4. MỤC TIÊU VIDEO & CTA */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-nle-violet/20 text-nle-violet flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                04
              </div>
              <span>Mục Tiêu Video & Kêu Gọi Hành Động (CTA)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-nle-violet border-nle-violet/30">Mục tiêu chuyển đổi</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-2">Mục tiêu video hướng tới:</label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {[
                  { id: "education", label: "📚 Giáo dục / Mẹo" },
                  { id: "entertainment", label: "🎭 Giải trí" },
                  { id: "conversion", label: "🛒 Bán hàng / Review" },
                  { id: "follow", label: "➕ Tăng Follow" },
                  { id: "viral_debate", label: "🔥 Viral / Tranh cãi" },
                ].map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, videoGoal: g.id as any })}
                    className={`py-2 px-2 rounded-lg text-center border text-xs font-medium transition-colors ${
                      brief.videoGoal === g.id
                        ? "bg-nle-violet/30 border-nle-violet text-white font-bold shadow-sm"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Hành động muốn người xem làm sau khi xem (like, mua hàng, follow, comment...):
              </label>
              <input
                type="text"
                value={brief.callToAction}
                onChange={(e) => onBriefChange({ ...brief, callToAction: e.target.value })}
                placeholder="Ví dụ: Thả tim và lưu ngay video này lại để bữa tối nay áp dụng thử ngay nhé!"
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
          </CardContent>
        </Card>

        {/* 5. GIỌNG ĐIỆU & PHONG CÁCH */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-rose-400/20 text-rose-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                05
              </div>
              <span>Giọng Điệu, Phong Cách & Trend / Meme</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-rose-400 border-rose-500/30">Tone & Voice</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-2">Tông giọng chủ đạo:</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                {[
                  { id: "casual", label: "Thân mật bạn bè" },
                  { id: "humorous", label: "Hài hước / Meme" },
                  { id: "serious", label: "Nghiêm túc / Uy tín" },
                  { id: "dramatic", label: "Kịch tính / Ly kỳ" },
                  { id: "inspiring", label: "Truyền cảm hứng" },
                  { id: "provocative", label: "Kích thích tranh luận" },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, tone: t.id as any })}
                    className={`py-2 px-2 rounded-lg text-center border text-xs font-medium transition-colors ${
                      brief.tone === t.id
                        ? "bg-rose-500/30 border-rose-400 text-white font-bold shadow-sm"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2.5">
              <div className="flex items-center space-x-2.5">
                <input
                  type="checkbox"
                  id="meme-toggle"
                  checked={brief.includeMemeSlang}
                  onChange={(e) => onBriefChange({ ...brief, includeMemeSlang: e.target.checked })}
                  className="rounded border-nle-border bg-nle-surface text-nle-cyan focus:ring-0 cursor-pointer w-4 h-4"
                />
                <label htmlFor="meme-toggle" className="text-xs text-gray-200 cursor-pointer font-medium">
                  Cho phép chèn trend, meme, tiếng lóng (Slang) giới trẻ để tăng tính giải trí
                </label>
              </div>
              {brief.includeMemeSlang && (
                <div>
                  <label className="block text-[11px] text-gray-400 mb-1">
                    Gợi ý từ lóng / meme muốn xuất hiện trong kịch bản:
                  </label>
                  <input
                    type="text"
                    value={brief.slangKeywords}
                    onChange={(e) => onBriefChange({ ...brief, slangKeywords: e.target.value })}
                    placeholder="Ví dụ: chuẩn đét, siêu bánh cuốn, bí thuật, đỉnh nóc kịch trần..."
                    className="w-full bg-nle-surface border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 6. CẤU TRÚC MONG MUỐN & VISUAL CUE */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-sky-400/20 text-sky-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                06
              </div>
              <span>Cấu Trúc Hook & Gợi Ý Hình Ảnh (Visual Cue)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-sky-400 border-sky-500/30">Giữ chân 3 giây đầu</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-2">
                Kiểu Hook mở đầu <span className="text-gray-400 font-normal">(3 giây đầu quyết định người xem ở lại hay lướt qua):</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { id: "counter_intuitive", label: "⚡ Phản trực giác / Ngược đời" },
                  { id: "fatal_mistake", label: "⚠️ Sai lầm chết người" },
                  { id: "curiosity_gap", label: "❓ Khoảng trống tò mò (Why?)" },
                  { id: "shocking_stat", label: "📊 Số liệu gây sốc thực tế" },
                ].map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, hookType: h.id as any })}
                    className={`p-2.5 rounded-lg text-left border text-xs transition-colors ${
                      brief.hookType === h.id
                        ? "bg-sky-400/20 border-sky-400 text-sky-300 font-bold shadow-sm"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                    }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-2">
                Cấu trúc phân đoạn kịch bản:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { id: "hook_body_climax_cta", label: "Hook (3s) – Thân bài – Cao trào lật kèo – CTA" },
                  { id: "problem_agitate_solution", label: "PAS: Nêu vấn đề – Xoáy sâu nỗi đau – Giải pháp tối ưu" },
                  { id: "myth_busting", label: "Vạch trần lầm tưởng – Dẫn chứng khoa học – Lời khuyên" },
                  { id: "3_step_tutorial", label: "Hướng dẫn 3 bước thực chiến cầm tay chỉ việc" },
                ].map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => onBriefChange({ ...brief, structurePacing: s.id as any })}
                    className={`p-2.5 rounded-lg text-left border text-xs transition-colors ${
                      brief.structurePacing === s.id
                        ? "bg-sky-400/20 border-sky-400 text-sky-300 font-bold shadow-sm"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-nle-panel border border-nle-border flex items-center space-x-2.5">
              <input
                type="checkbox"
                id="cue-toggle"
                checked={brief.includeVisualCues}
                onChange={(e) => onBriefChange({ ...brief, includeVisualCues: e.target.checked })}
                className="rounded border-nle-border bg-nle-surface text-nle-cyan focus:ring-0 cursor-pointer w-4 h-4"
              />
              <label htmlFor="cue-toggle" className="text-xs text-gray-200 cursor-pointer font-medium">
                Tự động kèm chỉ dẫn hình ảnh/cảnh quay cho từng câu thoại (Kịch bản chuẩn "Voiceover + Visual Cue")
              </label>
            </div>
          </CardContent>
        </Card>

        {/* 7. NHÂN VẬT & HÌNH THỨC THỂ HIỆN */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-indigo-400/20 text-indigo-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                07
              </div>
              <span>Nhân Vật / Hình Thức Thể Hiện (Format)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-indigo-400 border-indigo-500/30">Định dạng diễn xuất</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
              {[
                { id: "talking_head", label: "🎙️ Một người nói trực diện camera (On-cam)" },
                { id: "voiceover_broll", label: "🎞️ Lời bình Voiceover + B-roll tư liệu minh họa" },
                { id: "two_person_dialogue", label: "👥 Đối thoại 2 người (Phỏng vấn / Q&A / Tranh luận)" },
                { id: "cinematic_storytelling", label: "🍿 Storytelling tài liệu điện ảnh (Cinematic)" },
                { id: "pov_demo", label: "👀 Góc nhìn thứ nhất (POV thực hành thao tác)" },
              ].map((fmt) => (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => onBriefChange({ ...brief, formatType: fmt.id as any })}
                  className={`p-3 rounded-lg text-left border text-xs transition-colors ${
                    brief.formatType === fmt.id
                      ? "bg-indigo-400/20 border-indigo-400 text-indigo-300 font-bold shadow-sm"
                      : "bg-nle-panel border-nle-border text-gray-300 hover:text-white hover:bg-nle-border"
                  }`}
                >
                  {fmt.label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 8. DỮ LIỆU CỤ THỂ - NHIỀU FILE & NHIỀU TRANG WEB */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-emerald-400/20 text-emerald-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                08
              </div>
              <span>Dữ Liệu Cụ Thể (Số Liệu, Nhiều File & Nhiều Trang Web Đính Kèm)</span>
            </CardTitle>
            <Badge variant="emerald" className="text-xs font-medium">Tránh AI bịa đặt (Grounding)</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Số liệu thực tế, tên riêng, công thức hoặc dữ kiện cần bảo đảm chính xác 100%:
              </label>
              <textarea
                rows={3}
                value={brief.specificFactsAndData}
                onChange={(e) => onBriefChange({ ...brief, specificFactsAndData: e.target.value })}
                placeholder="Nhập các số liệu chính xác, tỷ lệ, công thức, ngày tháng để AI bắt buộc bám sát, tuyệt đối không bịa đặt..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 resize-none font-mono leading-relaxed focus:outline-none focus:border-nle-cyan"
              />
            </div>

            {/* Multiple File Attachments Bin */}
            <div className="p-3.5 rounded-lg bg-nle-panel border border-nle-border space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-gray-200 flex items-center">
                  <Upload className="w-4 h-4 text-emerald-400 mr-2" />
                  <span>Đính kèm tài liệu nghiên cứu (PDF, Word, Excel, TXT, Markdown):</span>
                </label>
                <label className="cursor-pointer px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30 text-xs font-medium flex items-center transition-colors">
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  <span>Chọn thêm file...</span>
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md,.csv"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>

              {brief.attachedFiles && brief.attachedFiles.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  {brief.attachedFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between p-2 rounded bg-nle-surface border border-nle-border text-xs text-gray-200"
                    >
                      <div className="flex items-center space-x-2 truncate mr-2">
                        {file.type === "xlsx" || file.type === "xls" ? (
                          <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <FileText className="w-4 h-4 text-nle-cyan shrink-0" />
                        )}
                        <span className="truncate font-medium">{file.name}</span>
                        <span className="text-[10px] text-gray-400 shrink-0 font-mono">
                          ({(file.size / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(file.id)}
                        className="text-gray-400 hover:text-rose-400 p-1 rounded hover:bg-white/5 transition-colors shrink-0"
                        title="Xóa file này"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic">Chưa có file nào được đính kèm. Bạn có thể chọn nhiều file cùng lúc.</p>
              )}
            </div>

            {/* Multiple Web Pages Bin */}
            <div className="p-3.5 rounded-lg bg-nle-panel border border-nle-border space-y-3">
              <label className="text-xs font-semibold text-gray-200 flex items-center">
                <Globe className="w-4 h-4 text-sky-400 mr-2" />
                <span>Đính kèm đường link / Trang web nguồn dữ liệu:</span>
              </label>

              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  value={newPageUrl}
                  onChange={(e) => setNewPageUrl(e.target.value)}
                  placeholder="Dán URL trang web (ví dụ: https://wikipedia.org/... hoặc báo chí, tài liệu)"
                  className="flex-1 bg-nle-surface border border-nle-border rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddWebPage();
                    }
                  }}
                />
                <input
                  type="text"
                  value={newPageNote}
                  onChange={(e) => setNewPageNote(e.target.value)}
                  placeholder="Ghi chú ngắn (tùy chọn)"
                  className="sm:w-48 bg-nle-surface border border-nle-border rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddWebPage();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddWebPage}
                  className="text-xs h-9 px-3 border-sky-500/40 text-sky-300 hover:bg-sky-500/10 shrink-0 font-medium"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Thêm Link
                </Button>
              </div>

              {brief.attachedPages && brief.attachedPages.length > 0 ? (
                <div className="space-y-1.5 pt-1">
                  {brief.attachedPages.map((page) => (
                    <div
                      key={page.id}
                      className="flex items-center justify-between p-2 rounded bg-nle-surface border border-nle-border text-xs text-gray-200"
                    >
                      <div className="flex items-center space-x-2 truncate mr-2">
                        <Link2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <a
                          href={page.url}
                          target="_blank"
                          rel="noreferrer"
                          className="truncate hover:underline text-sky-300 flex items-center font-mono text-[11px]"
                        >
                          {page.url}
                          <ExternalLink className="w-3 h-3 ml-1 opacity-70 shrink-0" />
                        </a>
                        {page.note && (
                          <span className="text-gray-400 text-[11px] truncate">
                            — {page.note}
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveWebPage(page.id)}
                        className="text-gray-400 hover:text-rose-400 p-1 rounded hover:bg-white/5 transition-colors shrink-0"
                        title="Xóa link này"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic">Chưa có link trang web nào. Dán URL và bấm "Thêm Link".</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 9. VÍ DỤ THAM KHẢO & VIDEO MẪU */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-fuchsia-400/20 text-fuchsia-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                09
              </div>
              <span>Ví Dụ Tham Khảo & Video Mẫu (Benchmark)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-fuchsia-400 border-fuchsia-500/30">Mẫu đối chiếu</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Kênh / Creator bạn thích phong cách để AI học hỏi tông điệu:
              </label>
              <input
                type="text"
                value={brief.benchmarkCreatorOrChannel}
                onChange={(e) => onBriefChange({ ...brief, benchmarkCreatorOrChannel: e.target.value })}
                placeholder="Ví dụ: Kênh @KhoaiLangThang (thân thiện mộc mạc), @NinhTito (hình ảnh đồ ăn bắt mắt)..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                  Link YouTube / TikTok mẫu để lấy nhịp độ:
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={brief.benchmarkMediaUrl}
                    onChange={(e) => onBriefChange({ ...brief, benchmarkMediaUrl: e.target.value })}
                    placeholder="https://youtube.com/watch?v=... hoặc TikTok URL"
                    className="flex-1 bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
                  />
                  <Youtube className="w-5 h-5 text-rose-400 shrink-0" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                  Tải lên video MP4 tham khảo để bóc tách:
                </label>
                <label className="flex items-center justify-center space-x-2 p-2 rounded-lg bg-nle-panel border border-dashed border-nle-border hover:border-fuchsia-400 cursor-pointer text-gray-300 hover:text-white transition-colors h-[42px]">
                  <Video className="w-4 h-4 text-fuchsia-400" />
                  <span className="text-xs">Chọn video MP4 / WebM...</span>
                  <input
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    onChange={handleVideoUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Đoạn script mẫu dán trực tiếp (để AI học cách ngắt nhịp câu và dùng từ):
              </label>
              <textarea
                rows={2}
                value={brief.benchmarkScriptExample}
                onChange={(e) => onBriefChange({ ...brief, benchmarkScriptExample: e.target.value })}
                placeholder="Dán đoạn văn mẫu của video viral bạn ưng ý vào đây..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 resize-none font-mono leading-relaxed focus:outline-none focus:border-nle-cyan"
              />
            </div>
          </CardContent>
        </Card>

        {/* 10. ĐIỀU CẦN TRÁNH */}
        <Card className="border-nle-border bg-nle-surface/90 shadow-md">
          <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center">
              <div className="w-6 h-6 rounded-md bg-rose-500/20 text-rose-400 flex items-center justify-center mr-2.5 text-xs font-mono font-bold">
                10
              </div>
              <span>Điều Cần Tránh (Negative Constraints & Từ Cấm)</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs text-rose-400 border-rose-500/30">An toàn chính sách</Badge>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Không nhắc đối thủ, tránh mở bài sáo rỗng, tránh quan điểm nhạy cảm:
              </label>
              <textarea
                rows={2}
                value={brief.negativeConstraints}
                onChange={(e) => onBriefChange({ ...brief, negativeConstraints: e.target.value })}
                placeholder="Ví dụ: Không chê bai cách làm truyền thống, không dùng từ sáo rỗng 'Chào mừng các bạn quay trở lại kênh...', tránh quảng cáo nhãn hàng cụ thể..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 resize-none focus:outline-none focus:border-nle-cyan"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-200 mb-1.5">
                Từ cấm / Không được xuất hiện trong kịch bản:
              </label>
              <input
                type="text"
                value={brief.forbiddenWords}
                onChange={(e) => onBriefChange({ ...brief, forbiddenWords: e.target.value })}
                placeholder="Ví dụ: nhất thế giới, cam kết 100%, trị dứt điểm, lừa đảo..."
                className="w-full bg-nle-panel border border-nle-border rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
              />
            </div>
          </CardContent>
        </Card>

        {/* BOTTOM ACTION BUTTONS */}
        <div className="bg-nle-panel border border-nle-border rounded-xl p-3.5 flex items-center justify-between shadow-lg mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSavedNotice(true);
              setTimeout(() => setSavedNotice(false), 2000);
            }}
            className="text-xs border-nle-border text-gray-300 hover:text-white h-9 px-3"
          >
            {savedNotice ? (
              <Check className="w-4 h-4 mr-1.5 text-emerald-400" />
            ) : (
              <Save className="w-4 h-4 mr-1.5 text-nle-cyan" />
            )}
            {savedNotice ? "Đã lưu bản nháp đề bài!" : "Lưu Đề Bài"}
          </Button>

          <Button
            variant="neon"
            size="default"
            onClick={onGenerateScript}
            disabled={isProcessing}
            className="px-6 font-bold text-xs h-10 shadow-lg shadow-nle-cyan/25"
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
    </div>
  );
}
