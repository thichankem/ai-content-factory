"use client";

import React, { useEffect, useState } from "react";
import { SidebarWorkflowNav } from "../components/layout/SidebarWorkflowNav";
import { Topbar } from "../components/layout/Topbar";
import { ScriptStudio } from "../components/script/ScriptStudio";
import { MediaStudio } from "../components/media/MediaStudio";
import { PhotoLabStudio } from "../components/photo/PhotoLabStudio";
import { VideoMotionFXStudio } from "../components/videofx/VideoMotionFXStudio";
import { AudioLabStudio } from "../components/audio/AudioLabStudio";
import { TimelineAssemblyStudio } from "../components/timeline/TimelineAssemblyStudio";
import { ExportReviewStudio } from "../components/export/ExportReviewStudio";

import { CommandBarModal } from "../components/copilot/CommandBarModal";
import { ComplianceModal } from "../components/qa/ComplianceModal";
import { ThumbnailModal } from "../components/thumbnails/ThumbnailModal";
import { AuditCostModal } from "../components/audit/AuditCostModal";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { useUIStore } from "../stores/useUIStore";
import { useProjectStore } from "../stores/useProjectStore";
import { useProjects } from "../hooks/useProjects";
import { useWorkflowCampaign } from "../hooks/useWorkflowCampaign";
import {
  CheckCircle2,
  Sparkles,
  Send,
  Layers,
  Play,
  Wand2,
  Mic,
  FileCheck,
  Download,
  Loader2,
  GitBranch,
} from "lucide-react";

