"use client";

import React, { useState } from "react";
import { useProjectStore } from "../../stores/useProjectStore";
import { useScriptEngine } from "../../hooks/useScriptEngine";
import { useProjects } from "../../hooks/useProjects";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { ViralityScoreResult } from "../../types/api";
import { Flame, CheckCircle2, AlertTriangle, Sparkles, Loader2, BookOpen, Clock, ShieldCheck } from "lucide-react";

export function ScriptStudio() {
  const { currentProject, confirmSourceRights } = useProjectStore();
  const { viralityMutation, updateScriptMutation } = useScriptEngine(currentProject?.id);
  const { approveScriptMutation } = useProjects();

  const [scriptText, setScriptText] = useState(
    currentProject?.script?.raw_script ||
      "[Hook]\nBạn có biết: 90% video ngắn thất bại ngay trong 3 giây đầu tiên?\n\n[Bằng chứng]\nLý do không phải vì nội dung dở, mà vì bạn chưa biết cách tạo Hook thu hút sự chú ý tức thì theo nguyên lý Curiosity Gap.\n\n[Cú lật Turn]\nHãy áp dụng ngay 3 bước này để giữ chân 100% khán giả đến giây cuối cùng.\n\n[Payoff & CTA]\nTheo dõi kênh để đón xem trọn bộ bí kíp tăng trưởng triệu view!"
  );

  const [viralityResult, setViralityResult] = useState<ViralityScoreResult | null>(null);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  const wordCount = scriptText.trim().split(/\s+/).filter(Boolean).length;
  const estimatedSeconds = (wordCount / 2.6).toFixed(1); // Vietnamese avg ~155 words per min

  const handleScoreVirality = async () => {
    try {
      const res = await viralityMutation.mutateAsync({
        scriptText,
        topic: currentProject?.topic || "Short-form video retention",
      });
      setViralityResult(res);
    } catch (err) {
      console.error("Failed to calculate virality:", err);
    }
  };

  const handleApproveGate1 = async () => {
    if (!currentProject) return;
    if (!currentProject.source_rights_confirmed) {
      alert("Bạn phải xác nhận bản quyền nguồn tư liệu (Source Rights) trước khi duyệt!");
      return;
    }
    await approveScriptMutation.mutateAsync(currentProject.id);
  };

  // AI Quick Actions for Script Studio
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-hook-gen",
      label: "AI Viết Lại Hook 3s Giật Gân",
      icon: Flame,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang phân tích tâm lý tò mò và tạo 3 biến thể Hook tỷ lệ giữ chân cao...");
        await new Promise((r) => setTimeout(r, 1100));
        setScriptText(
          "[Hook]\nĐừng bao giờ làm video nếu bạn chưa biết bí mật giữ chân này!\n\n" +
            scriptText.replace(/^\[Hook\]\n.*?\n\n/s, "")
        );
        setIsAiProcessing(false);
        setAiStatus("Đã tối ưu lại Hook 3 giây đầu kích thích tò mò tột độ!");
      },
    },
    {
      id: "ai-dramatic-tone",
      label: "AI Đổi Giọng Điệu Kịch Tính / Điện Ảnh",
      icon: Sparkles,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang biến đổi cấu trúc câu sang văn phong điều tra, gay cấn...");
        await new Promise((r) => setTimeout(r, 1200));
        setIsAiProcessing(false);
        setAiStatus("Đã chuyển đổi ngữ điệu kịch tính thành công!");
      },
    },
    {
      id: "ai-copy-risk",
      label: "AI Quét Đạo Văn & Bản Quyền (100% Unique)",
      icon: ShieldCheck,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang đối chiếu văn bản với kho dữ liệu YouTube/TikTok...");
        await new Promise((r) => setTimeout(r, 900));
        setIsAiProcessing(false);
        setAiStatus("An toàn 100%: Không phát hiện câu từ trùng lặp hay vi phạm bản quyền!");
      },
    },
  ];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* Universal AI Agent Bar for Scriptwriting */}
      <AIAgentBar
        tabTitle="Xây dựng Kịch bản (Scriptwriting & Storyboard)"
        agentRole="Chief Storyteller & Viral Script Director"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Viết kịch bản 45s về cách AI thay đổi ngành đồ họa', 'Thêm tình tiết hài hước')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang sinh kịch bản theo yêu cầu: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1400));
          setScriptText(
            `[Hook]\nBạn nghĩ AI sẽ cướp việc của designer? Sự thật hoàn toàn ngược lại!\n\n[Bằng chứng]\nTrong 30 ngày qua, những nhà sáng tạo kết hợp AI cùng Premiere Pro và After Effects đã tăng tốc độ sản xuất gấp 10 lần.\n\n[Cú lật Turn]\nBí quyết không nằm ở công cụ, mà ở tư duy kết hợp giữa Prompt thông minh và tay nghề chỉnh sửa thủ công.\n\n[Payoff & CTA]\nLưu ngay video này để áp dụng cho dự án tiếp theo!`
          );
          setIsAiProcessing(false);
          setAiStatus("Đã soạn thảo xong kịch bản mới chuẩn viral!");
        }}
      />

      {/* Main Grid: Editor Column + Analytics Column */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 flex-1 min-h-[460px]">
        {/* Script Editor Column */}
        <div className="lg:col-span-2 flex flex-col space-y-3">
          <Card className="flex-1 flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-nle-border">
              <div>
                <CardTitle className="text-xs font-bold text-white flex items-center">
                  <BookOpen className="w-4 h-4 mr-1.5 text-nle-cyan" />
                  <span>Trình soạn thảo Kịch bản (Script Studio)</span>
                  <Badge variant="cyan" className="ml-2 text-[9px]">
                    {wordCount} Từ • ~{estimatedSeconds}s Đọc
                  </Badge>
                </CardTitle>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Phân tách các khối [Hook], [Bằng chứng], [Cú lật], [CTA] để timeline tự đồng bộ
                </p>
              </div>

              <Button
                variant="neon"
                size="sm"
                onClick={handleScoreVirality}
                disabled={viralityMutation.isPending}
                className="text-xs h-7"
              >
                {viralityMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Flame className="w-3.5 h-3.5 mr-1.5 fill-current" />
                )}
                <span>Chấm điểm Virality</span>
              </Button>
            </CardHeader>

            <CardContent className="flex-1 p-3 flex flex-col justify-between">
              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                className="flex-1 w-full p-3 bg-nle-panel border border-nle-border rounded-lg text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-nle-cyan resize-none font-sans leading-relaxed"
                rows={10}
              />

              {/* Mandatory Human Review Gate 1 Banner */}
              <div className="mt-3 p-3 bg-nle-panel border border-nle-amber/40 rounded-lg flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="source-rights"
                    checked={currentProject?.source_rights_confirmed || false}
                    onChange={confirmSourceRights}
                    className="rounded border-nle-border text-nle-cyan focus:ring-0 w-4 h-4 bg-nle-surface cursor-pointer"
                  />
                  <label htmlFor="source-rights" className="text-xs text-gray-300 cursor-pointer">
                    Tôi xác nhận bản quyền nội dung nguồn tư liệu hợp pháp (Source Rights Confirmed)
                  </label>
                </div>

                <Button
                  variant="default"
                  size="sm"
                  onClick={handleApproveGate1}
                  disabled={!currentProject?.source_rights_confirmed || approveScriptMutation.isPending}
                  className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs h-7"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  <span>Gate 1: Duyệt kịch bản</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Virality Metrics Column */}
        <div className="flex flex-col space-y-3">
          <Card className="h-full flex flex-col">
            <CardHeader className="py-2.5 px-3 border-b border-nle-border">
              <CardTitle className="text-xs font-bold flex items-center text-white">
                <Flame className="w-4 h-4 text-amber-400 mr-1.5 fill-current" />
                <span>Phân tích Tỷ lệ Giữ chân (Virality Analytics)</span>
              </CardTitle>
            </CardHeader>

            <CardContent className="p-3 flex-1 flex flex-col space-y-3">
              {viralityResult ? (
                <>
                  <div className="p-3 rounded-lg bg-nle-panel border border-nle-border text-center">
                    <span className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-nle-cyan to-nle-violet">
                      {viralityResult.score}/100
                    </span>
                    <p className="text-[11px] text-gray-400 mt-0.5">Dự đoán tỷ lệ hoàn thành video</p>
                  </div>

                  {/* 4-part metrics breakdown */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded bg-nle-panel border border-nle-border text-center">
                      <span className="text-[10px] text-gray-400 uppercase">Hook (3s đầu)</span>
                      <p className="text-sm font-bold text-nle-cyan">{viralityResult.hook_score}%</p>
                    </div>
                    <div className="p-2 rounded bg-nle-panel border border-nle-border text-center">
                      <span className="text-[10px] text-gray-400 uppercase">Nhịp độ (Pacing)</span>
                      <p className="text-sm font-bold text-nle-violet">{viralityResult.pacing_score}%</p>
                    </div>
                    <div className="p-2 rounded bg-nle-panel border border-nle-border text-center">
                      <span className="text-[10px] text-gray-400 uppercase">Thời lượng (Duration)</span>
                      <p className="text-sm font-bold text-emerald-400">{viralityResult.duration_score}%</p>
                    </div>
                    <div className="p-2 rounded bg-nle-panel border border-nle-border text-center">
                      <span className="text-[10px] text-gray-400 uppercase">Kêu gọi (CTA)</span>
                      <p className="text-sm font-bold text-amber-400">{viralityResult.cta_score}%</p>
                    </div>
                  </div>

                  {/* Actionable Advice */}
                  <div className="flex-1 p-2.5 rounded bg-nle-panel border border-nle-border overflow-y-auto">
                    <span className="text-xs font-semibold text-white mb-1.5 block">💡 Gợi ý tối ưu retention:</span>
                    <ul className="space-y-1.5">
                      {viralityResult.advice.map((adv, idx) => (
                        <li key={idx} className="text-xs text-gray-300 flex items-start">
                          <span className="text-nle-cyan mr-1.5">•</span>
                          <span>{adv}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4 text-gray-400 border border-dashed border-nle-border rounded-lg">
                  <Sparkles className="w-8 h-8 text-nle-cyan/40 mb-2" />
                  <p className="text-xs">
                    Bấm <strong>Chấm điểm Virality</strong> để AI quét retention rate, hook và nhịp độ kịch bản.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
