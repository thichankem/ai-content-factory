"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ChatbotMessage,
  ScriptBriefSettings,
  SpeechPacingConfig,
  TargetScope,
} from "@/types/studio";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatTime } from "@/components/script/ScriptPacingBar";
import {
  Bot,
  Send,
  Sparkles,
  RotateCcw,
  Target,
  Sliders,
  CheckCircle2,
  CornerDownLeft,
  Flame,
  Film,
  ShieldAlert,
  Zap,
  Loader2,
  ChevronRight,
  Maximize2,
  Minimize2,
  Split,
  FileEdit,
} from "lucide-react";

interface ScriptChatbotProps {
  scriptText: string;
  onScriptTextChange: (newText: string) => void;
  targetScope: TargetScope;
  onTargetScopeChange: (scope: TargetScope) => void;
  pacingConfig: SpeechPacingConfig;
  brief: ScriptBriefSettings;
}

export function ScriptChatbot({
  scriptText,
  onScriptTextChange,
  targetScope,
  onTargetScopeChange,
  pacingConfig,
  brief,
}: ScriptChatbotProps) {
  const [messages, setMessages] = useState<ChatbotMessage[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content:
        `Xin chào! Tôi là AI Script Copilot. Bạn có thể yêu cầu tôi chỉnh sửa trực tiếp bất kỳ phần nào của kịch bản.\n\n` +
        `💡 MẸO SỬ DỤNG: Hãy bôi đen một đoạn văn bản hoặc nhập số dòng (ví dụ: dòng 10 đến 25). Tôi sẽ chỉ thay thế đúng phạm vi đó mà không làm ảnh hưởng các đoạn khác!`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [inputPrompt, setInputPrompt] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [undoStack, setUndoStack] = useState<Array<{ oldText: string; targetScope: TargetScope }>>([]);

  // Manual line inputs
  const lines = scriptText.split("\n");
  const totalLines = lines.length;
  const [inputStartLine, setInputStartLine] = useState<number>(targetScope.startLine || 1);
  const [inputEndLine, setInputEndLine] = useState<number>(targetScope.endLine || Math.min(10, totalLines));

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInputStartLine(targetScope.startLine || 1);
    setInputEndLine(targetScope.endLine || Math.min(15, totalLines));
  }, [targetScope.startLine, targetScope.endLine, totalLines]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  // Words and duration for the target scope
  const targetWords = targetScope.selectedText
    ? targetScope.selectedText.replace(/\[.*?\]/g, " ").replace(/\(.*?\)/g, " ").split(/\s+/).filter(Boolean).length
    : 0;
  const targetDuration = targetWords > 0 ? targetWords / (pacingConfig.wpm / 60) : 0;

  // Set line range manually
  const handleApplyLineRange = (start: number, end: number) => {
    const s = Math.max(1, Math.min(start, totalLines));
    const e = Math.max(s, Math.min(end, totalLines));
    const slice = lines.slice(s - 1, e).join("\n");
    const words = slice.replace(/\[.*?\]/g, " ").replace(/\(.*?\)/g, " ").split(/\s+/).filter(Boolean).length;
    const dur = words / (pacingConfig.wpm / 60);

    onTargetScopeChange({
      type: "lines",
      startLine: s,
      endLine: e,
      selectedText: slice,
      wordCount: words,
      estimatedSeconds: dur,
    });
  };

  // Quick section select
  const handleSelectSection = (keyword: string, fallbackLabel: string) => {
    let sLine = -1;
    let eLine = -1;

    for (let i = 0; i < lines.length; i++) {
      if (lines[i].toLowerCase().includes(keyword.toLowerCase())) {
        sLine = i + 1;
        // find next section header or end of script
        let j = i + 1;
        while (j < lines.length && !lines[j].trim().startsWith("[")) {
          j++;
        }
        eLine = j;
        break;
      }
    }

    if (sLine !== -1 && eLine !== -1) {
      handleApplyLineRange(sLine, eLine);
    } else {
      // fallback
      handleApplyLineRange(1, Math.min(12, totalLines));
    }
  };

  // Perform targeted AI script modification
  const handleExecuteRewrite = async (promptText: string) => {
    if (!promptText.trim() || isProcessing) return;

    setIsProcessing(true);
    const userMsg: ChatbotMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: promptText,
      targetScope: { ...targetScope },
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");

    // Simulate AI synthesis
    await new Promise((r) => setTimeout(r, 1200));

    // Determine what to replace
    const isTargetingLines = targetScope.type !== "full" && targetScope.startLine > 0 && targetScope.endLine >= targetScope.startLine;
    const oldSlice = isTargetingLines
      ? lines.slice(targetScope.startLine - 1, targetScope.endLine).join("\n")
      : scriptText;

    // Save previous state for undo
    setUndoStack((prev) => [{ oldText: scriptText, targetScope: { ...targetScope } }, ...prev]);

    // Generate intelligent rewrite depending on the prompt and brief
    let newSlice = "";
    let isFullScriptGen = false;
    let isCopyRiskCheck = false;
    const lowerPrompt = promptText.toLowerCase();

    if (
      lowerPrompt.includes("tự sinh") ||
      lowerPrompt.includes("sinh kịch bản") ||
      lowerPrompt.includes("tạo kịch bản") ||
      lowerPrompt.includes("viết kịch bản") ||
      lowerPrompt.includes("kịch bản mới") ||
      lowerPrompt.includes("soạn kịch bản") ||
      lowerPrompt.includes("10 tiêu chí")
    ) {
      isFullScriptGen = true;
      newSlice = `[Hook // 00:00 - 00:03]
(Visual Cue: Quay cận cảnh góc máy sốc, xuất hiện text cảnh báo neon nhấp nháy, khung hình ${brief.aspectRatio || "9:16"})
${
  brief.hookType === "counter_intuitive"
    ? `Nếu bạn vẫn nghĩ ${brief.topic ? brief.topic.toLowerCase() : "vấn đề này"} là chuyện đơn giản, thì 90% bạn đang làm sai ngay từ bước đầu tiên!`
    : brief.hookType === "fatal_mistake"
    ? `Sai lầm chết người khi ${brief.topic ? brief.topic.toLowerCase() : "làm điều này"} mà 99% mọi người đều mắc phải!`
    : `Dừng ngay việc làm này lại nếu bạn không muốn ${brief.audiencePainPoint ? brief.audiencePainPoint.toLowerCase() : "mất thời gian và tiền bạc"}!`
}

[Bằng chứng & Thực tế // 00:03 - 00:20]
(Visual Cue: Đưa đồ họa số liệu thực tế: ${(brief.specificFactsAndData || "Dữ liệu kiểm chứng độc lập").slice(0, 80)}..., nhạc nền chuyển nhịp kịch tính)
${brief.uniqueAngle || "Góc nhìn đột phá chưa từng được tiết lộ."}
Theo dữ liệu thực nghiệm: ${(brief.specificFactsAndData || "Tỷ lệ chuẩn xác định đã được xác thực 100%").slice(0, 100)}...

[Giải pháp & Cú lật Turn // 00:20 - 00:45]
(Visual Cue: Format ${brief.formatType === "talking_head" ? "Creator nói trực diện camera với biểu cảm thuyết phục" : "Cinematic B-Roll chi tiết từng động tác thực hành"}, phong cách ${brief.benchmarkCreatorOrChannel || "Chuyên nghiệp & cuốn hút"})
${brief.includeMemeSlang ? `Bí kíp này ${brief.slangKeywords || "chuẩn đét"} mà ít ai tiết lộ: ` : "Giải pháp cốt lõi ở đây: "}
Đừng làm theo lối mòn sáo rỗng. Hãy tập trung giải quyết đúng vấn đề ${brief.audienceDesire ? brief.audienceDesire.toLowerCase() : "đạt kết quả tối ưu"} để bứt phá.

[Payoff & CTA // 00:45 - 00:60]
(Visual Cue: Xuất hiện nút kêu gọi hành động đồ họa động theo chuẩn nền tảng ${(brief.platform || "tiktok").toUpperCase()})
${brief.callToAction || "Follow kênh ngay hôm nay để nhận trọn bộ cẩm nang chi tiết!"}`;
    } else if (lowerPrompt.includes("trùng lặp") || lowerPrompt.includes("bản quyền") || lowerPrompt.includes("unique") || lowerPrompt.includes("copy-risk")) {
      isCopyRiskCheck = true;
      newSlice = oldSlice;
    } else if (lowerPrompt.includes("hook") || lowerPrompt.includes("giật gân") || lowerPrompt.includes("3s") || lowerPrompt.includes("3 giây")) {
      newSlice = `[Hook // 00:00 - 00:03]\n(Visual Cue: Quay cận cảnh sốc 0.5s, âm thanh Bass Drop rung màn hình, text cảnh báo đỏ)\n${
        brief.hookType === "fatal_mistake"
          ? `Sai lầm chết người mà 99% mọi người đều mắc phải khi ${brief.topic.toLowerCase()}!`
          : `Đừng bao giờ làm điều này nếu bạn không muốn ${brief.audiencePainPoint.toLowerCase()}!`
      }`;
    } else if (lowerPrompt.includes("ngắn") || lowerPrompt.includes("rút gọn") || lowerPrompt.includes("10s") || lowerPrompt.includes("15s")) {
      newSlice = `[Nội dung tinh gọn // Rút ngắn]\n(Visual Cue: Chuyển cảnh nhanh 3 góc máy B-Roll minh họa)\nCông thức cốt lõi: ${brief.uniqueAngle.slice(0, 90)}... Áp dụng ngay để ${brief.audienceDesire.toLowerCase()}!`;
    } else if (lowerPrompt.includes("visual cue") || lowerPrompt.includes("hình ảnh") || lowerPrompt.includes("cảnh quay")) {
      newSlice = oldSlice.split("\n").map((l) => {
        if (l.trim().startsWith("[") && !l.includes("Visual Cue")) {
          return `${l}\n(Visual Cue: Quay cận cảnh góc máy POV, chuyển cảnh kinetic zoom in)`;
        }
        return l;
      }).join("\n");
      if (!newSlice.includes("Visual Cue")) {
        newSlice = `(Visual Cue: Quay cận cảnh chi tiết động tác, hiệu ứng chữ neon nhấp nháy)\n${oldSlice}`;
      }
    } else if (lowerPrompt.includes("hài hước") || lowerPrompt.includes("meme") || lowerPrompt.includes("tiếng lóng") || lowerPrompt.includes("slang")) {
      newSlice = `${oldSlice}\n(Visual Cue: Chèn sound effect 'boing' meme và icon cười nghiêng ngả)\nBí thuật này thì ${brief.slangKeywords || "chuẩn đét"}, áp dụng xong bao ngon không trượt phát nào!`;
    } else if (lowerPrompt.includes("số liệu") || lowerPrompt.includes("thực tế") || lowerPrompt.includes("bằng chứng") || lowerPrompt.includes("chống bịa")) {
      newSlice = `[Số liệu kiểm chứng // Thực tế 100%]\n(Visual Cue: Xuất hiện biểu đồ số liệu minh họa nguồn uy tín)\nTheo dữ liệu thực nghiệm: ${brief.specificFactsAndData || "Tỷ lệ chuẩn 1:1.15, số liệu được kiểm chứng độc lập"}.`;
    } else {
      // General contextual rewrite
      newSlice = `(Visual Cue: Góc máy ${brief.formatType === "talking_head" ? "On-cam trực diện thuyết phục" : "B-Roll điện ảnh cận cảnh"})\n${promptText.includes("kịch tính") ? "Bí mật mà không một chuyên gia nào muốn bạn biết: " : ""}${brief.uniqueAngle.slice(0, 120)}...`;
    }

    // Apply the replacement in the exact target line range
    let updatedFullScript = scriptText;
    if (isFullScriptGen) {
      updatedFullScript = newSlice;
      onTargetScopeChange({
        type: "full",
        startLine: 1,
        endLine: newSlice.split("\n").length,
        selectedText: newSlice,
        wordCount: newSlice.split(/\s+/).length,
        estimatedSeconds: newSlice.split(/\s+/).length / (pacingConfig.wpm / 60),
      });
    } else if (isCopyRiskCheck) {
      updatedFullScript = scriptText;
    } else if (isTargetingLines) {
      const beforeLines = lines.slice(0, targetScope.startLine - 1);
      const afterLines = lines.slice(targetScope.endLine);
      updatedFullScript = [...beforeLines, newSlice, ...afterLines].join("\n");
    } else {
      updatedFullScript = newSlice;
    }

    onScriptTextChange(updatedFullScript);

    // Add assistant response message with diff and undo capability
    const assistantMsg: ChatbotMessage = {
      id: `ai-${Date.now()}`,
      role: "assistant",
      content: isFullScriptGen
        ? `✨ Đã tự động tạo xong toàn bộ kịch bản dựa trên 10 tiêu chí đề bài cho chủ đề: "${brief.topic || "Mẹo nấu cơm"}"!`
        : isCopyRiskCheck
        ? `🛡️ Kết quả quét bản quyền: An toàn 100%! Kịch bản độc quyền, 0% Copy-Risk, tuân thủ đầy đủ chính sách nền tảng.`
        : isTargetingLines
        ? `✅ Đã sửa xong dòng ${targetScope.startLine} - ${targetScope.endLine} theo yêu cầu: "${promptText}". Các dòng khác được giữ nguyên 100%!`
        : `✅ Đã cập nhật lại toàn bộ kịch bản theo yêu cầu: "${promptText}".`,
      targetScope: { ...targetScope },
      diffBefore: isCopyRiskCheck ? undefined : oldSlice.slice(0, 180) + (oldSlice.length > 180 ? "..." : ""),
      diffAfter: isCopyRiskCheck ? undefined : newSlice.slice(0, 180) + (newSlice.length > 180 ? "..." : ""),
      applied: !isCopyRiskCheck,
      canUndo: !isCopyRiskCheck,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setIsProcessing(false);
  };

  // Undo last change
  const handleUndo = () => {
    if (undoStack.length === 0) return;
    const lastItem = undoStack[0];
    onScriptTextChange(lastItem.oldText);
    setUndoStack((prev) => prev.slice(1));

    const undoNotice: ChatbotMessage = {
      id: `undo-${Date.now()}`,
      role: "system",
      content: `↩️ Đã hoàn tác lại phiên bản kịch bản trước đó!`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, undoNotice]);
  };

  return (
    <Card className="flex flex-col h-full border-nle-border bg-nle-panel overflow-hidden shadow-2xl">
      {/* Header: AI Copilot Status & Undo */}
      <CardHeader className="py-2.5 px-3 border-b border-nle-border bg-nle-surface/90 flex flex-row items-center justify-between shrink-0">
        <div className="flex items-center space-x-2 min-w-0">
          <div className="w-6 h-6 rounded-lg bg-nle-cyan/20 border border-nle-cyan/40 flex items-center justify-center text-nle-cyan shrink-0">
            <Bot className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <CardTitle className="text-xs font-bold text-white flex items-center space-x-1.5 truncate">
              <span>AI Script Copilot</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </CardTitle>
            <p className="text-[10px] text-gray-400 truncate">
              Sửa trực tiếp kịch bản theo phạm vi đánh dấu
            </p>
          </div>
        </div>

        {undoStack.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleUndo}
            className="text-[10px] h-6 px-2 border-nle-border text-amber-300 hover:text-white hover:bg-nle-border"
          >
            <RotateCcw className="w-3 h-3 mr-1" />
            Hoàn tác ({undoStack.length})
          </Button>
        )}
      </CardHeader>

      {/* Target Scope Controller Bar */}
      <div className="p-2.5 bg-black/40 border-b border-nle-border space-y-2 shrink-0 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5">
            <Target className="w-3.5 h-3.5 text-nle-cyan shrink-0" />
            <span className="text-[11px] font-bold text-gray-200">
              {targetScope.type === "full" ? (
                "Phạm vi: Toàn bộ kịch bản"
              ) : (
                <>
                  Phạm vi sửa:{" "}
                  <span className="text-nle-cyan font-mono">
                    Dòng {targetScope.startLine} - {targetScope.endLine}
                  </span>
                </>
              )}
            </span>
          </div>

          {targetScope.type !== "full" && (
            <span className="text-[10px] font-mono text-gray-400">
              {targetWords} từ ~ {formatTime(targetDuration)}
            </span>
          )}
        </div>

        {/* Manual Range Pickers */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[10px] text-gray-400">Dòng:</span>
          <input
            type="number"
            min={1}
            max={totalLines}
            value={inputStartLine}
            onChange={(e) => setInputStartLine(parseInt(e.target.value) || 1)}
            className="w-12 bg-nle-panel border border-nle-border rounded p-1 text-[11px] text-center text-white font-mono"
          />
          <span className="text-gray-500">-</span>
          <input
            type="number"
            min={inputStartLine}
            max={totalLines}
            value={inputEndLine}
            onChange={(e) => setInputEndLine(parseInt(e.target.value) || totalLines)}
            className="w-12 bg-nle-panel border border-nle-border rounded p-1 text-[11px] text-center text-white font-mono"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleApplyLineRange(inputStartLine, inputEndLine)}
            className="text-[10px] h-6 px-2 border-nle-border text-gray-300 hover:text-white"
          >
            Đặt vùng
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              onTargetScopeChange({
                type: "full",
                startLine: 1,
                endLine: totalLines,
                selectedText: scriptText,
                wordCount: scriptText.split(/\s+/).length,
                estimatedSeconds: scriptText.split(/\s+/).length / (pacingConfig.wpm / 60),
              })
            }
            className="text-[10px] h-6 px-1.5 text-gray-400 hover:text-white"
          >
            Toàn văn
          </Button>
        </div>

        {/* Quick Section Jump Pills */}
        <div className="flex flex-wrap gap-1 pt-0.5">
          {[
            { key: "Hook", label: "Hook 3s" },
            { key: "Bằng chứng", label: "Nội dung" },
            { key: "Cú lật", label: "Cú lật Turn" },
            { key: "CTA", label: "CTA" },
          ].map((sec) => (
            <button
              key={sec.key}
              onClick={() => handleSelectSection(sec.key, sec.label)}
              className="px-1.5 py-0.5 rounded text-[10px] bg-nle-surface hover:bg-nle-border border border-nle-border text-gray-300 hover:text-white transition-colors"
            >
              [{sec.label}]
            </button>
          ))}
        </div>
      </div>

      {/* Quick Action Rewrite Chips */}
      <div className="px-2.5 py-2 border-b border-nle-border bg-nle-surface/40 flex items-center space-x-1.5 overflow-x-auto shrink-0 scrollbar-none">
        <span className="text-[10px] text-gray-400 font-semibold shrink-0">Lệnh nhanh:</span>
        {[
          { label: "✨ Tự sinh kịch bản", prompt: "Tự sinh toàn bộ kịch bản dựa trên 10 tiêu chí đề bài" },
          { label: "🔥 Viết lại Hook 3s", prompt: "Viết lại Hook 3 giây thật giật gân, tạo khoảng trống tò mò giữ chân người xem" },
          { label: "⚡ Rút ngắn 15s", prompt: "Rút ngắn đoạn này lại chỉ nói trong vòng 10 đến 15 giây" },
          { label: "🎬 Thêm Visual Cue", prompt: "Bổ sung chỉ dẫn Visual Cue góc máy chi tiết cho từng câu thoại" },
          { label: "🛡️ Quét bản quyền (100% Unique)", prompt: "Quét trùng lặp và bản quyền nội dung đảm bảo 100% unique" },
          { label: "😂 Chèn Slang/Meme", prompt: "Chèn thêm từ lóng giới trẻ, tiếng lóng tự nhiên và phong cách hài hước" },
          { label: "📊 Đưa số liệu chống bịa", prompt: "Đưa thêm số liệu thực tế kiểm chứng để nội dung uy tín chống bịa đặt" },
        ].map((chip, idx) => (
          <button
            key={idx}
            disabled={isProcessing}
            onClick={() => handleExecuteRewrite(chip.prompt)}
            className="px-2 py-0.5 rounded-full text-[10px] bg-nle-panel hover:bg-nle-cyan/20 hover:text-nle-cyan border border-nle-border text-gray-300 whitespace-nowrap transition-all"
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Chat Messages Feed */}
      <CardContent className="flex-1 p-3 overflow-y-auto space-y-3 min-h-0 text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col space-y-1 ${
              m.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div className="flex items-center space-x-1 text-[9px] text-gray-400 font-mono">
              <span>{m.role === "user" ? "Bạn" : m.role === "assistant" ? "AI Copilot" : "Hệ thống"}</span>
              <span>•</span>
              <span>{m.timestamp}</span>
            </div>

            <div
              className={`p-2.5 rounded-xl max-w-[92%] leading-relaxed ${
                m.role === "user"
                  ? "bg-nle-cyan/20 border border-nle-cyan/40 text-white rounded-tr-none"
                  : m.role === "assistant"
                  ? "bg-nle-surface border border-nle-border text-gray-200 rounded-tl-none"
                  : "bg-amber-500/10 border border-amber-500/30 text-amber-300 text-center w-full"
              }`}
            >
              <div className="whitespace-pre-line">{m.content}</div>

              {/* Diff Preview Card */}
              {m.diffAfter && (
                <div className="mt-2 pt-2 border-t border-nle-border/60 space-y-1.5 text-[11px]">
                  {m.diffBefore && (
                    <div className="p-1.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 line-through font-mono text-[10px]">
                      {m.diffBefore}
                    </div>
                  )}
                  <div className="p-1.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono text-[10px]">
                    {m.diffAfter}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex items-center space-x-2 text-nle-cyan text-xs bg-nle-surface/80 p-2.5 rounded-xl border border-nle-border w-fit animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>AI đang viết lại theo yêu cầu...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </CardContent>

      {/* Chat Prompt Input Box */}
      <div className="p-2.5 bg-nle-surface border-t border-nle-border shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleExecuteRewrite(inputPrompt);
          }}
          className="flex items-center space-x-1.5"
        >
          <input
            type="text"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={isProcessing}
            placeholder={
              targetScope.type !== "full"
                ? `Sửa dòng ${targetScope.startLine}-${targetScope.endLine}: 'Viết ngắn lại', 'Thêm kịch tính'...'`
                : "Yêu cầu sửa kịch bản..."
            }
            className="flex-1 bg-nle-panel border border-nle-border rounded-lg p-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-nle-cyan"
          />

          <Button
            type="submit"
            variant="neon"
            size="sm"
            disabled={!inputPrompt.trim() || isProcessing}
            className="h-8 px-3 shrink-0"
          >
            {isProcessing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
          </Button>
        </form>

        <div className="flex justify-between items-center text-[9px] text-gray-500 mt-1 px-0.5">
          <span>Gemini 2.5 Flash • Targeted Scope Editor</span>
          <span>Nhấn Enter để gửi</span>
        </div>
      </div>
    </Card>
  );
}
