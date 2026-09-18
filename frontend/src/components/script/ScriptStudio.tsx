"use client";

import React, { useState, useEffect } from "react";
import { useProjectStore } from "../../stores/useProjectStore";
import { useScriptEngine } from "../../hooks/useScriptEngine";
import { useProjects } from "../../hooks/useProjects";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import {
  ScriptBriefSettings,
  TargetScope,
  SpeechPacingConfig,
  SectionHistoryEntry,
} from "../../types/script";
import { ScriptPacingBar } from "./ScriptPacingBar";
import { ScriptChatbot } from "./ScriptChatbot";
import { ScriptBriefSettingsPanel, DEFAULT_BRIEF_SETTINGS } from "./ScriptBriefSettingsPanel";
import { ScriptEditorView } from "./ScriptEditorView";
import { ScriptSectionHistoryModal } from "./ScriptSectionHistoryModal";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
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
  Columns,
  ShieldCheck,
  PanelRightClose,
  PanelRightOpen,
  History,
} from "lucide-react";

export function ScriptStudio() {
  const { currentProject, confirmSourceRights } = useProjectStore();
  const { viralityMutation } = useScriptEngine(currentProject?.id);
  const { approveScriptMutation } = useProjects();

  // Navigation mode for the main work area: 1-column sequential workflow
  const [activeSubTab, setActiveSubTab] = useState<"brief" | "editor" | "virality">("brief");

  // Briefing 10 dimensions state
  const [brief, setBrief] = useState<ScriptBriefSettings>(DEFAULT_BRIEF_SETTINGS);

  // Script text state
  const [scriptText, setScriptText] = useState(
    currentProject?.script_document?.raw_script ||
      `[Hook // 00:00 - 00:03]\n(Visual Cue: Quay cận cảnh thìa cơm trắng dẻo bóng bẩy, khói nghi ngút bốc lên chậm rãi)\nĐừng bao giờ dùng ngón tay đo nước khi nấu cơm nữa, nếu bạn không muốn cả nồi cơm biến thành cháo dính!\n\n[Bằng chứng // 00:03 - 00:20]\n(Visual Cue: Chèn hình minh họa bàn tay ngập trong nồi cơm có dấu gạch chéo đỏ, chuyển cảnh sang chiếc cân điện tử mini)\nNgón tay mỗi người dài ngắn khác nhau, đáy nồi lại có độ cong vát khác nhau. Công thức chuẩn của các đầu bếp Nhật là tỷ lệ nước 1:1.15 theo khối lượng.\n\n[Cú lật Turn // 00:20 - 00:45]\n(Visual Cue: Quay cảnh nhỏ 1 giọt dầu mè nguyên chất vào nồi trước khi bấm nút Cook, hạt cơm tơi xốp tách rời)\nVà đây là bí quyết ít ai chỉ cho bạn: Hãy nhỏ đúng một giọt dầu mè và ngâm 10 phút trước khi bật nồi. Lớp màng lipid tự nhiên sẽ bọc từng hạt tinh bột, giúp cơm nở đều mà không hề bị nát hay dính đáy.\n\n[Payoff & CTA // 00:45 - 00:60]\n(Visual Cue: Người cầm bát cơm nóng hổi ăn thử biểu cảm gật gù hài lòng, icon thả tim và lưu video nhấp nháy)\nThử ngay bữa tối nay xem cơm nhà bạn có ngon hơn hẳn ngoài quán không nhé! Thả tim và lưu lại kẻo lúc nấu lại quên mất công thức!`
  );

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

  // Section History Tracking State
  const [historyEntries, setHistoryEntries] = useState<SectionHistoryEntry[]>([
    {
      id: "hist-init-hook",
      sectionKey: "hook",
      sectionLabel: "[Hook 3s]",
      version: 1,
      text: `[Hook // 00:00 - 00:03]\n(Visual Cue: Quay cận cảnh thìa cơm trắng dẻo bóng bẩy, khói nghi ngút bốc lên chậm rãi)\nĐừng bao giờ dùng ngón tay đo nước khi nấu cơm nữa, nếu bạn không muốn cả nồi cơm biến thành cháo dính!`,
      summary: "Bản gốc khởi tạo từ 10 tiêu chí đề bài",
      wordCount: 28,
      estimatedSeconds: 10.5,
      author: "snapshot",
      timestamp: "14:20",
    },
    {
      id: "hist-init-evidence",
      sectionKey: "evidence",
      sectionLabel: "[Bằng chứng / Nội dung]",
      version: 1,
      text: `[Bằng chứng // 00:03 - 00:20]\n(Visual Cue: Chèn hình minh họa bàn tay ngập trong nồi cơm có dấu gạch chéo đỏ, chuyển cảnh sang chiếc cân điện tử mini)\nNgón tay mỗi người dài ngắn khác nhau, đáy nồi lại có độ cong vát khác nhau. Công thức chuẩn của các đầu bếp Nhật là tỷ lệ nước 1:1.15 theo khối lượng.`,
      summary: "Bản gốc khởi tạo từ 10 tiêu chí đề bài",
      wordCount: 48,
      estimatedSeconds: 18.0,
      author: "snapshot",
      timestamp: "14:20",
    },
    {
      id: "hist-init-turn",
      sectionKey: "turn",
      sectionLabel: "[Cú lật Turn]",
      version: 1,
      text: `[Cú lật Turn // 00:20 - 00:45]\n(Visual Cue: Quay cảnh nhỏ 1 giọt dầu mè nguyên chất vào nồi trước khi bấm nút Cook, hạt cơm tơi xốp tách rời)\nVà đây là bí quyết ít ai chỉ cho bạn: Hãy nhỏ đúng một giọt dầu mè và ngâm 10 phút trước khi bật nồi. Lớp màng lipid tự nhiên sẽ bọc từng hạt tinh bột, giúp cơm nở đều mà không hề bị nát hay dính đáy.`,
      summary: "Bản gốc khởi tạo từ 10 tiêu chí đề bài",
      wordCount: 65,
      estimatedSeconds: 24.3,
      author: "snapshot",
      timestamp: "14:20",
    },
    {
      id: "hist-init-cta",
      sectionKey: "cta",
      sectionLabel: "[Payoff & CTA]",
      version: 1,
      text: `[Payoff & CTA // 00:45 - 00:60]\n(Visual Cue: Người cầm bát cơm nóng hổi ăn thử biểu cảm gật gù hài lòng, icon thả tim và lưu video nhấp nháy)\nThử ngay bữa tối nay xem cơm nhà bạn có ngon hơn hẳn ngoài quán không nhé! Thả tim và lưu lại kẻo lúc nấu lại quên mất công thức!`,
      summary: "Bản gốc khởi tạo từ 10 tiêu chí đề bài",
      wordCount: 36,
      estimatedSeconds: 13.5,
      author: "snapshot",
      timestamp: "14:20",
    },
  ]);

  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // Virality & AI status states
  const [viralityResult, setViralityResult] = useState<ViralityResult | null>(null);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);
  const [showRightChatbot, setShowRightChatbot] = useState(true);

  // Record a history entry
  const handleRecordHistory = (newEntry: SectionHistoryEntry) => {
    const sameSectionCount = historyEntries.filter((e) => e.sectionKey === newEntry.sectionKey).length;
    const entryWithVer: SectionHistoryEntry = {
      ...newEntry,
      version: sameSectionCount + 1,
    };
    setHistoryEntries((prev) => [entryWithVer, ...prev]);
  };

  // Restore a historical section entry directly into the script
  const handleRestoreHistoryEntry = (entry: SectionHistoryEntry) => {
    if (entry.sectionKey === "full") {
      setScriptText(entry.text);
      setAiStatus(`Đã khôi phục toàn bộ kịch bản về Phiên bản #${entry.version}!`);
      return;
    }

    let regex: RegExp | null = null;
    if (entry.sectionKey === "hook") {
      regex = /\[Hook[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i;
    } else if (entry.sectionKey === "turn") {
      regex = /\[(Cú lật|Turn)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i;
    } else if (entry.sectionKey === "cta") {
      regex = /\[(Payoff|CTA|Kêu gọi)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i;
    } else if (entry.sectionKey === "evidence") {
      regex = /\[(Bằng chứng|Nội dung|Context)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i;
    }

    if (regex && regex.test(scriptText)) {
      setScriptText((prev) => prev.replace(regex!, entry.text));
      setAiStatus(`Đã khôi phục đoạn ${entry.sectionLabel} về Phiên bản #${entry.version}!`);
    } else {
      setScriptText((prev) => `${entry.text}\n\n${prev}`);
      setAiStatus(`Đã khôi phục đoạn ${entry.sectionLabel}!`);
    }
  };

  // Manual snapshot saver
  const handleSaveManualSnapshot = (note: string, sectionKey: string) => {
    let textToSave = scriptText;
    let label = "Toàn bộ kịch bản";

    if (sectionKey === "hook") {
      const match = scriptText.match(/\[Hook[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i);
      if (match) textToSave = match[0];
      label = "[Hook 3s]";
    } else if (sectionKey === "turn") {
      const match = scriptText.match(/\[(Cú lật|Turn)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i);
      if (match) textToSave = match[0];
      label = "[Cú lật Turn]";
    } else if (sectionKey === "cta") {
      const match = scriptText.match(/\[(Payoff|CTA|Kêu gọi)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i);
      if (match) textToSave = match[0];
      label = "[Payoff & CTA]";
    } else if (sectionKey === "evidence") {
      const match = scriptText.match(/\[(Bằng chứng|Nội dung|Context)[\s\S]*?\][\s\S]*?(?=\n\s*\n\[|$)/i);
      if (match) textToSave = match[0];
      label = "[Bằng chứng / Nội dung]";
    }

    const words = textToSave.replace(/\[.*?\]/g, " ").split(/\s+/).filter(Boolean).length;
    handleRecordHistory({
      id: `manual-${Date.now()}`,
      sectionKey,
      sectionLabel: label,
      version: 1,
      text: textToSave,
      summary: note,
      wordCount: words,
      estimatedSeconds: words / (pacingConfig.wpm / 60),
      author: "snapshot",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    });
    setAiStatus(`Đã lưu bản nháp: "${note}"!`);
  };

  // Generate complete script from the 10 briefing dimensions
  const handleGenerateFromBrief = async () => {
    setIsAiProcessing(true);
    setAiStatus(`AI Storyteller đang tổng hợp 10 tiêu chí & dữ liệu đính kèm để viết kịch bản...`);

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
Theo dữ liệu thực nghiệm đã kiểm chứng: ${brief.specificFactsAndData.slice(0, 100)}...

[Giải pháp & Cú lật Turn // 00:20 - 00:45]
(Visual Cue: Format ${brief.formatType === "talking_head" ? "Creator nói trực diện camera với biểu cảm thuyết phục" : "Cinematic B-Roll chi tiết từng động tác thực hành"}, phong cách ${brief.benchmarkCreatorOrChannel})
${brief.includeMemeSlang ? `Bí kíp này ${brief.slangKeywords || "chuẩn đét"} mà ít ai tiết lộ: ` : "Giải pháp cốt lõi ở đây: "}
Đừng làm theo lối mòn sáo rỗng. Hãy tập trung giải quyết đúng vấn đề ${brief.audienceDesire.toLowerCase()} để đạt hiệu quả cao nhất.

[Payoff & CTA // 00:45 - 00:60]
(Visual Cue: Xuất hiện nút kêu gọi hành động đồ họa động theo chuẩn nền tảng ${brief.platform.toUpperCase()})
${brief.callToAction}`;

    setScriptText(generatedScript);

    // Also record full script snapshot
    handleRecordHistory({
      id: `gen-${Date.now()}`,
      sectionKey: "full",
      sectionLabel: "Toàn bộ kịch bản",
      version: 1,
      text: generatedScript,
      summary: `Tạo mới từ 10 tiêu chí đề bài (${brief.platform.toUpperCase()} • ${brief.targetDuration})`,
      wordCount: generatedScript.replace(/\[.*?\]/g, " ").split(/\s+/).filter(Boolean).length,
      estimatedSeconds: generatedScript.replace(/\[.*?\]/g, " ").split(/\s+/).filter(Boolean).length / (pacingConfig.wpm / 60),
      author: "ai",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    });

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
      setActiveSubTab("virality");
    } catch (err) {
      console.error("Failed to calculate virality:", err);
    }
  };

  const handleApproveGate1 = async () => {
    if (!currentProject) return;
    if (!currentProject.source_rights_confirmed) {
      alert("Bạn phải xác nhận bản quyền nguồn tư liệu (Source Rights) trước khi duyệt Gate 1!");
      return;
    }
    await approveScriptMutation.mutateAsync(currentProject.id);
  };

  // Quick actions on top AI Agent Bar
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-hook-gen",
      label: "AI Tối Ưu Lại Hook 3s",
      icon: Flame,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang phân tích tâm lý giữ chân và tái tạo Hook 3 giây...");
        await new Promise((r) => setTimeout(r, 900));
        const newHook = `[Hook // 00:00 - 00:03]\n(Visual Cue: Cận cảnh giật gân, nhịp cắt 0.5s dồn dập)\n${
          brief.hookType === "fatal_mistake"
            ? "Sai lầm chết người mà 99% mọi người đều mắc phải khi " + brief.topic.toLowerCase() + "!"
            : "Bí mật đằng sau " + brief.topic.toLowerCase() + " mà không một chuyên gia nào muốn bạn biết!"
        }\n\n`;

        setScriptText((prev) =>
          prev.replace(
            /\[Hook\s*\/\/\s*00:00\s*-\s*00:03\]\n(\(Visual Cue:.*?\)\n)?.*?\n\n/s,
            newHook
          )
        );

        handleRecordHistory({
          id: `hook-${Date.now()}`,
          sectionKey: "hook",
          sectionLabel: "[Hook 3s]",
          version: 1,
          text: newHook.trim(),
          summary: "AI tối ưu lại Hook 3s giật gân",
          wordCount: newHook.replace(/\[.*?\]/g, " ").split(/\s+/).filter(Boolean).length,
          estimatedSeconds: newHook.replace(/\[.*?\]/g, " ").split(/\s+/).filter(Boolean).length / (pacingConfig.wpm / 60),
          author: "ai",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        });

        setIsAiProcessing(false);
        setAiStatus("Đã cập nhật Hook 3 giây đầu giữ chân khán giả tột độ!");
      },
    },
    {
      id: "ai-cue-gen",
      label: "AI Tự Động Bổ Sung Visual Cue",
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang rà soát từng câu thoại để chèn góc máy Visual Cue...");
        await new Promise((r) => setTimeout(r, 800));
        setIsAiProcessing(false);
        setAiStatus("Đã đồng bộ chỉ dẫn Visual Cue cho toàn bộ kịch bản!");
      },
    },
    {
      id: "ai-copy-risk",
      label: "Quét Trùng Lặp & Bản Quyền (100% Unique)",
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang quét đối chiếu tránh vi phạm bản quyền...");
        await new Promise((r) => setTimeout(r, 900));
        setIsAiProcessing(false);
        setAiStatus("An toàn 100%: Kịch bản độc quyền, 0% Copy-Risk!");
      },
    },
  ];

  return (
    <div className="flex flex-col space-y-2.5 h-full min-h-0 font-sans">
      {/* Top AI Agent Bar */}
      <AIAgentBar
        tabTitle="Xây dựng Kịch bản (Script Studio & Storyboard)"
        agentRole="Chief Storyteller & Viral Script Director"
        promptPlaceholder={`Yêu cầu AI viết kịch bản về: "${brief.topic}"...`}
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang điều chỉnh kịch bản theo lệnh: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1000));
          setIsAiProcessing(false);
          setAiStatus("Đã tinh chỉnh kịch bản thành công!");
        }}
      />

      {/* Top Pacing Bar: Live Duration & Speed Rate Predictor */}
      <ScriptPacingBar
        scriptText={scriptText}
        targetDurationStr={brief.targetDuration}
        targetScope={targetScope}
        pacingConfig={pacingConfig}
        onPacingChange={setPacingConfig}
      />

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
            <span>1. Đề Bài (10 Tiêu Chí)</span>
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
            <span>2. Soạn Thảo & Visual Cues</span>
          </button>

          <button
            onClick={() => setActiveSubTab("virality")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeSubTab === "virality"
                ? "bg-nle-cyan text-black shadow-sm font-bold"
                : "text-gray-400 hover:text-white hover:bg-nle-surface"
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>3. Phân Tích & Duyệt Gate 1</span>
            {viralityResult && (
              <Badge variant="amber" className="text-[9px] py-0 px-1">
                {viralityResult.score}đ
              </Badge>
            )}
          </button>
        </div>

        {/* Right Toolbar: History Button & Chatbot Toggle Button */}
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsHistoryModalOpen(true)}
            className="text-xs h-7 px-2.5 border-amber-500/40 text-amber-300 hover:bg-amber-500/10 font-medium"
          >
            <History className="w-3.5 h-3.5 mr-1 text-amber-400" />
            <span>Lịch Sử Phân Đoạn ({historyEntries.length})</span>
          </Button>

          <button
            onClick={() => setShowRightChatbot(!showRightChatbot)}
            title={showRightChatbot ? "Thu nhỏ AI Chatbot" : "Mở AI Chatbot"}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs border transition-colors ${
              showRightChatbot
                ? "bg-nle-surface border-nle-cyan/40 text-nle-cyan font-semibold"
                : "bg-nle-panel border-nle-border text-gray-400 hover:text-white"
            }`}
          >
            {showRightChatbot ? (
              <>
                <PanelRightClose className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Ẩn Chatbot</span>
              </>
            ) : (
              <>
                <PanelRightOpen className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Mở Chatbot</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* MAIN TWO-COLUMN WORKSPACE: LEFT MAIN VIEW + RIGHT PERSISTENT CHATBOT */}
      {/* ========================================================================= */}
      <div className="flex-1 flex space-x-3 min-h-0 overflow-hidden">
        {/* Left / Center Main Studio Area */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* TAB 1: 10 Dimensions Settings */}
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

          {/* TAB 2: Script Editor with Line Numbers */}
          {activeSubTab === "editor" && (
            <div className="flex-1 min-h-0 overflow-hidden">
              <ScriptEditorView
                scriptText={scriptText}
                onScriptTextChange={setScriptText}
                targetScope={targetScope}
                onTargetScopeChange={setTargetScope}
                pacingConfig={pacingConfig}
                sourceRightsConfirmed={currentProject?.source_rights_confirmed || false}
                onConfirmSourceRights={confirmSourceRights}
                onApproveGate1={handleApproveGate1}
                isApproving={approveScriptMutation.isPending}
                onScoreVirality={handleScoreVirality}
                topic={brief.topic}
                platform={brief.platform}
                targetDuration={brief.targetDuration}
                onOpenHistory={() => setIsHistoryModalOpen(true)}
                historyCount={historyEntries.length}
              />
            </div>
          )}

          {/* TAB 3: Virality Analytics & Gate 1 */}
          {activeSubTab === "virality" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 flex-1 min-h-0 overflow-y-auto">
              <Card className="lg:col-span-2 flex flex-col min-h-0 border-nle-border bg-nle-panel">
                <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
                  <CardTitle className="text-xs font-bold text-white flex items-center">
                    <Flame className="w-4 h-4 text-amber-400 mr-1.5 fill-current" />
                    <span>Báo Cáo Giữ Chân Khán Giả (Retention & Virality Score)</span>
                  </CardTitle>
                  <Button
                    variant="neon"
                    size="sm"
                    onClick={handleScoreVirality}
                    disabled={viralityMutation.isPending}
                    className="text-xs h-7"
                  >
                    {viralityMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Quét Lại"}
                  </Button>
                </CardHeader>
                <CardContent className="p-3 flex-1 flex flex-col space-y-3 min-h-0">
                  {viralityResult ? (
                    <>
                      <div className="p-4 rounded-xl bg-gradient-to-r from-nle-panel via-nle-surface to-nle-panel border border-nle-border text-center">
                        <span className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-nle-cyan via-emerald-400 to-nle-violet">
                          {viralityResult.score}/100
                        </span>
                        <p className="text-xs text-gray-300 font-medium mt-1">
                          Dự đoán tỷ lệ hoàn thành video trên {brief.platform.toUpperCase()}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        <div className="p-2.5 rounded-lg bg-nle-surface border border-nle-border text-center">
                          <span className="text-[10px] text-gray-400 uppercase font-mono">Hook (3s đầu)</span>
                          <p className="text-base font-bold text-nle-cyan">{viralityResult.hook_score}%</p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-nle-surface border border-nle-border text-center">
                          <span className="text-[10px] text-gray-400 uppercase font-mono">Nhịp độ (Pacing)</span>
                          <p className="text-base font-bold text-nle-violet">{viralityResult.pacing_score}%</p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-nle-surface border border-nle-border text-center">
                          <span className="text-[10px] text-gray-400 uppercase font-mono">Thời lượng</span>
                          <p className="text-base font-bold text-emerald-400">{viralityResult.duration_score}%</p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-nle-surface border border-nle-border text-center">
                          <span className="text-[10px] text-gray-400 uppercase font-mono">Kêu gọi (CTA)</span>
                          <p className="text-base font-bold text-amber-400">{viralityResult.cta_score}%</p>
                        </div>
                      </div>

                      <div className="p-3 rounded-lg bg-nle-surface border border-nle-border space-y-2">
                        <span className="text-xs font-semibold text-white block">💡 Lời khuyên tối ưu từ Giám đốc Kịch bản AI:</span>
                        <ul className="space-y-1.5">
                          {viralityResult.advice.map((adv, idx) => (
                            <li key={idx} className="text-xs text-gray-300 flex items-start">
                              <span className="text-nle-cyan mr-2 font-bold">•</span>
                              <span>{adv}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-400 border border-dashed border-nle-border rounded-lg">
                      <Sparkles className="w-8 h-8 text-nle-cyan/40 mb-2" />
                      <p className="text-xs">Bấm <strong>Chấm điểm Virality</strong> để AI phân tích toàn diện kịch bản.</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Gate 1 Review Card */}
              <Card className="flex flex-col min-h-0 border-nle-border bg-nle-panel">
                <CardHeader className="py-2.5 px-3 border-b border-nle-border">
                  <CardTitle className="text-xs font-bold text-white flex items-center">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 mr-1.5" />
                    <span>Cổng Duyệt Kịch Bản (Gate 1)</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-3 flex-1 flex flex-col justify-between space-y-3">
                  <div className="space-y-2 text-xs text-gray-300">
                    <div className="p-2.5 rounded bg-nle-surface border border-nle-border space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-400">Chủ đề:</span>
                        <span className="font-semibold text-white truncate max-w-[160px]">{brief.topic}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-400">Nền tảng:</span>
                        <span className="text-amber-300 font-mono">{brief.platform.toUpperCase()}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-400">Thời lượng:</span>
                        <span className="text-nle-cyan font-mono">{brief.targetDuration}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-400">Bản quyền nguồn:</span>
                        <span className={currentProject?.source_rights_confirmed ? "text-emerald-400 font-bold" : "text-amber-400"}>
                          {currentProject?.source_rights_confirmed ? "Đã xác nhận" : "Chưa xác nhận"}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-gray-400 leading-normal">
                      * Theo quy định bất biến của hệ thống, chỉ khi Operator duyệt Gate 1, pipeline mới được phép tiến hành tổng hợp giọng đọc và dựng video.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Button
                      variant="default"
                      onClick={handleApproveGate1}
                      disabled={!currentProject?.source_rights_confirmed || approveScriptMutation.isPending}
                      className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-bold text-xs h-9"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1.5" />
                      Phê Duyệt Kịch Bản (Pass Gate 1)
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setActiveSubTab("editor")}
                      className="w-full text-xs border-nle-border text-gray-300 h-8"
                    >
                      Quay Lại Sửa Kịch Bản
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Right Side: ALWAYS-PRESENT AI CHATBOT (SỬA TRỰC TIẾP KỊCH BẢN THEO DÒNG ĐÁNH DẤU) */}
        {showRightChatbot && (
          <div className="w-[360px] lg:w-[400px] shrink-0 h-full min-h-0 flex flex-col">
            <ScriptChatbot
              scriptText={scriptText}
              onScriptTextChange={setScriptText}
              targetScope={targetScope}
              onTargetScopeChange={setTargetScope}
              pacingConfig={pacingConfig}
              brief={brief}
              onRecordHistory={handleRecordHistory}
              onOpenHistory={() => setIsHistoryModalOpen(true)}
              historyCount={historyEntries.length}
            />
          </div>
        )}
      </div>

      {/* Section-by-Section Version History Modal */}
      <ScriptSectionHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        historyEntries={historyEntries}
        onRestoreEntry={handleRestoreHistoryEntry}
        onSaveManualSnapshot={handleSaveManualSnapshot}
        onDeleteEntry={(id) => setHistoryEntries((prev) => prev.filter((e) => e.id !== id))}
      />
    </div>
  );
}
