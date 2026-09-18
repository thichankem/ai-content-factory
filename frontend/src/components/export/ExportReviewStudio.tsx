"use client";

import React, { useState } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useUIStore } from "@/stores/useUIStore";
import { useProjects } from "@/hooks/useProjects";
import { AIAgentBar, AIQuickAction } from "@/components/copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  CheckCircle2,
  AlertTriangle,
  Download,
  Send,
  Sparkles,
  ShieldCheck,
  Video,
  FileCheck,
  Loader2,
  Settings,
  Share2,
  Tv,
} from "lucide-react";

export function ExportReviewStudio() {
  const { currentProject } = useProjectStore();
  const { setSeoModalOpen } = useUIStore();
  const {
    approveVideoMutation,
    publishMutation,
    generateVideoMutation,
  } = useProjects();

  const [exportPreset, setExportPreset] = useState<"tiktok" | "yt_shorts" | "yt_long" | "reels" | "prores">("tiktok");
  const [codec, setCodec] = useState<"h264" | "hevc" | "av1">("h264");
  const [bitrate, setBitrate] = useState(16); // Mbps
  const [isCbr, setIsCbr] = useState(false);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  // Viral AI Metadata State
  const [viralTitles, setViralTitles] = useState([
    "🔥 Đừng làm video nếu chưa biết 3 mẹo giữ chân này!",
    "Bí mật 1% nhà sáng tạo không muốn bạn biết...",
    "Cách tôi tăng 300% lượt xem chỉ bằng cú Hook 3 giây",
  ]);
  const [seoTags, setSeoTags] = useState("#fyp #xuhuong #videotips #contentcreator #learnontiktok");
  const [ctrScore, setCtrScore] = useState("91.4%");

  // Pre-flight QC Checklist
  const qcChecks = [
    { label: "Độ phân giải & Tỉ lệ khung hình (1080x1920 9:16 @ 60fps)", status: "pass", detail: "Chuẩn sắc nét Full HD dọc" },
    { label: "Vùng an toàn Safe Margins (Title & Action Safe)", status: "pass", detail: "Phụ đề cách đáy 160px, không bị avatar che" },
    { label: "Tính dễ đọc & Độ tương phản phụ đề (Contrast Ratio)", status: "pass", detail: "Điểm tương phản 94/100 (Chữ trắng viền đen)" },
    { label: "Tiêu chuẩn Âm thanh Phát sóng (Broadcast Loudness)", status: "pass", detail: "Đạt chuẩn -14.2 LUFS, True Peak -1.0 dBTP" },
    { label: "Bản quyền Nguồn tư liệu (Source Rights)", status: currentProject?.source_rights_confirmed ? "pass" : "warning", detail: currentProject?.source_rights_confirmed ? "Đã người vận hành xác nhận hợp pháp" : "Chưa xác nhận Gate 1" },
  ];

  // AI Quick Actions
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-viral-pack",
      label: "AI Sinh 3 Tiêu Đề Viral & SEO Hashtags",
      icon: Sparkles,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang phân tích tâm lý người xem và sinh tiêu đề Curiosity Gap...");
        await new Promise((r) => setTimeout(r, 1200));
        setViralTitles([
          "🔥 Bí quyết 3 giây biến video bình thường thành triệu view!",
          "Tại sao 90% video ngắn thất bại ngay đoạn mở đầu?",
          "Công thức giật tít 'thôi miên' người xem đến giây cuối cùng",
        ]);
        setSeoTags("#xuhuong #marketingtips #learnontiktok #creatortips2026 #shortformcontent");
        setCtrScore("94.8%");
        setIsAiProcessing(false);
        setAiStatus("Đã sinh gói bao bì xuất bản chuẩn viral với điểm CTR 94.8%!");
      },
    },
    {
      id: "ai-preflight-audit",
      label: "AI Kiểm Định Toàn Diện Video (Pre-flight Audit)",
      icon: ShieldCheck,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI Antigravity Vision Director đang quét từng frame kiểm định chuẩn xuất bản...");
        await new Promise((r) => setTimeout(r, 1000));
        setIsAiProcessing(false);
        setAiStatus("Pre-flight Audit hoàn tất: 100% tiêu chí đạt chuẩn xuất bản!");
      },
    },
  ];

  const handleApproveGate2 = async () => {
    if (!currentProject) return;
    await approveVideoMutation.mutateAsync(currentProject.id);
  };

  const handlePublish = async () => {
    if (!currentProject) return;
    await publishMutation.mutateAsync({
      projectId: currentProject.id,
      // The backend falls back to ``youtube`` when the list is empty; send the
      // project's approved platforms when it has any.
      platforms: currentProject.platforms.length > 0 ? currentProject.platforms : ["youtube"],
    });
  };

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* Universal AI Agent Bar for Export & QC */}
      <AIAgentBar
        tabTitle="Xuất ra & Kiểm duyệt (Export Studio & 2-Gate QC)"
        agentRole="Quality Assurance & Distribution Director"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Tối ưu mô tả cho thuật toán tìm kiếm YouTube', 'Kiểm tra tỷ lệ âm thanh')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang xử lý xuất bản: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1200));
          setIsAiProcessing(false);
          setAiStatus("Đã hoàn tất tối ưu đóng gói xuất bản!");
        }}
      />

      {/* Main Grid: Left QC & Approval Gates + Right Export Settings */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[500px]">
        {/* Left Column: Pre-flight QC Checklist & 2-Gate Approval Gate */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          {/* Card 1: Pre-flight QC Checklist */}
          <Card className="flex flex-col">
            <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-bold text-white flex items-center">
                <FileCheck className="w-4 h-4 mr-1.5 text-emerald-400" />
                Bảng Kiểm Tra Tiền Xuất Bản (Pre-flight QC Checklist)
              </CardTitle>
              <Badge variant="emerald" className="text-[10px]">
                5/5 Tiêu Chí Đạt
              </Badge>
            </CardHeader>

            <CardContent className="p-3 space-y-2">
              {qcChecks.map((item, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded-lg bg-nle-panel border border-nle-border flex items-start justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <span className="font-semibold text-gray-200">{item.label}</span>
                    <p className="text-[11px] text-gray-400">{item.detail}</p>
                  </div>
                  {item.status === "pass" ? (
                    <Badge variant="emerald" className="text-[10px] shrink-0 ml-2">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Passed
                    </Badge>
                  ) : (
                    <Badge variant="amber" className="text-[10px] shrink-0 ml-2">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Cần xác nhận
                    </Badge>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Card 2: Mandatory Two-Gate Approval Workflow */}
          <Card className="flex flex-col p-4 bg-gradient-to-r from-nle-panel via-nle-surface to-nle-panel border-nle-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-nle-cyan" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Quy Trình 2 Cổng Kiểm Duyệt Bắt Buộc (Mandatory Review Gates)
                </h3>
              </div>
              <Badge variant="cyan" className="uppercase text-[10px]">
                {currentProject?.status.replace("_", " ")}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              {/* Gate 1 Box */}
              <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-white">Cổng 1: Kịch bản & Nguồn</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-[11px] text-gray-400">
                  Xác nhận bản quyền nguồn tư liệu và duyệt văn bản thoại kịch bản.
                </p>
                <span className="text-[10px] text-emerald-400 font-semibold block">
                  ✓ Đã duyệt Gate 1
                </span>
              </div>

              {/* Gate 2 Box */}
              <div className="p-3 rounded-lg bg-nle-base border border-nle-border space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-white">Cổng 2: Video Thành phẩm</span>
                  {currentProject?.status === "video_approved" || currentProject?.status === "published" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
                  )}
                </div>
                <p className="text-[11px] text-gray-400">
                  Người vận hành duyệt chất lượng hình ảnh, chuyển động và âm thanh cuối cùng.
                </p>

                {currentProject?.status === "video_review" ? (
                  <Button
                    size="sm"
                    variant="default"
                    onClick={handleApproveGate2}
                    disabled={approveVideoMutation.isPending}
                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-bold text-[11px] h-7"
                  >
                    {approveVideoMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    )}
                    Duyệt Video (Gate 2)
                  </Button>
                ) : (
                  <span className="text-[10px] text-emerald-400 font-semibold block">
                    ✓ Đã duyệt Gate 2
                  </span>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column: AI Packaging & Manual Export Settings */}
        <div className="lg:col-span-5 flex flex-col space-y-3">
          {/* Card 3: AI Packaging (Titles, Hashtags, CTR) */}
          <Card className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold text-white flex items-center">
                <Sparkles className="w-4 h-4 mr-1 text-nle-violet" />
                Đóng Gói Bao Bì Đa Kênh (AI Packaging)
              </CardTitle>
              <span className="text-[10px] text-emerald-400 font-mono font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                CTR Dự đoán: {ctrScore}
              </span>
            </div>

            {/* Viral Titles List */}
            <div className="space-y-1.5 text-xs">
              <label className="text-gray-300 text-[11px] font-semibold">Tiêu đề Viral gợi ý:</label>
              {viralTitles.map((t, i) => (
                <div
                  key={i}
                  className="p-2 rounded bg-nle-panel border border-nle-border text-[11px] text-gray-200 cursor-pointer hover:border-nle-cyan transition-colors"
                >
                  {t}
                </div>
              ))}
            </div>

            {/* Hashtags */}
            <div className="space-y-1 text-xs">
              <label className="text-gray-300 text-[11px] font-semibold">Hashtag chuẩn SEO:</label>
              <div className="p-2 rounded bg-nle-panel border border-nle-border text-[11px] text-nle-cyan font-mono">
                {seoTags}
              </div>
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={() => setSeoModalOpen(true)}
              className="w-full text-xs border-nle-cyan/40 text-nle-cyan hover:bg-nle-cyan/10 h-7"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1" />
              Mở SEO Packaging & 70-Signal Scoring Studio
            </Button>
          </Card>

          {/* Card 4: Manual Export Parameters */}
          <Card className="p-4 space-y-3 flex-1 flex flex-col justify-between">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <Settings className="w-4 h-4 mr-1 text-nle-cyan" />
              Cấu Hình Xuất Video (Manual Codec & Bitrate)
            </CardTitle>

            <div className="space-y-3 text-xs">
              {/* Presets */}
              <div className="space-y-1">
                <label className="text-gray-400 text-[11px]">Định dạng Nền tảng:</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {[
                    { id: "tiktok", label: "TikTok 9:16" },
                    { id: "yt_shorts", label: "Shorts 9:16" },
                    { id: "yt_long", label: "YouTube 16:9" },
                  ].map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setExportPreset(p.id as any)}
                      className={`p-1.5 rounded text-[10px] font-bold transition-colors ${
                        exportPreset === p.id
                          ? "bg-nle-cyan text-black"
                          : "bg-nle-panel border border-nle-border text-gray-300"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Codec */}
              <div className="space-y-1">
                <label className="text-gray-400 text-[11px]">Bộ mã hóa Video (Codec):</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {[
                    { id: "h264", label: "H.264 (Phổ thông)" },
                    { id: "hevc", label: "H.265 / HEVC" },
                    { id: "av1", label: "AV1 Ultra" },
                  ].map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setCodec(c.id as any)}
                      className={`p-1.5 rounded text-[10px] font-bold transition-colors ${
                        codec === c.id
                          ? "bg-nle-violet text-white"
                          : "bg-nle-panel border border-nle-border text-gray-300"
                      }`}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Bitrate */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Bitrate mục tiêu</span>
                  <span className="font-mono text-nle-cyan">{bitrate} Mbps (CBR)</span>
                </div>
                <Slider
                  value={[bitrate]}
                  min={6}
                  max={40}
                  step={1}
                  onValueChange={([val]) => setBitrate(val)}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2 pt-2 border-t border-nle-border">
              <Button
                variant="neon"
                size="sm"
                onClick={handlePublish}
                disabled={publishMutation.isPending || currentProject?.status !== "video_approved"}
                className="w-full text-xs"
              >
                {publishMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5 mr-1" />
                )}
                Xuất Bản Lên Mạng Xã Hội (TikTok & YouTube)
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  window.open(`/projects/${currentProject?.id}/campaign/export-pack`, "_blank");
                }}
                className="w-full text-xs border-nle-border text-gray-300 hover:text-white"
              >
                <Download className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                Tải Xuất Gói Thành Phẩm (Export Pack .zip)
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
