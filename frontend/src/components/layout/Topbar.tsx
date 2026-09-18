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
} from "lucide-react";

export function Topbar() {
  const { currentProject, projects } = useProjectStore();
  const {
    activeTab,
    setActiveTab,
    setCommandBarOpen,
    setQAModalOpen,
    setAuditModalOpen,
    setNewProjectModalOpen,
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

  // Adobe Premiere Pro Workspace Tabs (Learning, Assembly, Editing, Color, Effects, Audio, Graphics)
  const adobeWorkspaces: Array<{ id: ActiveStudioTab; label: string }> = [
    { id: "script", label: "Kịch bản" },
    { id: "assets", label: "Tư liệu" },
    { id: "photo", label: "Đồ họa / Ảnh" },
    { id: "video_fx", label: "Màu sắc & FX" },
    { id: "audio", label: "Âm thanh" },
    { id: "timeline", label: "Dựng phim (Assembly)" },
    { id: "export", label: "Xuất bản (Export)" },
  ];

  return (
    <header className="h-14 border-b border-nle-border bg-nle-surface/95 backdrop-blur px-4 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Project Info */}
      <div className="flex items-center space-x-3">
        {currentProject && (
          <div className="flex items-center space-x-2">
            <span className="text-sm font-bold text-white max-w-[200px] truncate">
              {currentProject.name}
            </span>
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

      {/* Premiere Pro Workspaces Bar */}
      <nav className="hidden md:flex items-center space-x-1 bg-nle-panel border border-nle-border rounded-lg p-0.5 text-xs">
        {adobeWorkspaces.map((ws) => (
          <button
            key={ws.id}
            onClick={() => setActiveTab(ws.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === ws.id
                ? "bg-nle-surface text-nle-cyan shadow-sm font-semibold border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {ws.label}
          </button>
        ))}
      </nav>

      {/* Action Tools & AI Co-Pilot */}
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCommandBarOpen(true)}
          className="border-nle-cyan/40 text-nle-cyan hover:bg-nle-cyan/10 text-xs flex items-center space-x-1.5 h-8"
        >
          <Sparkles className="w-3.5 h-3.5 text-nle-cyan" />
          <span>AI Co-Pilot</span>
          <kbd className="text-[10px] bg-nle-panel px-1.5 py-0.5 rounded border border-nle-border ml-1 text-gray-400 font-mono">
            Ctrl+K
          </kbd>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setQAModalOpen(true)}
          className="text-xs text-gray-300 hover:text-white h-8"
        >
          <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
          <span>QA & Brand</span>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAuditModalOpen(true)}
          className="text-xs text-gray-300 hover:text-white h-8"
        >
          <DollarSign className="w-3.5 h-3.5 mr-1 text-amber-400" />
          <span>Cost & Audit</span>
        </Button>
      </div>
    </header>
  );
}