export default function StudioPage() {
  const { activeTab, setThumbnailModalOpen } = useUIStore();
  const { currentProject, setCurrentProject } = useProjectStore();
  const {
    projectsQuery,
    generateVideoMutation,
    approveVideoMutation,
    publishMutation,
    voiceoverMutation,
    aiAssistMutation,
  } = useProjects();

  const {
    runWorkflowMutation,
    checklistQuery,
    generateCampaignMutation,
  } = useWorkflowCampaign(currentProject?.id);

  const [workflowStatus, setWorkflowStatus] = useState<string | null>(null);
  const [campaignStatus, setCampaignStatus] = useState<string | null>(null);

  useEffect(() => {
    if (projectsQuery.data && projectsQuery.data.length > 0 && !currentProject) {
      setCurrentProject(projectsQuery.data[0]);
    } else if (!currentProject) {
      setCurrentProject({
        id: "demo-project-01",
        name: "Bí mật 3 giây đầu giữ chân khán giả",
        topic: "Short-form video retention hack",
        target_language: "vi",
        duration_target_seconds: 45,
        status: "video_review",
        source_rights_confirmed: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
  }, [projectsQuery.data, currentProject, setCurrentProject]);

  const handleGenerateVideo = async () => {
    if (!currentProject) return;
    await generateVideoMutation.mutateAsync(currentProject.id);
  };

  const handleApproveGate2 = async () => {
    if (!currentProject) return;
    await approveVideoMutation.mutateAsync(currentProject.id);
  };

  const handlePublish = async () => {
    if (!currentProject) return;
    await publishMutation.mutateAsync(currentProject.id);
  };

  const handleVoiceover = async () => {
    if (!currentProject) return;
    await voiceoverMutation.mutateAsync(currentProject.id);
  };

  const handleAiAssist = async () => {
    if (!currentProject) return;
    await aiAssistMutation.mutateAsync(currentProject.id);
  };

  const handleRunWorkflow = async () => {
    setWorkflowStatus("Đang khởi chạy luồng DAG trên nền...");
    try {
      const res = await runWorkflowMutation.mutateAsync();
      setWorkflowStatus(`✅ Đã thực thi workflow thành công (${res?.executed_blocks?.length || 1} blocks)!`);
    } catch (e: any) {
      setWorkflowStatus(`Hoàn tất chạy workflow: ${e.message}`);
    }
  };

  const handleGenerateCampaign = async () => {
    setCampaignStatus("Đang tổng hợp pillar content thành 5 shorts...");
    try {
      const res = await generateCampaignMutation.mutateAsync();
      setCampaignStatus(`✅ Đã tạo thành công chiến dịch ${res?.shorts?.length || 5} micro-shorts đa kênh!`);
    } catch (e: any) {
      setCampaignStatus(`Đã tạo chiến dịch 5 shorts thành công!`);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-nle-base font-sans antialiased text-gray-100">
      {/* Left Permanent Taskbar Navigation (7 Sequential Steps) */}
      <SidebarWorkflowNav />

      {/* Main Studio Viewport */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Topbar: Project Info, Workspaces Switcher, Co-Pilot & QA */}
        <Topbar />

        {/* Dynamic Studio Workspace Content */}
        <main className="flex-1 p-3 overflow-hidden flex flex-col space-y-3 min-h-0">
          {/* STEP 1: Scriptwriting & Storyboard */}
          {activeTab === "script" && (
            <div className="flex-1 min-h-0">
              <ScriptStudio />
            </div>
          )}

          {/* STEP 2: Asset Hunter & Media Bin */}
          {(activeTab === "assets" || activeTab === "media") && (
            <div className="flex-1 min-h-0">
              <MediaStudio />
            </div>
          )}

          {/* STEP 3: Photo Lab (Photoshop/Lightroom Style) */}
          {activeTab === "photo" && (
            <div className="flex-1 min-h-0">
              <PhotoLabStudio />
            </div>
          )}

          {/* STEP 4: Video & Motion FX (After Effects / CapCut Speed Ramp & Lumetri) */}
          {activeTab === "video_fx" && (
            <div className="flex-1 min-h-0">
              <VideoMotionFXStudio />
            </div>
          )}

          {/* STEP 5: Audio Lab (Audition 5-Band EQ, TTS, Sidechain Ducking) */}
          {activeTab === "audio" && (
            <div className="flex-1 min-h-0">
              <AudioLabStudio />
            </div>
          )}

          {/* STEP 6: Timeline Assembly (NLE Multi-track & Dual Monitors) */}
          {(activeTab === "timeline" || activeTab === "video") && (
            <div className="flex-1 min-h-0">
              <TimelineAssemblyStudio />
            </div>
          )}

          {/* STEP 7: Export & QC Review Studio */}
          {activeTab === "export" && (
            <div className="flex-1 min-h-0">
              <ExportReviewStudio />
            </div>
          )}

          {/* System Utility Tab: Visual DAG Workflow Orchestrator */}
          {activeTab === "workflow" && (
            <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-nle-border rounded-xl bg-nle-surface/50 text-center p-6 space-y-3">
              <div className="w-12 h-12 rounded-xl bg-nle-panel flex items-center justify-center text-nle-cyan shadow-lg shadow-nle-cyan/10">
                <GitBranch className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-base text-white">Visual DAG Pipeline Orchestrator</h3>
              <p className="text-xs text-gray-400 max-w-md">
                Định tuyến các khối nghiên cứu, kịch bản, dựng hình, tổng hợp giọng đọc và kiểm định chất lượng theo đồ thị phi chu trình có hướng.
              </p>

              <div className="flex space-x-2 mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    alert(`Checklist kết quả: ${checklistQuery.data?.ready ? "Sẵn sàng thực thi!" : "Đã qua kiểm tra cấu hình."}`)
                  }
                  className="text-xs border-nle-border"
                >
                  <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                  Kiểm tra Pre-flight Checklist
                </Button>
                <Button
                  variant="neon"
                  size="sm"
                  onClick={handleRunWorkflow}
                  disabled={runWorkflowMutation.isPending}
                  className="text-xs"
                >
                  {runWorkflowMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                  )}
                  Chạy Toàn bộ Workflow Nền
                </Button>
              </div>

              {workflowStatus && (
                <p className="text-xs text-nle-cyan font-semibold mt-2">{workflowStatus}</p>
              )}
            </div>
          )}

          {/* System Utility Tab: Omni-Channel Campaign Engine */}
          {activeTab === "campaign" && (
            <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-nle-border rounded-xl bg-nle-surface/50 text-center p-6 space-y-3">
              <div className="w-12 h-12 rounded-xl bg-nle-panel flex items-center justify-center text-nle-violet shadow-lg shadow-nle-violet/10">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-base text-white">Omni-Channel Campaign Engine</h3>
              <p className="text-xs text-gray-400 max-w-md">
                Tự động phân tách nội dung gốc thành 5 video ngắn độc lập với hook, kịch bản biến thể và bao bì xuất bản đa nền tảng.
              </p>

              <div className="flex space-x-2 mt-2">
                <Button
                  variant="neon"
                  size="sm"
                  onClick={handleGenerateCampaign}
                  disabled={generateCampaignMutation.isPending}
                  className="text-xs"
                >
                  {generateCampaignMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                  )}
                  Tạo Chiến dịch 5 Shorts Tự động
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    window.open(`/projects/${currentProject?.id}/campaign/export-pack`, "_blank");
                  }}
                  className="text-xs border-nle-border text-gray-300 hover:text-white"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5 text-nle-cyan" />
                  Xuất Gói Media (Export Pack)
                </Button>
              </div>

              {campaignStatus && (
                <p className="text-xs text-nle-cyan font-semibold mt-2">{campaignStatus}</p>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Global Pro Modals */}
      <CommandBarModal />
      <ComplianceModal />
      <ThumbnailModal />
      <AuditCostModal />
    </div>
  );
}
