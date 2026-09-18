"use client";

import React, { useEffect } from "react";
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
  Bot,
  DownloadCloud,
  Cpu,
  Target,
  ShieldCheck,
  DollarSign,
  FolderPlus,
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
    title: "Tư liệu & Slide HTML",
    subtitle: "Asset Bin & HTML Slide Deck",
    icon: FolderOpen,
    accentColor: "text-amber-400",
  },
  {
    id: "photo",
    stepNumber: "03",
    title: "Chỉnh sửa Ảnh & Đồ họa",
    subtitle: "Photo Lab & Layer Compositor",
    icon: ImageIcon,
    accentColor: "text-nle-violet",
  },
  {
    id: "video_fx",
    stepNumber: "04",
    title: "Chỉnh sửa Video & Kỹ xảo",
    subtitle: "Speed Ramping & Motion Easing",
    icon: Film,
    accentColor: "text-rose-400",
  },
  {
    id: "audio",
    stepNumber: "05",
    title: "Chỉnh sửa Âm thanh",
    subtitle: "5-Band EQ & Auto-Ducking",
    icon: Sliders,
    accentColor: "text-emerald-400",
  },
  {
    id: "timeline",
    stepNumber: "06",
    title: "Ghép nối Kéo thả",
    subtitle: "NLE Assembly & Dual Monitors",
    icon: Layers,
    accentColor: "text-sky-400",
  },
  {
    id: "export",
    stepNumber: "07",
    title: "Xuất ra & Kiểm duyệt",
    subtitle: "Pre-flight QC & Packaging",
    icon: Download,
    accentColor: "text-amber-500",
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
    setIngestionModalOpen,
    setAgentBridgeModalOpen,
    setSeoModalOpen,
    setQAModalOpen,
    setAuditModalOpen,
    setNewProjectModalOpen,
  } = useUIStore();
  const { currentProject, projects, setCurrentProject } = useProjectStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandBarOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setCommandBarOpen]);

  return (
    <aside
      className={`h-full bg-nle-base border-r border-nle-border flex flex-col justify-between transition-all duration-300 z-30 select-none ${
        sidebarCollapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Top Header / Studio Brand & Project Selector */}
      <div className="flex flex-col shrink-0">
        <div className="h-12 px-3 border-b border-nle-border flex items-center justify-between">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-nle-cyan via-nle-violet to-emerald-400 flex items-center justify-center font-black text-black text-[11px] shadow-sm shadow-nle-cyan/20">
                CF
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-xs tracking-wider text-white">
                  STUDIO <span className="text-nle-cyan text-[10px]">ULTIMATE</span>
                </span>
              </div>
            </div>
          )}

          {sidebarCollapsed && (
            <div className="w-7 h-7 mx-auto rounded-md bg-gradient-to-tr from-nle-cyan to-nle-violet flex items-center justify-center font-bold text-black text-xs">
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

        {/* Project Selector & Status Banner */}
        {!sidebarCollapsed ? (
          <div className="p-2 border-b border-nle-border bg-nle-panel/30">
            <div className="flex items-center space-x-1.5">
              {projects && projects.length > 0 ? (
                <select
                  value={currentProject?.id || ""}
                  onChange={(e) => {
                    const p = projects.find((proj) => proj.id === e.target.value);
                    if (p) setCurrentProject(p);
                  }}
                  className="flex-1 bg-nle-panel border border-nle-border rounded-md px-2 py-1 text-xs text-white font-medium outline-none truncate"
                >
                  {projects.map((proj) => (
                    <option key={proj.id} value={proj.id} className="bg-nle-base">
                      {proj.name}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="flex-1 text-xs font-semibold text-gray-200 truncate px-1">
                  {currentProject?.name || "Dự án mẫu"}
                </span>
              )}
              <button
                onClick={() => setNewProjectModalOpen(true)}
                className="w-7 h-7 rounded-md bg-nle-panel hover:bg-nle-surface border border-nle-border text-nle-cyan flex items-center justify-center transition-colors shrink-0"
                title="Tạo dự án mới"
              >
                <FolderPlus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Mandatory Review Gates Badges */}
            {currentProject && (
              <div className="mt-1.5 flex items-center gap-1 flex-wrap">
                <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-nle-panel text-nle-cyan border border-nle-border">
                  {currentProject.status.replace("_", " ")}
                </span>
                {currentProject.status === "script_review" && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse font-medium">
                    Gate 1: Duyệt kịch bản
                  </span>
                )}
                {currentProject.status === "video_review" && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse font-medium">
                    Gate 2: Duyệt video
                  </span>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="py-2 flex justify-center border-b border-nle-border">
            <button
              onClick={() => setNewProjectModalOpen(true)}
              className="w-8 h-8 rounded-md bg-nle-panel hover:bg-nle-surface border border-nle-border text-nle-cyan flex items-center justify-center transition-colors"
              title="Tạo dự án mới"
            >
              <FolderPlus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Main Navigation: 7 Steps */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {/* Workflow Title */}
        {!sidebarCollapsed && (
          <div className="px-3.5 pt-3 pb-1 flex items-center justify-between shrink-0">
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

      {/* Bottom Auxiliary Section: Tools Quick Bar, DAG, Campaign & AI Agent Status */}
      <div className="p-2 border-t border-nle-border space-y-1.5 bg-nle-surface/40 shrink-0">
        {/* Quick Modal Tools Bar */}
        {!sidebarCollapsed ? (
          <div className="grid grid-cols-5 gap-1 bg-nle-panel/60 p-1 rounded-lg border border-nle-border">
            <button
              onClick={() => setIngestionModalOpen(true)}
              className="p-1.5 rounded flex items-center justify-center text-gray-400 hover:text-nle-cyan hover:bg-nle-surface transition-colors"
              title="Nạp Media ngoại vi (Kling, Veo, URL)"
            >
              <DownloadCloud className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setAgentBridgeModalOpen(true)}
              className="p-1.5 rounded flex items-center justify-center text-gray-400 hover:text-nle-violet hover:bg-nle-surface transition-colors"
              title="Universal Agent Bridge (Claude, Gemini brief.md)"
            >
              <Cpu className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setSeoModalOpen(true)}
              className="p-1.5 rounded flex items-center justify-center text-gray-400 hover:text-amber-400 hover:bg-nle-surface transition-colors"
              title="Chấm điểm SEO 70 tín hiệu"
            >
              <Target className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setQAModalOpen(true)}
              className="p-1.5 rounded flex items-center justify-center text-gray-400 hover:text-emerald-400 hover:bg-nle-surface transition-colors"
              title="Tuân thủ chính sách & Bản quyền (Gate QA)"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setAuditModalOpen(true)}
              className="p-1.5 rounded flex items-center justify-center text-gray-400 hover:text-rose-400 hover:bg-nle-surface transition-colors"
              title="Kiểm toán chi phí Token / GPU"
            >
              <DollarSign className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col space-y-1 items-center pb-1 border-b border-nle-border">
            <button
              onClick={() => setIngestionModalOpen(true)}
              className="w-8 h-8 rounded-md flex items-center justify-center text-gray-400 hover:text-nle-cyan hover:bg-nle-panel transition-colors"
              title="Nạp Media ngoại vi"
            >
              <DownloadCloud className="w-4 h-4" />
            </button>
            <button
              onClick={() => setAgentBridgeModalOpen(true)}
              className="w-8 h-8 rounded-md flex items-center justify-center text-gray-400 hover:text-nle-violet hover:bg-nle-panel transition-colors"
              title="Agent Bridge"
            >
              <Cpu className="w-4 h-4" />
            </button>
            <button
              onClick={() => setSeoModalOpen(true)}
              className="w-8 h-8 rounded-md flex items-center justify-center text-gray-400 hover:text-amber-400 hover:bg-nle-panel transition-colors"
              title="SEO Scorer"
            >
              <Target className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Visual DAG Workflow Link */}
        <button
          onClick={() => setActiveTab("workflow")}
          title={sidebarCollapsed ? "Visual DAG Orchestrator" : undefined}
          className={`w-full flex items-center rounded-lg transition-all text-left ${
            sidebarCollapsed ? "p-2.5 justify-center" : "px-3 py-2 space-x-2.5"
          } ${
            activeTab === "workflow"
              ? "bg-nle-panel border border-nle-cyan/40 text-nle-cyan shadow-sm"
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
              ? "bg-nle-panel border border-nle-violet/40 text-nle-violet shadow-sm"
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
