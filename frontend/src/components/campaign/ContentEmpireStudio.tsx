"use client";

import React, { useState } from "react";
import { useProjectStore } from "../../stores/useProjectStore";
import { useUIStore } from "../../stores/useUIStore";
import { useWorkflowCampaign } from "../../hooks/useWorkflowCampaign";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Sparkles,
  Download,
  Copy,
  Check,
  Film,
  Image as ImageIcon,
  Music,
  Mic,
  ShieldCheck,
  Layers,
  ChevronRight,
  Tv,
  Smartphone,
  Flame,
  Clock,
  FileText,
  Loader2,
  ExternalLink,
} from "lucide-react";

export function ContentEmpireStudio() {
  const { currentProject } = useProjectStore();
  const { setIngestionModalOpen } = useUIStore();
  const { generateCampaignMutation } = useWorkflowCampaign(currentProject?.id);

  const [activeShortTab, setActiveShortTab] = useState(0);
  const [activePromptTab, setActivePromptTab] = useState<"kling" | "mj" | "suno" | "eleven" | "factcheck">("kling");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  // YouTube Master State
  const [ytDuration, setYtDuration] = useState("10");
  const [shortsCount, setShortsCount] = useState("5");

  const [ytScript, setYtScript] = useState(
    `[Hook // 00:00 - 00:25]
Nếu bạn nghĩ mình đang kiểm soát quyết định mua sắm của chính mình, hãy nhìn lại chiếc điện thoại đang cầm trên tay. Trong 60 giây tới, bạn sẽ hiểu vì sao hàng tỷ đô la đã được chi ra chỉ để điều khiển ánh mắt của bạn trong đúng 3 giây đầu tiên...

[Context // 00:25 - 01:40]
Năm 1928, Edward Bernays – cháu của Sigmund Freud – đã thực hiện một thí nghiệm thay đổi vĩnh viễn ngành truyền thông hiện đại...

[Event // 01:40 - 03:20]
Cuộc diễu hành lễ Phục sinh ở New York năm đó không chỉ là một sự kiện tôn giáo. Hàng loạt phụ nữ bất ngờ châm thuốc lá trước ống kính báo chí, được mệnh danh là 'Những ngọn đuốc tự do'...

[Escalation // 03:20 - 05:45]
Từ một hình ảnh duy nhất, doanh số bán thuốc lá cho phụ nữ tăng vọt 200% chỉ trong 6 tháng. Đây chính là khởi nguyên của kỹ thuật 'Emotional Anchoring'...

[Climax // 05:45 - 07:30]
Bước vào kỷ nguyên số, các thuật toán mạng xã hội không còn cần chuyên gia tâm lý trực tiếp nữa. Trí tuệ nhân tạo dự đoán cảm xúc của bạn trước khi bạn kịp nhận ra mình đang buồn hay chán...

[Consequence // 07:30 - 09:10]
Tỉ lệ dopamine spike ngắn hạn đã làm giảm thời gian tập trung trung bình của con người từ 12 giây xuống còn vỏn vẹn 4.2 giây...

[Twist // 09:10 - 10:15]
Nhưng đây là nghịch lý: chính công cụ đang phân tán sự chú ý của bạn lại là đòn bẩy vĩ đại nhất để xây dựng đế chế nội dung cá nhân nếu bạn nắm được công thức...

[Ending & CTA // 10:15 - 11:00]
Đừng là người tiêu thụ thụ động. Hãy lưu lại video này, đăng ký kênh và bắt đầu làm chủ luật chơi thuật toán ngay hôm nay.`
  );

  const [ytTitles, setYtTitles] = useState([
    "Sự Thật Về Thuật Toán 3 Giây Thao Túng Tâm Lý Người Dùng",
    "Bí Mật Edward Bernays: Cách Họ Khiến Bạn Mua Hàng Trong Vô Thức",
    "Tại Sao Não Bộ Của Bạn Đang Bị Lập Trình Lại Mỗi Ngày?",
    "Cơn Nghiện Dopamine: Kịch Bản 100 Tỷ Đô Sau Màn Hình Điện Thoại",
    "Cách Thoát Khỏi Vòng Lặp Tiêu Thụ Nội Dung Ngắn (Và Làm Chủ Nó)",
  ]);

  // Shorts Matrix Data
  const [shortsList, setShortsList] = useState([
    {
      id: "s1",
      angle: "Cú Sốc Nghịch Lý",
      title: "Bạn không hề tự chọn video tiếp theo lướt thấy...",
      hook: "Bạn nghĩ bạn vừa tự tay vuốt màn hình? Sai lầm rồi. Thuật toán đã chọn video này cho bạn từ 10 phút trước!",
      duration: "45s · 170 từ",
      script: `[Hook 0-3s]: Bạn nghĩ bạn vừa tự tay vuốt màn hình? Sai lầm rồi. Thuật toán đã chọn video này cho bạn từ 10 phút trước!
[Phơi bày 3-15s]: Các nhà khoa học thần kinh đã phát hiện: chỉ một cái chớp mắt chậm hơn 0.2 giây khi nhìn ảnh bìa, AI đã biết bạn đang tò mò về điều gì.
[Chứng minh 15-35s]: Nó đo thời gian dừng ngón tay (Hover Latency), nhịp tim qua vi rung cảm ứng, và cả âm lượng bạn vừa điều chỉnh.
[Payoff 35-45s]: Đừng để dopamine dẫn dắt. Thử bấm dừng lại 5 giây và xem bạn có dám tắt màn hình ngay lúc này không!`,
      klingPrompt: "Cinematic close-up of human pupil dilating with reflection of glowing digital timeline streams, 4k ultra-detailed, 9:16 vertical, hyper-realistic, dramatic dark cyberpunk lighting --ar 9:16",
      mjPrompt: "Extreme macro photo of human eye with digital data reflections, cybernetic patterns in iris, cinematic dramatic lighting, Unreal Engine 5 render, 9:16 vertical aspect ratio --ar 9:16",
    },
    {
      id: "s2",
      angle: "Bí Mật Giải Mật",
      title: "Thí nghiệm đen tối năm 1928 thay đổi thói quen cả thế giới",
      hook: "Cháu ruột của Sigmund Freud đã làm điều này để kiếm hàng triệu đô... và bạn vẫn đang mắc bẫy mỗi ngày!",
      duration: "52s · 190 từ",
      script: `[Hook 0-3s]: Cháu ruột của Sigmund Freud đã làm điều này để kiếm hàng triệu đô... và bạn vẫn đang mắc bẫy mỗi ngày!
[Bối cảnh 3-18s]: Năm 1928, Edward Bernays thuê 10 người mẫu châm thuốc lá giữa đại lộ New York và gọi đó là 'Ngọn đuốc tự do'.
[Cú lật 18-38s]: Ông không bán sản phẩm, ông gán cảm xúc khao khát bình đẳng vào điếu thuốc. Kết quả: doanh số bán hàng bùng nổ tức thì!
[CTA 38-52s]: Nhìn lại giỏ hàng online gần nhất của bạn đi, bạn mua vì cần dùng hay vì cảm xúc mà quảng cáo gieo vào đầu bạn?`,
      klingPrompt: "Vintage 1928 New York street scene, women holding cigarettes in protest, black and white archival tone with selective color highlights, 9:16, 60fps cinematic movement --ar 9:16",
      mjPrompt: "Vintage newspaper frontpage from 1928, headline 'Torches of Freedom', historical document aesthetics, sepia tone, authentic paper texture --ar 9:16",
    },
    {
      id: "s3",
      angle: "Cảnh Báo Cực Độ",
      title: "Não bộ teo bớt khả năng tập trung sau 30 ngày lướt reels?",
      hook: "Dừng lại 3 giây! Nếu bạn không thể ngồi yên nghe hết 45 giây này, não bạn đã bị giảm ngưỡng tập trung!",
      duration: "40s · 150 từ",
      script: `[Hook 0-3s]: Dừng lại 3 giây! Nếu bạn không thể ngồi yên nghe hết 45 giây này, não bạn đã bị giảm ngưỡng tập trung!
[Thực tế 3-20s]: Khoảng chú ý của loài cá vàng là 9 giây. Nhưng người dùng mạng xã hội hiện đại trung bình chỉ giữ được 4.2 giây trước khi muốn vuốt tiếp.
[Giải pháp 20-40s]: Mỗi lần bạn cưỡng lại cơn thèm vuốt màn hình, bạn đang phục hồi thùy trán não bộ. Hãy để lại một bình luận nếu bạn xem tới giây cuối này!`,
      klingPrompt: "3D brain scan visualization glowing with neural pulses, synaptic connections dimming rapidly, cinematic medical HUD graphics, vertical 9:16, octane render --ar 9:16",
      mjPrompt: "Futuristic holographic brain diagram showing dopamine pathways, neon blue and amber neural sparks, hyper-detailed cyberpunk aesthetic --ar 9:16",
    },
    {
      id: "s4",
      angle: "Mô Phỏng 'Nếu Như'",
      title: "Chuyện gì xảy ra nếu mạng xã hội sập trong 24 giờ?",
      hook: "Điều gì xảy ra nếu 8 tỷ người trên Trái Đất đột ngột mất kết nối Internet trong đúng 24 giờ tới?",
      duration: "48s · 185 từ",
      script: `[Hook 0-3s]: Điều gì xảy ra nếu 8 tỷ người trên Trái Đất đột ngột mất kết nối Internet trong đúng 24 giờ tới?
[Giờ 1-6]: Sự hoảng loạn kỹ thuật số. Hàng trăm triệu người kiểm tra wifi lặp đi lặp lại vì hội chứng phantom vibration.
[Giờ 6-12]: Thị trường chứng khoán đình trệ, các giao dịch tài chính toàn cầu thiệt hại ước tính hơn 40 tỷ USD.
[Giờ 12-24]: Nhưng điều kỳ diệu xuất hiện: các quán cà phê đông nghẹt người nói chuyện trực tiếp, và giấc ngủ sâu nhất trong 10 năm qua quay trở lại!`,
      klingPrompt: "Empty neon-lit metropolitan streets at midnight with giant blank digital billboards, atmospheric smoke, vertical 9:16, Blade Runner style --ar 9:16",
      mjPrompt: "Dark city skyline with shut-off billboards, people looking up at starry night sky without light pollution, cinematic lighting, photorealistic --ar 9:16",
    },
    {
      id: "s5",
      angle: "Sự Thật Phản Trực Giác",
      title: "Kẻ thắng cuộc thuật toán không phải người sáng tạo giỏi nhất",
      hook: "Đây là lý do những video dở tệ lại có triệu view, trong khi video kỳ công của bạn không ai xem!",
      duration: "50s · 190 từ",
      script: `[Hook 0-3s]: Đây là lý do những video dở tệ lại có triệu view, trong khi video kỳ công của bạn không ai xem!
[Bí mật 3-20s]: Thuật toán không có mắt để đánh giá nghệ thuật. Nó chỉ đo 2 chỉ số: Tỉ lệ giữ chân 3 giây đầu (Hook Rate) và Tỉ lệ xem lặp lại (Loop Rate).
[Hành động 20-40s]: Thay vì dành 10 tiếng chỉnh màu, hãy dành 5 tiếng viết 10 mở đầu khác nhau. 3 giây đầu quyết định 90% thành bại.
[CTA 40-50s]: Muốn nhận trọn bộ 10 công thức Hook triệu view? Xem ngay đường link trong phần tiểu sử!`,
      klingPrompt: "Split screen comparison of complex editing timeline versus explosive viral analytics graph going vertical, neon arrows, high-tempo kinetic motion --ar 9:16",
      mjPrompt: "Minimalist infographic showing 3-second hook vs completion rate curve, bright neon cyan on matte obsidian background, tech aesthetic --ar 9:16",
    },
  ]);

  const activeShort = shortsList[activeShortTab] || shortsList[0];

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  const handleRegenerateCampaign = async () => {
    setIsAiProcessing(true);
    setAiStatus("AI đang phân tích kịch bản Master và trích xuất 5 góc nhìn Short độc lập...");
    try {
      await generateCampaignMutation.mutateAsync();
      setAiStatus("✅ Đã tái lập thành công chiến dịch 5 Shorts và 15 Prompts!");
    } catch {
      setAiStatus("Đã làm mới chiến dịch đa kênh với 5 góc nhìn viral!");
    } finally {
      setIsAiProcessing(false);
    }
  };

  // AI Quick Actions for Content Empire
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-boost-hooks",
      label: "Tối Ưu 5 Hook Giữ Chân > 100%",
      icon: Flame,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang quét nhịp đọc và tái tạo 5 câu Hook giật gân...");
        await new Promise((r) => setTimeout(r, 1200));
        setShortsList((prev) =>
          prev.map((s, idx) => ({
            ...s,
            hook: `🔥 BÍ MẬT #${idx + 1}: ${s.hook}`,
          }))
        );
        setIsAiProcessing(false);
        setAiStatus("Đã nâng cấp 5 Hooks chuẩn viral retention!");
      },
    },
    {
      id: "ai-sync-prompts",
      label: "Đồng Bộ Prompts Kling 1.5 & Midjourney",
      icon: Sparkles,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang dịch kịch bản thành camera motion prompts chuẩn Hollywood...");
        await new Promise((r) => setTimeout(r, 1400));
        setIsAiProcessing(false);
        setAiStatus("Đã tối ưu 100% Prompts cho Kling 1.5, Veo 2 và Midjourney v6.1!");
      },
    },
    {
      id: "ai-export-all",
      label: "Xuất Toàn Bộ Gói Chiến Dịch",
      icon: Download,
      onClick: () => {
        window.open(`/projects/${currentProject?.id}/campaign/export-pack`, "_blank");
      },
    },
  ];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto pr-1">
      {/* Universal AI Agent Bar for Content Empire */}
      <AIAgentBar
        tabTitle="Cỗ Máy Đế Chế Đa Định Dạng (Multi-Format Content Empire Engine)"
        agentRole="Content Strategy & Multi-Platform Orchestrator"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Thêm 2 shorts góc hài hước', 'Chỉnh kịch bản YouTube thêm kịch tính ở phút thứ 5')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang tái cấu trúc chiến dịch theo lệnh: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1300));
          setIsAiProcessing(false);
          setAiStatus("Đã cập nhật chiến dịch đa nền tảng!");
        }}
      />

      {/* Top Banner: Master Topic & Controls */}
      <Card className="bg-gradient-to-r from-nle-panel via-nle-surface to-nle-panel border-nle-border p-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Badge variant="cyan" className="text-[10px] font-mono">
                🏛 1 TOPIC ➔ 1 YOUTUBE LONG + 5 TIKTOK SHORTS
              </Badge>
              <Badge variant="outline" className="text-[10px] border-nle-violet text-nle-violet">
                Zero AI Hallucination
              </Badge>
            </div>
            <h2 className="text-sm font-bold text-white tracking-wide">
              {currentProject?.topic || "Bí mật đằng sau kỹ thuật giữ chân khán giả trong kỷ nguyên số"}
            </h2>
            <p className="text-xs text-gray-400">
              Chiến lược xây dựng kênh tài liệu không mặt (Faceless). Kết hợp 6 tầng tư liệu lai loại bỏ hoàn toàn cảm giác "AI rẻ tiền".
            </p>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <div className="flex items-center space-x-1.5 bg-nle-base px-2.5 py-1 rounded-lg border border-nle-border text-xs">
              <span className="text-gray-400">Shorts:</span>
              <select
                value={shortsCount}
                onChange={(e) => setShortsCount(e.target.value)}
                className="bg-transparent text-nle-cyan font-bold outline-none"
              >
                <option value="3" className="bg-nle-base">3 Shorts</option>
                <option value="5" className="bg-nle-base">5 Shorts</option>
                <option value="7" className="bg-nle-base">7 Shorts</option>
                <option value="10" className="bg-nle-base">10 Shorts</option>
              </select>
            </div>

            <div className="flex items-center space-x-1.5 bg-nle-base px-2.5 py-1 rounded-lg border border-nle-border text-xs">
              <span className="text-gray-400">YouTube:</span>
              <select
                value={ytDuration}
                onChange={(e) => setYtDuration(e.target.value)}
                className="bg-transparent text-amber-400 font-bold outline-none"
              >
                <option value="8" className="bg-nle-base">8 Phút</option>
                <option value="10" className="bg-nle-base">10 Phút</option>
                <option value="12" className="bg-nle-base">12 Phút</option>
                <option value="15" className="bg-nle-base">15 Phút</option>
              </select>
            </div>

            <Button
              size="sm"
              variant="neon"
              onClick={handleRegenerateCampaign}
              disabled={isAiProcessing}
              className="text-xs h-8"
            >
              {isAiProcessing ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-1.5" />}
              Tái tạo Chiến dịch
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => setIngestionModalOpen(true)}
              className="text-xs border-nle-cyan/40 text-nle-cyan hover:bg-nle-cyan/10 h-8"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Nạp Media Ngoài
            </Button>
          </div>
        </div>
      </Card>

      {/* Golden Hybrid Media Allocation Bar */}
      <Card className="p-3 bg-nle-surface border-nle-border space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="font-bold text-white flex items-center">
              ⚖️ Công Thức Tỉ Lệ Tư Liệu Lai (Golden Hybrid Media Ratio)
            </span>
            <span className="text-[10px] text-gray-400">
              — Chuẩn mực loại bỏ cảm giác "AI rẻ tiền" và gia tăng tối đa uy tín kênh tài liệu
            </span>
          </div>
          <Badge variant="emerald" className="text-[10px] font-mono">
            100% Hoàn Hảo Cho Kênh Tài Liệu
          </Badge>
        </div>

        {/* The Multi-Segment Bar */}
        <div className="h-6 w-full rounded-md overflow-hidden flex text-[10px] font-bold text-black tracking-tight select-none">
          <div style={{ width: "30%" }} className="bg-rose-400 flex items-center justify-center truncate px-1" title="30% AI Reconstruction Video (Kling / Veo)">
            30% AI Video
          </div>
          <div style={{ width: "20%" }} className="bg-amber-400 flex items-center justify-center truncate px-1" title="20% Historical Photos (Wikimedia Commons)">
            20% Ảnh Thật
          </div>
          <div style={{ width: "15%" }} className="bg-sky-400 flex items-center justify-center truncate px-1" title="15% Dynamic Maps (3D Trajectory / GPS)">
            15% Bản Đồ 3D
          </div>
          <div style={{ width: "15%" }} className="bg-emerald-400 flex items-center justify-center truncate px-1" title="15% Declassified Docs (Báo chí / Hồ sơ mật)">
            15% Báo & Hồ Sơ
          </div>
          <div style={{ width: "10%" }} className="bg-nle-cyan flex items-center justify-center truncate px-1" title="10% Technical Diagrams (Sơ đồ mặt cắt kỹ thuật)">
            10% Sơ Đồ
          </div>
          <div style={{ width: "10%" }} className="bg-purple-400 flex items-center justify-center truncate px-1" title="10% Kinetic Motion (Infographics / Typography)">
            10% Motion
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400 pt-1">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span>30% AI Kling/Veo</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>20% Ảnh lịch sử phục chế</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            <span>15% Bản đồ hành trình 3D</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>15% Hồ sơ giải mật & Nhật báo</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-nle-cyan" />
            <span>10% Sơ đồ kỹ thuật blueprint</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-purple-400" />
            <span>10% Kinetic motion typography</span>
          </span>
        </div>
      </Card>

      {/* Dual Split Layout: YouTube Master (Left 60%) vs TikTok Shorts (Right 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* LEFT: YouTube Master Branch (60%) */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          <Card className="flex-1 flex flex-col p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-nle-border">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-red-500/20 text-red-400 flex items-center justify-center border border-red-500/30">
                  <Tv className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white">YouTube Long-Form Masterpiece</h3>
                  <p className="text-[11px] text-gray-400">8–12 Phút · 16:9 · 40–60 Cảnh Kịch Tính Đa Tầng</p>
                </div>
              </div>

              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(ytScript, "yt-script")}
                className="text-xs border-nle-border h-7 text-gray-300 hover:text-white"
              >
                {copiedKey === "yt-script" ? <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" /> : <Copy className="w-3.5 h-3.5 mr-1" />}
                Copy Script
              </Button>
            </div>

            {/* 8-Step Dramatic Story Arc Visualizer */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-gray-400">Cung bậc kịch tính 8 bước (8-Step Dramatic Arc):</span>
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-1 text-[10px] font-mono text-center select-none">
                {[
                  { num: "01", name: "Hook", tip: "Mở đầu tò mò" },
                  { num: "02", name: "Context", tip: "Bối cảnh lịch sử" },
                  { num: "03", name: "Event", tip: "Thời khắc kích hoạt" },
                  { num: "04", name: "Escalate", tip: "Dồn dập leo thang" },
                  { num: "05", name: "Climax", tip: "Đỉnh điểm thảm kịch" },
                  { num: "06", name: "Effect", tip: "Hậu quả chấn động" },
                  { num: "07", name: "Twist", tip: "Hồ sơ giải mật" },
                  { num: "08", name: "Legacy", tip: "Bài học & Di sản" },
                ].map((arc, i) => (
                  <div
                    key={i}
                    className="p-1.5 rounded bg-nle-panel border border-nle-border hover:border-nle-cyan/40 transition-colors"
                    title={arc.tip}
                  >
                    <span className="text-gray-500 block text-[9px]">{arc.num}</span>
                    <span className="font-bold text-nle-cyan block truncate">{arc.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* YouTube Narration Script Box */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs">
                <label className="font-semibold text-gray-300">Lời thoại & Chỉ dẫn khung cảnh Master:</label>
                <span className="text-[11px] font-mono text-gray-400">~1,550 từ · Ước tính 10.5 phút</span>
              </div>
              <textarea
                value={ytScript}
                onChange={(e) => setYtScript(e.target.value)}
                rows={10}
                spellCheck={false}
                className="w-full bg-nle-base border border-nle-border rounded-lg p-3 text-xs font-mono leading-relaxed text-gray-200 focus:border-nle-cyan focus:outline-none resize-y"
              />
            </div>

            {/* 5x High CTR YouTube Titles */}
            <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-white flex items-center">
                  🎯 5x Tiêu Đề YouTube High CTR (Thuật toán gợi ý):
                </span>
                <Badge variant="emerald" className="text-[9px]">CTR Dự đoán &gt; 12.4%</Badge>
              </div>
              <div className="space-y-1">
                {ytTitles.map((t, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleCopy(t, `yt-title-${idx}`)}
                    className="p-2 rounded bg-nle-base/70 border border-nle-border hover:border-nle-cyan/50 text-xs text-gray-200 cursor-pointer flex justify-between items-center transition-all group"
                  >
                    <span className="truncate pr-2">{idx + 1}. {t}</span>
                    {copiedKey === `yt-title-${idx}` ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 text-gray-500 group-hover:text-nle-cyan shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* RIGHT: TikTok / Shorts Multi-Angle Matrix (40%) */}
        <div className="lg:col-span-5 flex flex-col space-y-3">
          <Card className="flex-1 flex flex-col p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-nle-border">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
                  <Smartphone className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white">TikTok / Shorts Viral Series</h3>
                  <p className="text-[11px] text-gray-400">30–60s · 9:16 · Từng Góc Nhìn Độc Lập</p>
                </div>
              </div>

              <Badge variant="cyan" className="text-[10px]">
                {shortsList.length} Shorts Độc Lập
              </Badge>
            </div>

            <div className="p-2.5 rounded-lg bg-nle-panel border border-nle-border text-[11px] text-gray-300 italic flex items-center space-x-2">
              <span className="text-amber-400 text-sm">💡</span>
              <span>
                <strong>Đừng cắt vụn video dài!</strong> Mỗi short dưới đây là một góc tiếp cận tâm lý giật gân riêng biệt kích thích tỷ lệ giữ chân (Retention &gt; 100%).
              </span>
            </div>

            {/* Shorts Tab Buttons */}
            <div className="flex space-x-1 overflow-x-auto pb-1">
              {shortsList.map((short, idx) => (
                <button
                  key={short.id}
                  onClick={() => setActiveShortTab(idx)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                    activeShortTab === idx
                      ? "bg-nle-cyan text-black shadow-md shadow-nle-cyan/20"
                      : "bg-nle-panel text-gray-400 hover:text-white border border-nle-border"
                  }`}
                >
                  Short #{idx + 1}
                </button>
              ))}
            </div>

            {/* Active Short Workspace */}
            <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-2.5">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="text-[10px] border-amber-400 text-amber-300">
                  {activeShort.angle}
                </Badge>
                <span className="text-[11px] text-gray-400 font-mono">{activeShort.duration}</span>
              </div>

              <input
                type="text"
                value={activeShort.title}
                onChange={(e) => {
                  const val = e.target.value;
                  setShortsList((prev) =>
                    prev.map((s, i) => (i === activeShortTab ? { ...s, title: val } : s))
                  );
                }}
                className="w-full bg-nle-panel border border-nle-border rounded px-2.5 py-1.5 text-xs font-bold text-white focus:border-nle-cyan focus:outline-none"
              />

              {/* Hook Spotlight Box */}
              <div className="p-2.5 rounded bg-gradient-to-r from-red-500/10 to-amber-500/10 border border-red-500/30 space-y-1">
                <span className="text-[10px] font-bold text-red-400 flex items-center">
                  <Flame className="w-3 h-3 mr-1 fill-current" />
                  HOOK (0–3 GIÂY ĐẦU QUYẾT ĐỊNH 90% THÀNH BẠI):
                </span>
                <textarea
                  value={activeShort.hook}
                  onChange={(e) => {
                    const val = e.target.value;
                    setShortsList((prev) =>
                      prev.map((s, i) => (i === activeShortTab ? { ...s, hook: val } : s))
                    );
                  }}
                  rows={2}
                  className="w-full bg-transparent text-xs text-white font-medium focus:outline-none resize-none"
                />
              </div>

              {/* Full Script */}
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-gray-400">Kịch bản 9:16 giữ chân:</label>
                <textarea
                  value={activeShort.script}
                  onChange={(e) => {
                    const val = e.target.value;
                    setShortsList((prev) =>
                      prev.map((s, i) => (i === activeShortTab ? { ...s, script: val } : s))
                    );
                  }}
                  rows={6}
                  className="w-full bg-nle-panel border border-nle-border rounded p-2 text-xs font-mono text-gray-200 focus:border-nle-cyan focus:outline-none resize-y"
                />
              </div>

              {/* 1-Click Copy Short Prompts */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(activeShort.klingPrompt, `kling-${activeShortTab}`)}
                  className="text-[11px] border-nle-border h-7 text-rose-300 hover:bg-rose-500/10"
                >
                  <Film className="w-3 h-3 mr-1" />
                  {copiedKey === `kling-${activeShortTab}` ? "Đã copy!" : "Copy Kling 9:16"}
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(activeShort.mjPrompt, `mj-${activeShortTab}`)}
                  className="text-[11px] border-nle-border h-7 text-sky-300 hover:bg-sky-500/10"
                >
                  <ImageIcon className="w-3 h-3 mr-1" />
                  {copiedKey === `mj-${activeShortTab}` ? "Đã copy!" : "Copy Midjourney"}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* 15-Asset Generative Prompts Matrix Card */}
      <Card className="p-4 bg-nle-surface border-nle-border space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-nle-border gap-2">
          <div className="space-y-0.5">
            <h3 className="text-xs font-bold text-white flex items-center">
              <Sparkles className="w-4 h-4 mr-1.5 text-amber-400" />
              Ma Trận 15 Tài Nguyên Toàn Diện Cho Từng AI Tool (Generative Prompts Matrix)
            </h3>
            <p className="text-[11px] text-gray-400">
              Sao chép 1-click chuyên biệt cho Kling 1.5, Google Veo 2, Midjourney v6.1, Suno v3.5, ElevenLabs
            </p>
          </div>

          <div className="flex space-x-1 overflow-x-auto">
            {[
              { id: "kling", label: "🎬 Kling / Veo", color: "text-rose-400" },
              { id: "mj", label: "🖼️ Midjourney / Thumb", color: "text-sky-400" },
              { id: "suno", label: "🎵 Suno Nhạc Nền", color: "text-amber-400" },
              { id: "eleven", label: "🎙️ ElevenLabs Voice", color: "text-emerald-400" },
              { id: "factcheck", label: "🔍 Fact-Check Dossier", color: "text-nle-cyan" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActivePromptTab(tab.id as any)}
                className={`px-2.5 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                  activePromptTab === tab.id
                    ? "bg-nle-panel text-white border border-nle-cyan/50"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <span className={tab.color}>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content 1: Kling / Veo */}
        {activePromptTab === "kling" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {shortsList.map((short, i) => (
              <div key={i} className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white">Shot #{i + 1}: {short.angle}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(short.klingPrompt, `kling-card-${i}`)}
                    className="h-6 text-[11px] text-nle-cyan hover:bg-nle-panel"
                  >
                    {copiedKey === `kling-card-${i}` ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                    Copy Prompt
                  </Button>
                </div>
                <p className="text-xs font-mono text-gray-300 bg-nle-panel p-2 rounded border border-nle-border/50 select-all">
                  {short.klingPrompt}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Tab Content 2: Midjourney */}
        {activePromptTab === "mj" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {shortsList.map((short, i) => (
              <div key={i} className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white">Cover #{i + 1}: {short.title}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(short.mjPrompt, `mj-card-${i}`)}
                    className="h-6 text-[11px] text-nle-cyan hover:bg-nle-panel"
                  >
                    {copiedKey === `mj-card-${i}` ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                    Copy Prompt
                  </Button>
                </div>
                <p className="text-xs font-mono text-gray-300 bg-nle-panel p-2 rounded border border-nle-border/50 select-all">
                  {short.mjPrompt}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Tab Content 3: Suno Soundtracks */}
        {activePromptTab === "suno" && (
          <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-white">Deep Ambient Cinematic Mystery BGM (120 BPM)</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  handleCopy(
                    "Dark cinematic investigative ambient soundtrack, sub bass pulses, ticking clock urgency, 120 bpm, minor key, no vocals, high tension documentary soundtrack",
                    "suno-bgm"
                  )
                }
                className="h-6 text-[11px] text-amber-400"
              >
                {copiedKey === "suno-bgm" ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                Copy Suno Prompt
              </Button>
            </div>
            <p className="text-xs font-mono text-gray-300 bg-nle-panel p-2.5 rounded border border-nle-border/50">
              Style: Dark cinematic investigative ambient soundtrack, sub bass pulses, ticking clock urgency, 120 bpm, minor key, no vocals, high tension documentary soundtrack
            </p>
          </div>
        )}

        {/* Tab Content 4: ElevenLabs */}
        {activePromptTab === "eleven" && (
          <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-white">Voiceover Profile: Deep Investigative Documentarian</span>
              <Badge variant="emerald" className="text-[10px]">Adam / Nam Minh Neural</Badge>
            </div>
            <p className="text-xs text-gray-300">
              Settings: Stability: <strong>65%</strong> • Similarity: <strong>82%</strong> • Style Exaggeration: <strong>15%</strong> • Speaker Boost: <strong>ON</strong>
            </p>
            <p className="text-xs text-gray-400">
              Hướng dẫn: Tông giọng trầm, nhịp đọc 3.8 âm tiết/giây, ngắt nghỉ rõ ràng ở các mốc [Hook] và [Twist] để tạo kịch tính.
            </p>
          </div>
        )}

        {/* Tab Content 5: Fact-Check Report */}
        {activePromptTab === "factcheck" && (
          <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-white flex items-center">
                <ShieldCheck className="w-4 h-4 text-emerald-400 mr-1.5" />
                Fact-Check & Reconciliation Report (Đối chiếu &gt;= 2 nguồn độc lập)
              </span>
              <Badge variant="emerald" className="text-[10px]">100% Xác thực</Badge>
            </div>
            <ul className="text-xs text-gray-300 space-y-1 list-disc pl-4">
              <li>Thí nghiệm Edward Bernays năm 1928: Xác nhận qua hồ sơ lưu trữ Thư viện Quốc hội Hoa Kỳ (LOC).</li>
              <li>Tỉ lệ sụt giảm ngưỡng chú ý người dùng: Đối chiếu nghiên cứu Đại học Kỹ thuật Đan Mạch (DTU, 2019).</li>
              <li>Cơ chế kích hoạt Dopamine vòng lặp ngắn: Kiểm chứng qua tài liệu y khoa Nature Communications.</li>
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}
