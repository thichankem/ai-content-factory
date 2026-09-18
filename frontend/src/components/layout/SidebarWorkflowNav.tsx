"use client";

import React from "react";
import { useUIStore, ActiveStudioTab } from "../../stores/useUIStore";
import { useProjectStore } from "../../stores/useProjectStore";
import {
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Film,
  Sliders,
  Layers,
  Download,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  GitBranch,
  ShieldAlert,
  Bot,
} from "lucide-react";

interface WorkflowStep {
  id: ActiveStudioTab;
  stepNumber: string;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: "script",
    stepNumber: "01",
    title: "Xây dựng Kịch bản",
    subtitle: "AI Script & Storyboard",
    icon: FileText,
    accentColor: "text-nle-cyan",
  },
  {
    id: "assets",
    stepNumber: "02",
    title: "Chọn Tư liệu & Nhạc",
    subtitle: "Asset Hunter & Media Bin",
    icon: FolderOpen,
    accentColor: "text-amber-400",
  },
  {
    id: "photo",
    stepNumber: "03",
    title: "Chỉnh sửa Ảnh",
    subtitle: "Photo Lab & Photoshop Layers",
    icon: ImageIcon,
    accentColor: "text-nle-violet",
  },
  {
    id: "video_fx",
    stepNumber: "04",
    title: "Chỉnh sửa Video & FX",
    subtitle: "After Effects & Speed Ramp",
    icon: Film,
    accentColor: "text-rose-400",
  },
  {
    id: "audio",
    stepNumber: "05",
    title: "Chỉnh sửa Âm thanh",
    subtitle: "Audition EQ & Ducking",
    icon: Sliders,
    accentColor: "text-emerald-400",
  },
  {
    id: "timeline",
    stepNumber: "06",
    title: "Ghép nối Kéo thả",
    subtitle: "NLE Assembly & Dual Monitor",
    icon: Layers,
    accentColor: "text-sky-400",
  },
  {
    id: "export",
    stepNumber: "07",
    title: "Xuất ra & Kiểm duyệt",
    subtitle: "Pre-flight QC & 2-Gate Approval",
    icon: Download,
    accentColor: "text-nle-cyan",
  },
];

