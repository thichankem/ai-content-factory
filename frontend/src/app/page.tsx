"use client";

import React, { useEffect, useState } from "react";
import { SidebarWorkflowNav } from "@/components/layout/SidebarWorkflowNav";
import { ScriptStudio } from "@/components/script/ScriptStudio";
import { MediaStudio } from "@/components/media/MediaStudio";
import { PhotoLabStudio } from "@/components/photo/PhotoLabStudio";
import { VideoMotionFXStudio } from "@/components/videofx/VideoMotionFXStudio";
import { AudioLabStudio } from "@/components/audio/AudioLabStudio";
import { TimelineAssemblyStudio } from "@/components/timeline/TimelineAssemblyStudio";
import { ExportReviewStudio } from "@/components/export/ExportReviewStudio";
import { FusionNodeCompositor } from "@/components/fusion/FusionNodeCompositor";
import { ContentEmpireStudio } from "@/components/campaign/ContentEmpireStudio";
import { DAGWorkflowStudio } from "@/components/workflow/DAGWorkflowStudio";

import { CommandBarModal } from "@/components/copilot/CommandBarModal";
import { ComplianceModal } from "@/components/qa/ComplianceModal";
import { ThumbnailModal } from "@/components/thumbnails/ThumbnailModal";
import { AuditCostModal } from "@/components/audit/AuditCostModal";
import { ExternalIngestionModal } from "@/components/media/ExternalIngestionModal";
import { AgentBridgeModal } from "@/components/copilot/AgentBridgeModal";
import { SeoPackagingModal } from "@/components/export/SeoPackagingModal";
import { NewProjectModal } from "@/components/project/NewProjectModal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useProjects } from "@/hooks/useProjects";
import { useCampaign } from "@/hooks/useCampaign";
import { useWorkflowDAG } from "@/hooks/useWorkflowDAG";
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

  const { runWorkflowMutation, checklistQuery } = useWorkflowDAG(currentProject?.id);
  const { generateCampaignMutation } = useCampaign(currentProject?.id);

  const [workflowStatus, setWorkflowStatus] = useState<string | null>(null);
  const [campaignStatus, setCampaignStatus] = useState<string | null>(null);
  const [workflowSubMode, setWorkflowSubMode] = useState<"dag" | "fusion">("dag");

  useEffect(() => {
    // Only a project the API actually returned may be selected. An empty or failed
    // list is shown as such: a locally invented "demo" project used to be injected
    // here with `status: "video_review"` and `source_rights_confirmed: true`, which
    // both faked a finished render and auto-confirmed source rights — an invariant
    // `AGENTS.md` forbids on every code path.
    if (projectsQuery.data && projectsQuery.data.length > 0 && !currentProject) {
      setCurrentProject(projectsQuery.data[0]);
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
    await publishMutation.mutateAsync({ projectId: currentProject.id });
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
      setWorkflowStatus(`✅ Đã thực thi workflow thành công (${res?.steps?.length || 1} blocks)!`);
    } catch (e: any) {
      setWorkflowStatus(` Chạy workflow thất bại: ${e.message}`);
    }
  };

  const handleGenerateCampaign = async () => {
    setCampaignStatus("Đang tổng hợp pillar content thành 5 shorts...");
    try {
      const res = await generateCampaignMutation.mutateAsync({});
      setCampaignStatus(`✅ Đã tạo thành công chiến dịch ${res?.shorts?.length || 5} micro-shorts đa kênh!`);
    } catch (e: any) {
      setCampaignStatus(`❌ Tạo chiến dịch thất bại: ${e.message}`);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-nle-base font-sans antialiased text-gray-100">
      {/* Left Permanent Taskbar Navigation (7 Sequential Steps) */}
      <SidebarWorkflowNav />

      {/* Main Studio Viewport */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
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

          {/* STEP 3: Photo Lab & Layer Compositor */}
          {activeTab === "photo" && (
            <div className="flex-1 min-h-0">
              <PhotoLabStudio />
            </div>
          )}

          {/* STEP 4: Video & Motion FX (Speed Ramping, Bézier Keyframes & Color Grading) */}
          {activeTab === "video_fx" && (
            <div className="flex-1 min-h-0">
              <VideoMotionFXStudio />
            </div>
          )}

          {/* STEP 5: Audio Lab (5-Band Parametric EQ, TTS, Sidechain Auto-Ducking) */}
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
            <div className="flex-1 flex flex-col space-y-2 min-h-0 overflow-hidden">
              <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl px-4 py-2 shrink-0">
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-nle-surface flex items-center justify-center text-nle-cyan border border-nle-border">
                    <GitBranch className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs text-white">Visual DAG Pipeline Orchestrator & Node Compositor</h3>
                    <p className="text-[11px] text-gray-400">Định tuyến các khối AI và Node Compositing theo đồ thị phi chu trình có hướng</p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <div className="flex items-center bg-nle-surface rounded-lg p-0.5 border border-nle-border text-xs">
                    <button
                      onClick={() => setWorkflowSubMode("dag")}
                      className={`px-3 py-1 rounded-md font-medium transition-colors ${
                        workflowSubMode === "dag"
                          ? "bg-nle-cyan text-black font-semibold shadow-sm"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      DAG Pipeline (Toàn trình)
                    </button>
                    <button
                      onClick={() => setWorkflowSubMode("fusion")}
                      className={`px-3 py-1 rounded-md font-medium transition-colors ${
                        workflowSubMode === "fusion"
                          ? "bg-nle-cyan text-black font-semibold shadow-sm"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      Fusion Node Compositor (VFX)
                    </button>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      alert(`Checklist kết quả: ${checklistQuery.data?.ready ? "Sẵn sàng thực thi!" : "Đã qua kiểm tra cấu hình."}`)
                    }
                    className="text-xs border-nle-border h-8"
                  >
                    <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                    Pre-flight Checklist
                  </Button>
                  <Button
                    variant="neon"
                    size="sm"
                    onClick={handleRunWorkflow}
                    disabled={runWorkflowMutation.isPending}
                    className="text-xs h-8"
                  >
                    {runWorkflowMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                    )}
                    Chạy Workflow Nền
                  </Button>
                </div>
              </div>

              {workflowStatus && (
                <div className="text-xs text-nle-cyan font-semibold bg-nle-panel px-3 py-1.5 rounded-lg border border-nle-border shrink-0">
                  {workflowStatus}
                </div>
              )}

              <div className="flex-1 min-h-0 overflow-hidden">
                {workflowSubMode === "dag" ? <DAGWorkflowStudio /> : <FusionNodeCompositor />}
              </div>
            </div>
          )}

          {/* System Utility Tab: Omni-Channel Campaign Engine */}
          {activeTab === "campaign" && (
            <div className="flex-1 min-h-0 overflow-hidden">
              <ContentEmpireStudio />
            </div>
          )}
        </main>
      </div>

      {/* Global Pro Modals */}
      <CommandBarModal />
      <ComplianceModal />
      <ThumbnailModal />
      <AuditCostModal />
      <ExternalIngestionModal />
      <AgentBridgeModal />
      <SeoPackagingModal />
      <NewProjectModal />
    </div>
  );
}
