"use client";

import React, { useEffect } from "react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { useProjectStore } from "../../stores/useProjectStore";
import { useUIStore, ActiveStudioTab } from "../../stores/useUIStore";
import {
  Sparkles,
  ShieldCheck,
  DollarSign,
  FolderPlus,
  Play,
  Share2,
  DownloadCloud,
  Cpu,
  Target,
} from "lucide-react";

export function Topbar() {
  const { currentProject, projects, setCurrentProject } = useProjectStore();
  const {
    activeTab,
    setActiveTab,
    setCommandBarOpen,
    setQAModalOpen,
    setAuditModalOpen,
    setNewProjectModalOpen,
    setIngestionModalOpen,
    setAgentBridgeModalOpen,
    setSeoModalOpen,
  } = useUIStore();

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

  // Standard NLE Workspace Layouts (Script, Assets & Slides, Graphics, Color & FX, Audio, Assembly, Export)
  const nleWorkspaces: Array<{ id: ActiveStudioTab; label: string }> = [
    { id: "script", label: "Kịch bản" },
    { id: "assets", label: "Tư liệu & Slides" },
    { id: "photo", label: "Đồ họa / Ảnh" },
    { id: "video_fx", label: "Màu sắc & FX" },
    { id: "audio", label: "Âm thanh" },
    { id: "timeline", label: "Dựng phim (Assembly)" },
    { id: "export", label: "Xuất bản (Export)" },
  ];

  return (
    <header className="h-14 border-b border-nle-border bg-nle-surface/95 backdrop-blur px-4 flex items-center justify-between sticky top-0 z-40">
      {/* Brand, Project Info & Selector */}
      <div className="flex items-center space-x-2.5">
        {projects && projects.length > 0 ? (
          <select
            value={currentProject?.id || ""}
            onChange={(e) => {
              const p = projects.find((proj) => proj.id === e.target.value);
              if (p) setCurrentProject(p);
            }}
            className="bg-nle-panel border border-nle-border rounded-lg px-2.5 py-1 text-xs text-white font-bold outline-none max-w-[200px] truncate"
          >
            {projects.map((proj) => (
              <option key={proj.id} value={proj.id} className="bg-nle-base">
                {proj.name}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-sm font-bold text-white max-w-[200px] truncate">
            {currentProject?.name || "Dự án mẫu"}
          </span>
        )}

        <Button
          size="sm"
          variant="outline"
          onClick={() => setNewProjectModalOpen(true)}
          className="h-7 px-2 border-nle-border text-gray-300 hover:text-white text-xs"
          title="Tạo dự án mới"
        >
          <FolderPlus className="w-3.5 h-3.5 text-nle-cyan" />
        </Button>

        {currentProject && (
          <div className="hidden lg:flex items-center space-x-2">
            <Badge variant="cyan" className="uppercase text-[10px] font-mono">
              {currentProject.status.replace("_", " ")}
            </Badge>

            {/* Mandatory Review Gates Badges */}
            {currentProject.status === "script_review" && (
              <Badge variant="amber" className="text-[10px] animate-pulse">
                Gate 1: Cần duyệt kịch bản
              </Badge>
            )}
            {currentProject.status === "video_review" && (
              <Badge variant="amber" className="text-[10px] animate-pulse">
                Gate 2: Cần duyệt video
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* NLE Workspaces Bar */}
      <nav className="hidden xl:flex items-center space-x-1 bg-nle-panel border border-nle-border rounded-lg p-0.5 text-xs">
        {nleWorkspaces.map((ws) => (
          <button
            key={ws.id}
            onClick={() => setActiveTab(ws.id)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
              activeTab === ws.id
                ? "bg-nle-surface text-nle-cyan shadow-sm font-semibold border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {ws.label}
          </button>
        ))}
      </nav>

      {/* Action Tools & AI Quick Hubs */}
      <div className="flex items-center space-x-1.5">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIngestionModalOpen(true)}
          className="border-nle-border text-gray-300 hover:text-white text-xs h-7 px-2"
          title="Nạp tư liệu từ Kling, Veo, Midjourney, ElevenLabs"
        >
          <DownloadCloud className="w-3.5 h-3.5 text-nle-cyan mr-1" />
          <span className="hidden sm:inline">Nạp Media</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setAgentBridgeModalOpen(true)}
          className="border-nle-border text-gray-300 hover:text-white text-xs h-7 px-2"
          title="Xuất brief.md cho Claude/Gemini và nhập kịch bản"
        >
          <Cpu className="w-3.5 h-3.5 text-nle-violet mr-1" />
          <span className="hidden sm:inline">Agent Bridge</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setSeoModalOpen(true)}
          className="border-nle-border text-gray-300 hover:text-white text-xs h-7 px-2"
          title="Chấm điểm 70 tín hiệu SEO YouTube/TikTok"
        >
          <Target className="w-3.5 h-3.5 text-amber-400 mr-1" />
          <span className="hidden sm:inline">SEO</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setCommandBarOpen(true)}
          className="border-nle-cyan/40 text-nle-cyan hover:bg-nle-cyan/10 text-xs flex items-center space-x-1 h-7 px-2"
        >
          <Sparkles className="w-3 h-3 text-nle-cyan" />
          <span>Co-Pilot</span>
          <kbd className="hidden md:inline text-[9px] bg-nle-panel px-1 py-0.5 rounded border border-nle-border text-gray-400 font-mono">
            Ctrl+K
          </kbd>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setQAModalOpen(true)}
          className="text-xs text-gray-300 hover:text-white h-7 px-2"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAuditModalOpen(true)}
          className="text-xs text-gray-300 hover:text-white h-7 px-2"
        >
          <DollarSign className="w-3.5 h-3.5 text-amber-400" />
        </Button>
      </div>
    </header>
  );
}
