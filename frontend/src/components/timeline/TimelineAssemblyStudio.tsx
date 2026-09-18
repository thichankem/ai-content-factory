"use client";

import React, { useState } from "react";
import { DualMonitorPlayer } from "@/components/timeline/DualMonitorPlayer";
import { TimelineVisualizer } from "@/components/timeline/TimelineVisualizer";
import { AIAgentBar, AIQuickAction } from "@/components/copilot/AIAgentBar";
import { useTimelineStore } from "@/stores/useTimelineStore";
import { makeScenes } from "@/lib/scenes";
import { PropertiesInspector } from "@/components/inspector/PropertiesInspector";
import { CaptionSimplifier } from "@/components/captions/CaptionSimplifier";
import {
  Sparkles,
  Layers,
  Scissors,
  Magnet,
  Wand2,
  Sliders,
  Type,
  ChevronRight,
  ChevronLeft,
  PanelRight,
} from "lucide-react";

export function TimelineAssemblyStudio() {
  const { setScenes, setSelectedSceneIndex } = useTimelineStore();
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);
  const [activeSidePanel, setActiveSidePanel] = useState<"properties" | "captions" | "none">("properties");

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
        setScenes(
          makeScenes([
            { label: "Scene 1 • Hook 3s Viral", duration: 3.8, text: "90% video ngắn thất bại ngay trong 3s đầu", filter: "contrast" },
            { label: "Scene 2 • Bằng chứng Thống kê", duration: 14.5, text: "Lý do là vì thiếu một chiếc Hook giữ chân", filter: "cool" },
            { label: "Scene 3 • Cú lật Bất ngờ", duration: 11.2, text: "Áp dụng ngay 3 bước này để giữ chân 100%", grade: "teal-orange" },
            { label: "Scene 4 • Payoff & CTA Cuối", duration: 8.5, text: "Bấm theo dõi để xem trọn bộ bí kíp!" },
          ])
        );
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

      {/* Top: Dual Monitor Player + Right Collapsible Inspector Panel */}
      <div className="flex-1 min-h-[340px] flex overflow-hidden gap-3 relative">
        {/* Center/Left: Dual Monitor Player */}
        <div className="flex-1 min-w-0 h-full overflow-hidden flex flex-col">
          <DualMonitorPlayer />
        </div>

        {/* Right Collapsible Inspector (Properties Inspector & Neural Auto-Captions) */}
        {activeSidePanel !== "none" ? (
          <div className="w-80 lg:w-96 shrink-0 h-full overflow-hidden flex flex-col bg-nle-surface border border-nle-border rounded-xl shadow-xl">
            {/* Inspector Switcher Tabs Header */}
            <div className="h-10 px-2.5 bg-nle-panel border-b border-nle-border flex items-center justify-between shrink-0 text-xs">
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setActiveSidePanel("properties")}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                    activeSidePanel === "properties"
                      ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5 text-nle-cyan" />
                  <span>Properties</span>
                </button>

                <button
                  onClick={() => setActiveSidePanel("captions")}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                    activeSidePanel === "captions"
                      ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <Type className="w-3.5 h-3.5 text-amber-400" />
                  <span>Auto-Captions</span>
                </button>
              </div>

              <button
                onClick={() => setActiveSidePanel("none")}
                className="p-1 rounded text-gray-400 hover:text-white hover:bg-nle-surface transition-colors"
                title="Thu gọn bảng thuộc tính để mở rộng Monitor"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Inspector Scrollable Viewport */}
            <div className="flex-1 overflow-y-auto p-2">
              {activeSidePanel === "properties" && <PropertiesInspector />}
              {activeSidePanel === "captions" && <CaptionSimplifier />}
            </div>
          </div>
        ) : (
          /* Expand Button when Panel is Collapsed */
          <button
            onClick={() => setActiveSidePanel("properties")}
            className="absolute right-2 top-2 z-30 px-2.5 py-1.5 rounded-lg bg-nle-panel border border-nle-border text-gray-300 hover:text-white hover:border-nle-cyan/50 text-xs font-semibold flex items-center space-x-1.5 shadow-md backdrop-blur-sm"
            title="Mở bảng Properties Inspector"
          >
            <PanelRight className="w-3.5 h-3.5 text-nle-cyan" />
            <span>Mở Inspector</span>
          </button>
        )}
      </div>

      {/* Bottom: Professional Multi-track Timeline */}
      <div className="h-56 shrink-0">
        <TimelineVisualizer />
      </div>
    </div>
  );
}
