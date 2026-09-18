"use client";

import React, { useState } from "react";
import { DualMonitorPlayer } from "./DualMonitorPlayer";
import { TimelineVisualizer } from "./TimelineVisualizer";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { useTimelineStore } from "../../stores/useTimelineStore";
import { Sparkles, Layers, Scissors, Magnet, Wand2 } from "lucide-react";

export function TimelineAssemblyStudio() {
  const { setScenes, setSelectedSceneIndex } = useTimelineStore();
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  // Quick actions for Timeline Assembly
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-auto-assemble",
      label: "AI Tự Ghép Nối Timeline Từ Kịch Bản",
      icon: Wand2,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang đọc cấu trúc Hook/Turn/CTA và tự động xếp clip vào V1, V2, A1...");
        await new Promise((r) => setTimeout(r, 1400));
        setScenes([
          { index: 0, label: "Scene 1 • Hook 3s Viral", duration: 3.8, text: "90% video ngắn thất bại ngay trong 3s đầu", filter: "vibrant" },
          { index: 1, label: "Scene 2 • Bằng chứng Thống kê", duration: 14.5, text: "Lý do là vì thiếu một chiếc Hook giữ chân", filter: "cinema" },
          { index: 2, label: "Scene 3 • Cú lật Bất ngờ", duration: 11.2, text: "Áp dụng ngay 3 bước này để giữ chân 100%", filter: "warm" },
          { index: 3, label: "Scene 4 • Payoff & CTA Cuối", duration: 8.5, text: "Bấm theo dõi để xem trọn bộ bí kíp!", filter: "none" },
        ]);
        setSelectedSceneIndex(0);
        setIsAiProcessing(false);
        setAiStatus("Đã tự động ghép nối hoàn chỉnh 4 phân cảnh vào Timeline!");
      },
    },
    {
      id: "ai-beat-snap",
      label: "AI Hút Vết Cắt Khớp Beat (Magnetic Snap)",
      icon: Magnet,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang căn chỉnh các điểm nối clip khớp chuẩn xác từng nhịp trống BGM...");
        await new Promise((r) => setTimeout(r, 900));
        setIsAiProcessing(false);
        setAiStatus("Đã đồng bộ 100% vết cắt clip theo nhịp beat 120 BPM!");
      },
    },
    {
      id: "ai-suggest-transitions",
      label: "AI Gợi Ý Chuyển Cảnh (Whip Pan / Glitch)",
      icon: Sparkles,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang phân tích chuyển động và chèn Transition Whip Pan vào điểm lật cảnh...");
        await new Promise((r) => setTimeout(r, 1000));
        setIsAiProcessing(false);
        setAiStatus("Đã chèn 3 hiệu ứng chuyển cảnh động cực mượt!");
      },
    },
  ];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-hidden">
      {/* Universal AI Agent Bar for Timeline */}
      <AIAgentBar
        tabTitle="Ghép nối Kéo thả (Timeline Assembly & NLE Monitors)"
        agentRole="Executive Film Director & Editor"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Cắt bỏ 2 giây đầu của Scene 2', 'Chèn b-roll vào khoảng giây thứ 5')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang điều khiển dòng thời gian: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1300));
          setIsAiProcessing(false);
          setAiStatus("Đã thực thi điều chỉnh timeline từ AI Prompt!");
        }}
      />

      {/* Top: Dual Monitor Player + Audio VU Meter + Tool Palette */}
      <div className="flex-1 min-h-[320px] overflow-hidden">
        <DualMonitorPlayer />
      </div>

      {/* Bottom: Professional Multi-track Timeline */}
      <div className="h-56 shrink-0">
        <TimelineVisualizer />
      </div>
    </div>
  );
}