export function SidebarWorkflowNav() {
  const {
    activeTab,
    setActiveTab,
    completedSteps,
    sidebarCollapsed,
    toggleSidebar,
    setCommandBarOpen,
  } = useUIStore();
  const { currentProject } = useProjectStore();

  return (
    <aside
      className={`h-full bg-nle-base border-r border-nle-border flex flex-col justify-between transition-all duration-300 z-30 select-none ${
        sidebarCollapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Top Header / Studio Brand */}
      <div>
        <div className="h-14 px-3.5 border-b border-nle-border flex items-center justify-between">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-nle-cyan via-nle-violet to-emerald-400 flex items-center justify-center font-black text-black text-xs shadow-md shadow-nle-cyan/20">
                CF
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-xs tracking-wider text-white">
                  STUDIO <span className="text-nle-cyan text-[10px]">ULTIMATE</span>
                </span>
                <span className="text-[9px] text-gray-400 tracking-tight">
                  Premiere • AE • CapCut
                </span>
              </div>
            </div>
          )}

          {sidebarCollapsed && (
            <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-tr from-nle-cyan to-nle-violet flex items-center justify-center font-bold text-black text-xs">
              CF
            </div>
          )}

          <button
            onClick={toggleSidebar}
            className="p-1 rounded-md text-gray-400 hover:text-white hover:bg-nle-panel transition-colors"
            title={sidebarCollapsed ? "Mở rộng thanh công cụ" : "Thu gọn thanh công cụ"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Workflow Title */}
        {!sidebarCollapsed && (
          <div className="px-3.5 pt-3 pb-1 flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Quy trình Dựng phim 7 Bước
            </span>
            <span className="text-[10px] font-mono text-nle-cyan">
              {Object.values(completedSteps).filter(Boolean).length}/7 Done
            </span>
          </div>
        )}

        {/* Sequential 7-Step Navigation Items */}
        <nav className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-250px)]">
          {WORKFLOW_STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = activeTab === step.id;
            const isCompleted = completedSteps[step.id];

            return (
              <button
                key={step.id}
                onClick={() => setActiveTab(step.id)}
                title={sidebarCollapsed ? `${step.stepNumber}. ${step.title}` : undefined}
                className={`w-full group relative flex items-center rounded-lg transition-all text-left ${
                  sidebarCollapsed ? "p-2.5 justify-center" : "px-3 py-2.5 space-x-3"
                } ${
                  isActive
                    ? "bg-gradient-to-r from-nle-panel via-nle-surface to-transparent border border-nle-cyan/40 shadow-lg shadow-nle-cyan/5 text-white"
                    : "text-gray-400 hover:text-gray-100 hover:bg-nle-panel/60 border border-transparent"
                }`}
              >
                {/* Step Number or Active Indicator Bar */}
                {isActive && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-nle-cyan shadow-sm shadow-nle-cyan" />
                )}

                {/* Step Icon */}
                <div
                  className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 transition-colors ${
                    isActive
                      ? "bg-nle-cyan/20 text-nle-cyan border border-nle-cyan/30"
                      : "bg-nle-panel text-gray-400 group-hover:text-white border border-nle-border"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Step Info (When Expanded) */}
                {!sidebarCollapsed && (
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-gray-500 font-bold tracking-tight">
                        STEP {step.stepNumber}
                      </span>
                      {isCompleted ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isActive ? (
                        <span className="w-2 h-2 rounded-full bg-nle-cyan animate-ping" />
                      ) : null}
                    </div>
                    <span
                      className={`text-xs font-semibold truncate ${
                        isActive ? "text-white" : "text-gray-300 group-hover:text-white"
                      }`}
                    >
                      {step.title}
                    </span>
                    <span className="text-[10px] text-gray-500 truncate">
                      {step.subtitle}
                    </span>
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Auxiliary Section: DAG, Campaign & AI Agent Status */}
      <div className="p-2 border-t border-nle-border space-y-1 bg-nle-surface/40">
        {/* Visual DAG Workflow Link */}
        <button
          onClick={() => setActiveTab("workflow")}
          title={sidebarCollapsed ? "Visual DAG Orchestrator" : undefined}
          className={`w-full flex items-center rounded-lg transition-all text-left ${
            sidebarCollapsed ? "p-2.5 justify-center" : "px-3 py-2 space-x-2.5"
          } ${
            activeTab === "workflow"
              ? "bg-nle-panel border border-nle-cyan/40 text-nle-cyan"
              : "text-gray-400 hover:text-white hover:bg-nle-panel/40"
          }`}
        >
          <GitBranch className="w-4 h-4 text-nle-cyan shrink-0" />
          {!sidebarCollapsed && (
            <span className="text-xs font-medium truncate">Visual DAG Pipeline</span>
          )}
        </button>

        {/* Omni-Channel Campaign Link */}
        <button
          onClick={() => setActiveTab("campaign")}
          title={sidebarCollapsed ? "Omni-Channel Campaign" : undefined}
          className={`w-full flex items-center rounded-lg transition-all text-left ${
            sidebarCollapsed ? "p-2.5 justify-center" : "px-3 py-2 space-x-2.5"
          } ${
            activeTab === "campaign"
              ? "bg-nle-panel border border-nle-violet/40 text-nle-violet"
              : "text-gray-400 hover:text-white hover:bg-nle-panel/40"
          }`}
        >
          <Sparkles className="w-4 h-4 text-nle-violet shrink-0" />
          {!sidebarCollapsed && (
            <span className="text-xs font-medium truncate">Omni Campaign (5 Shorts)</span>
          )}
        </button>

        {/* AI Agent Harness Status Pill */}
        <div
          onClick={() => setCommandBarOpen(true)}
          className={`cursor-pointer rounded-lg border border-nle-border bg-nle-panel/80 p-2 flex items-center hover:border-nle-cyan/50 transition-all ${
            sidebarCollapsed ? "justify-center" : "space-x-2"
          }`}
          title="Mở AI Agent Harness Co-Pilot (Ctrl+K)"
        >
          <div className="relative">
            <Bot className="w-4 h-4 text-nle-cyan" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-nle-panel animate-pulse" />
          </div>
          {!sidebarCollapsed && (
            <div className="flex flex-col min-w-0">
              <div className="flex items-center space-x-1">
                <span className="text-[11px] font-bold text-white">AI Harness</span>
                <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1 rounded font-mono">
                  Online
                </span>
              </div>
              <span className="text-[9px] text-gray-400 truncate">
                Gemini • Kling • ElevenLabs
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
