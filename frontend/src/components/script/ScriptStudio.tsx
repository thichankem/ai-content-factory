"use client";

import React, { useState, useEffect } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useScriptEngine } from "@/hooks/useScriptEngine";
import { useProjects } from "@/hooks/useProjects";
import { ScriptBriefSettings, SpeechPacingConfig, TargetScope, SectionHistoryEntry } from "@/types/studio";
import { ScriptPacingBar } from "@/components/script/ScriptPacingBar";
import { ScriptChatbot } from "@/components/script/ScriptChatbot";
import { ScriptBriefSettingsPanel, DEFAULT_BRIEF_SETTINGS } from "@/components/script/ScriptBriefSettingsPanel";
import { ScriptEditorView } from "@/components/script/ScriptEditorView";
import { ScriptSectionHistoryModal } from "@/components/script/ScriptSectionHistoryModal";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ViralityResult } from "@/types/qa";
import {
  Flame,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Loader2,
  BookOpen,
  SlidersHorizontal,
  FileText,
  ShieldCheck,
  PanelLeftClose,
  PanelLeftOpen,
  History,
} from "lucide-react";

export function ScriptStudio() {
  const { currentProject } = useProjectStore();
  const { viralityMutation } = useScriptEngine(currentProject?.id);
  const { approveScriptMutation, saveScriptMutation } = useProjects();

  // Navigation mode for the main work area (2 tabs: 10 Tiêu Chí & Kịch Bản)
  const [activeSubTab, setActiveSubTab] = useState<"brief" | "editor">("brief");

  // Briefing 10 dimensions state
  const [brief, setBrief] = useState<ScriptBriefSettings>(DEFAULT_BRIEF_SETTINGS);

  /*
   * The editor opens on the project's saved script, and on nothing at all when
   * there is none. It used to open on a ~1,100-character "cơm trắng" demo script
   * hardcoded in this file, which read as the project's own narration before
   * anything had been drafted — and which the operator could then approve.
   */
  const [scriptText, setScriptText] = useState(
    currentProject?.script_document?.raw_script ?? ""
  );

  /** Result of the last save / approval, and the last failure. */
  const [gateStatus, setGateStatus] = useState<string | null>(null);
  const [gateError, setGateError] = useState<string | null>(null);

  useEffect(() => {
    if (currentProject?.script_document?.raw_script) {
      setScriptText(currentProject.script_document.raw_script);
    }
  }, [currentProject?.script_document?.raw_script]);

  // Speech Pacing State (Default: 160 WPM - natural TTS pacing)
  const [pacingConfig, setPacingConfig] = useState<SpeechPacingConfig>({
    wpm: 160,
    label: "Chuẩn (160 WPM)",
    preset: "normal",
  });

  // Targeted Scope for Chatbot editing (default: full script)
  const [targetScope, setTargetScope] = useState<TargetScope>({
    type: "full",
    startLine: 1,
    endLine: 10,
    selectedText: "",
    wordCount: 0,
    estimatedSeconds: 0,
  });

  // Virality & AI status states
  const [viralityResult, setViralityResult] = useState<ViralityResult | null>(null);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);
  const [showChatbot, setShowChatbot] = useState(true);

  // Section History Tracking State
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyEntries, setHistoryEntries] = useState<SectionHistoryEntry[]>([
    {
      id: "h-init",
      sectionKey: "full",
      sectionLabel: "Toàn văn kịch bản",
      version: 1,
      text: currentProject?.script_document?.raw_script || "Bản thảo khởi tạo ban đầu",
      summary: "Khởi tạo kịch bản dự án",
      wordCount: (currentProject?.script_document?.raw_script || "").split(/\s+/).filter(Boolean).length,
      estimatedSeconds: (currentProject?.script_document?.raw_script || "").split(/\s+/).filter(Boolean).length / (160 / 60),
      author: "ai",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const handleSaveManualSnapshot = (note: string, sectionKey: string) => {
    setHistoryEntries((prev) => [
      {
        id: `h-${Date.now()}`,
        sectionKey: sectionKey || "full",
        sectionLabel: sectionKey === "full" ? "Toàn văn kịch bản" : `Phân đoạn [${sectionKey}]`,
        version: prev.length + 1,
        text: scriptText,
        summary: note || "Snapshot thủ công bởi Operator",
        wordCount: scriptText.split(/\s+/).filter(Boolean).length,
        estimatedSeconds: scriptText.split(/\s+/).filter(Boolean).length / (pacingConfig.wpm / 60),
        author: "snapshot",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
      ...prev,
    ]);
  };

  const handleRestoreHistoryEntry = (entry: SectionHistoryEntry) => {
    setScriptText(entry.text);
    setGateStatus(`Đã khôi phục kịch bản về phiên bản #${entry.version} (${entry.summary})`);
    setIsHistoryOpen(false);
  };

  // Generate complete script from the 10 briefing dimensions
  const handleGenerateFromBrief = async () => {
    setIsAiProcessing(true);
    setAiStatus(`AI Storyteller đang tổng hợp 10 tiêu chí để viết kịch bản cho: "${brief.topic}"...`);

    // Simulate structured prompt synthesis
    await new Promise((r) => setTimeout(r, 1400));

    const generatedScript = `[Hook // 00:00 - 00:03]
(Visual Cue: Quay cận cảnh góc máy sốc, xuất hiện text cảnh báo neon nhấp nháy, khung hình ${brief.aspectRatio})
${
  brief.hookType === "counter_intuitive"
    ? `Nếu bạn vẫn nghĩ ${brief.topic.toLowerCase()} là chuyện đơn giản, thì 90% bạn đang làm sai ngay từ bước đầu tiên!`
    : brief.hookType === "fatal_mistake"
    ? `Sai lầm chết người khi ${brief.topic.toLowerCase()} mà 99% mọi người đều mắc phải!`
    : `Dừng ngay việc làm này lại nếu bạn không muốn ${brief.audiencePainPoint.toLowerCase()}!`
}

[Bằng chứng & Thực tế // 00:03 - 00:20]
(Visual Cue: Đưa đồ họa số liệu thực tế: ${brief.specificFactsAndData.slice(0, 80)}..., nhạc nền chuyển nhịp kịch tính)
${brief.uniqueAngle}
Theo dữ liệu thực nghiệm: ${brief.specificFactsAndData.slice(0, 100)}...

[Giải pháp & Cú lật Turn // 00:20 - 00:45]
(Visual Cue: Format ${brief.formatType === "talking_head" ? "Creator nói trực diện camera với biểu cảm thuyết phục" : "Cinematic B-Roll chi tiết từng động tác thực hành"}, phong cách ${brief.benchmarkCreatorOrChannel})
${brief.includeMemeSlang ? `Bí kíp này ${brief.slangKeywords || "chuẩn đét"} mà ít ai tiết lộ: ` : "Giải pháp cốt lõi ở đây: "}
Đừng làm theo lối mòn sáo rỗng. Hãy tập trung giải quyết đúng vấn đề ${brief.audienceDesire.toLowerCase()} để đạt hiệu quả cao nhất.

[Payoff & CTA // 00:45 - 00:60]
(Visual Cue: Xuất hiện nút kêu gọi hành động đồ họa động theo chuẩn nền tảng ${brief.platform.toUpperCase()})
${brief.callToAction}`;

    setScriptText(generatedScript);
    setHistoryEntries((prev) => [
      {
        id: `h-${Date.now()}`,
        sectionKey: "full",
        sectionLabel: "Toàn văn kịch bản (10 Tiêu chí)",
        version: prev.length + 1,
        text: generatedScript,
        summary: `Tự sinh kịch bản từ 10 tiêu chí cho "${brief.topic}"`,
        wordCount: generatedScript.split(/\s+/).filter(Boolean).length,
        estimatedSeconds: generatedScript.split(/\s+/).filter(Boolean).length / (pacingConfig.wpm / 60),
        author: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
      ...prev,
    ]);
    setIsAiProcessing(false);
    setAiStatus(`Đã tạo xong kịch bản chuẩn cho nền tảng ${brief.platform.toUpperCase()} (${brief.targetDuration})!`);
    setActiveSubTab("editor");
  };

  const handleScoreVirality = async () => {
    try {
      const res = await viralityMutation.mutateAsync({
        script_text: scriptText,
        topic: brief.topic || currentProject?.topic || "Viral script retention",
      });
      setViralityResult(res);
    } catch (err) {
      console.error("Failed to calculate virality:", err);
    }
  };

  /**
   * Persist the editor's text to the server.
   *
   * No screen in the Next client used to save the script: the save mutation
   * existed but nothing called it, so Gate 1 was decided against a script the
   * backend had never received — and ``source_rights_confirmed`` could never
   * become true there. Saving is now an explicit, reportable action.
   */
  const handleSaveScript = async (sourceRightsConfirmed?: boolean) => {
    if (!currentProject) {
      setGateError("Chưa chọn dự án — không có gì để lưu.");
      return;
    }
    setGateError(null);
    try {
      await saveScriptMutation.mutateAsync({
        projectId: currentProject.id,
        script: scriptText,
        ...(sourceRightsConfirmed === undefined ? {} : { sourceRightsConfirmed }),
      });
      setGateStatus(
        sourceRightsConfirmed
          ? "Đã lưu kịch bản và ghi nhận xác nhận bản quyền nguồn tư liệu lên server."
          : "Đã lưu kịch bản lên server."
      );
    } catch (error) {
      setGateError(
        `Lưu kịch bản thất bại: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };

  /** Record the source-rights confirmation on the server, with the script. */
  const handleConfirmSourceRights = () => {
    if (currentProject?.source_rights_confirmed) return;
    void handleSaveScript(true);
  };

  const handleApproveGate1 = async () => {
    setGateError(null);
    if (!currentProject) {
      setGateError("Chưa chọn dự án để duyệt Gate 1.");
      return;
    }
    if (!currentProject.source_rights_confirmed) {
      // Stated in the page instead of an `alert()`, which the previous version
      // used here — and which the studio also used to announce approvals that
      // the server had rejected.
      setGateError(
        "Phải ghi nhận xác nhận bản quyền nguồn tư liệu (Source Rights) lên server trước khi duyệt Gate 1."
      );
      return;
    }
    try {
      await approveScriptMutation.mutateAsync(currentProject.id);
      setGateStatus("Gate 1 đã được duyệt trên server. Dự án chuyển sang bước 2.");
    } catch (error) {
      setGateError(
        `Duyệt Gate 1 thất bại: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };

  return (
    <div className="flex flex-col space-y-2.5 h-full min-h-0 font-sans">

      {/* Top Pacing Bar: Live Duration & Speed Rate Predictor */}
      <ScriptPacingBar
        scriptText={scriptText}
        targetDurationStr={brief.targetDuration}
        targetScope={targetScope}
        pacingConfig={pacingConfig}
        onPacingChange={setPacingConfig}
      />

      {/* Gate 1 outcome — shown, not alerted. The server's answer is the only one
          that counts, so a rejection has to be readable here. */}
      {gateError && (
        <div className="shrink-0 text-xs text-rose-300 bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/30 flex items-start">
          <AlertTriangle className="w-3.5 h-3.5 mr-1.5 shrink-0 mt-0.5" />
          <span>{gateError}</span>
        </div>
      )}
      {gateStatus && (
        <div className="shrink-0 text-xs text-emerald-300 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/30 flex items-start">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 shrink-0 mt-0.5" />
          <span>{gateStatus}</span>
        </div>
      )}

      {/* Navigation Sub-Tabs & View Controller */}
      <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl px-3 py-1.5 shrink-0">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setActiveSubTab("brief")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeSubTab === "brief"
                ? "bg-nle-cyan text-black shadow-sm font-bold"
                : "text-gray-400 hover:text-white hover:bg-nle-surface"
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>1. 10 Tiêu Chí</span>
          </button>

          <button
            onClick={() => setActiveSubTab("editor")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeSubTab === "editor"
                ? "bg-nle-cyan text-black shadow-sm font-bold"
                : "text-gray-400 hover:text-white hover:bg-nle-surface"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>2. Kịch Bản</span>
            {viralityResult && (
              <Badge variant="amber" className="text-[9px] py-0 px-1 ml-1">
                {viralityResult.score}đ
              </Badge>
            )}
          </button>
        </div>

        {/* AI Chatbot Toggle Button */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setShowChatbot(!showChatbot)}
            title={showChatbot ? "Thu nhỏ AI Chatbot" : "Mở AI Chatbot"}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs border transition-colors ${
              showChatbot
                ? "bg-nle-surface border-nle-cyan/40 text-nle-cyan font-semibold"
                : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
            }`}
          >
            {showChatbot ? (
              <>
                <PanelLeftClose className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Ẩn Chatbot</span>
              </>
            ) : (
              <>
                <PanelLeftOpen className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Mở Chatbot</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* MAIN WORKSPACE: LEFT AI CHATBOT COPILOT + RIGHT SINGLE-COLUMN WORKSPACE  */}
      {/* ========================================================================= */}
      <div className="flex-1 flex space-x-3 min-h-0 overflow-hidden">
        {/* Left Side: ALWAYS-PRESENT AI CHATBOT (Tự sinh kịch bản & sửa theo dòng) */}
        {showChatbot && (
          <div className="w-[320px] xl:w-[350px] shrink-0 h-full min-h-0 flex flex-col">
            <ScriptChatbot
              scriptText={scriptText}
              onScriptTextChange={setScriptText}
              targetScope={targetScope}
              onTargetScopeChange={setTargetScope}
              pacingConfig={pacingConfig}
              brief={brief}
            />
          </div>
        )}

        {/* Right Side / Center: Single Column Studio Area */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* TAB 1: 10 Dimensions Settings (Single-Column) */}
          {activeSubTab === "brief" && (
            <div className="flex-1 min-h-0 overflow-hidden">
              <ScriptBriefSettingsPanel
                brief={brief}
                onBriefChange={setBrief}
                onGenerateScript={handleGenerateFromBrief}
                isProcessing={isAiProcessing}
              />
            </div>
          )}

          {/* TAB 2: Script Editor with Line Numbers (Single-Column) */}
          {activeSubTab === "editor" && (
            <div className="flex-1 min-h-0 overflow-hidden">
              <ScriptEditorView
                scriptText={scriptText}
                onScriptTextChange={setScriptText}
                targetScope={targetScope}
                onTargetScopeChange={setTargetScope}
                pacingConfig={pacingConfig}
                sourceRightsConfirmed={currentProject?.source_rights_confirmed || false}
                onConfirmSourceRights={handleConfirmSourceRights}
                onSaveScript={() => void handleSaveScript()}
                isSaving={saveScriptMutation.isPending}
                onApproveGate1={handleApproveGate1}
                isApproving={approveScriptMutation.isPending}
                onScoreVirality={handleScoreVirality}
                viralityResult={viralityResult}
                isScoringVirality={viralityMutation.isPending}
                onOpenHistory={() => setIsHistoryOpen(true)}
                historyCount={historyEntries.length}
                topic={brief.topic}
                platform={brief.platform}
                targetDuration={brief.targetDuration}
              />
            </div>
          )}
        </div>
      </div>

      {/* Script Section History Modal */}
      <ScriptSectionHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        historyEntries={historyEntries}
        onRestoreEntry={handleRestoreHistoryEntry}
        onSaveManualSnapshot={handleSaveManualSnapshot}
        onClearHistory={() => setHistoryEntries([])}
        onDeleteEntry={(id) => setHistoryEntries((prev) => prev.filter((e) => e.id !== id))}
      />
    </div>
  );
}
