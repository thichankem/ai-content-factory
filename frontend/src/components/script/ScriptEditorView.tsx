"use client";

import React, { useState, useRef, useEffect } from "react";
import { SpeechPacingConfig, TargetScope } from "@/types/studio";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  SlidersHorizontal,
  Flame,
  CheckCircle2,
  BookOpen,
  Eye,
  ShieldCheck,
  Copy,
  Check,
  Film,
  Sparkles,
  Layers,
  Save,
  Loader2,
  History,
} from "lucide-react";

interface StoryboardScene {
  id: string;
  timeRange: string;
  section: string;
  voiceover: string;
  visualCue: string;
}

interface ScriptEditorViewProps {
  scriptText: string;
  onScriptTextChange: (text: string) => void;
  targetScope: TargetScope;
  onTargetScopeChange: (scope: TargetScope) => void;
  pacingConfig: SpeechPacingConfig;
  sourceRightsConfirmed: boolean;
  onConfirmSourceRights: () => void;
  /** Persist the editor's text; Gate 1 reads the saved copy, not this one. */
  onSaveScript?: () => void;
  isSaving?: boolean;
  onApproveGate1: () => void;
  isApproving?: boolean;
  onScoreVirality?: () => void;
  onOpenHistory?: () => void;
  historyCount?: number;
  topic: string;
  platform: string;
  targetDuration: string;
}

export function ScriptEditorView({
  scriptText,
  onScriptTextChange,
  targetScope,
  onTargetScopeChange,
  pacingConfig,
  sourceRightsConfirmed,
  onConfirmSourceRights,
  onSaveScript,
  isSaving = false,
  onApproveGate1,
  isApproving = false,
  onScoreVirality,
  onOpenHistory,
  historyCount,
  topic,
  platform,
  targetDuration,
}: ScriptEditorViewProps) {
  const [viewMode, setViewMode] = useState<"raw" | "storyboard">("raw");
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);

  const lines = scriptText.split("\n");
  const totalLines = lines.length;

  // Sync scroll between gutter and textarea
  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = e.currentTarget.scrollTop;
    }
  };

  // Detect line numbers from text selection
  const handleSelectText = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const startPos = textarea.selectionStart;
    const endPos = textarea.selectionEnd;

    if (startPos === endPos) {
      // Cursor only - detect current line
      const textBefore = scriptText.slice(0, startPos);
      const currentLine = textBefore.split("\n").length;
      const currentLineText = lines[currentLine - 1] || "";
      const words = currentLineText.trim().split(/\s+/).filter(Boolean).length;
      const dur = words / (pacingConfig.wpm / 60);

      onTargetScopeChange({
        type: "lines",
        startLine: currentLine,
        endLine: currentLine,
        selectedText: currentLineText,
        wordCount: words,
        estimatedSeconds: dur,
      });
      return;
    }

    // Selected multiple characters/lines
    const textBefore = scriptText.slice(0, startPos);
    const selected = scriptText.slice(startPos, endPos);
    const startLine = textBefore.split("\n").length;
    const selectedLinesCount = selected.split("\n").length;
    const endLine = startLine + selectedLinesCount - 1;

    const clean = selected.replace(/\[.*?\]/g, " ").replace(/\(.*?\)/g, " ").trim();
    const words = clean ? clean.split(/\s+/).filter(Boolean).length : 0;
    const dur = words / (pacingConfig.wpm / 60);

    onTargetScopeChange({
      type: "selection",
      startLine,
      endLine,
      selectedText: selected,
      wordCount: words,
      estimatedSeconds: dur,
    });
  };

  // Click on a line number in the gutter
  const handleLineGutterClick = (lineIndex: number) => {
    const lineNum = lineIndex + 1;
    const lineContent = lines[lineIndex] || "";
    const words = lineContent.trim().split(/\s+/).filter(Boolean).length;
    const dur = words / (pacingConfig.wpm / 60);

    onTargetScopeChange({
      type: "lines",
      startLine: lineNum,
      endLine: lineNum,
      selectedText: lineContent,
      wordCount: words,
      estimatedSeconds: dur,
    });
  };

  // Parse raw script into two-column storyboard scenes
  const parseStoryboardScenes = (): StoryboardScene[] => {
    const rawBlocks = scriptText.split(/\n\s*\n/);
    return rawBlocks
      .map((block, idx) => {
        const trimmed = block.trim();
        if (!trimmed) return null;

        const headerMatch = trimmed.match(/^\[(.*?)\]/);
        const sectionHeader = headerMatch ? headerMatch[1] : `Phân đoạn ${idx + 1}`;
        const rest = headerMatch ? trimmed.slice(headerMatch[0].length).trim() : trimmed;

        let visualCue = "Quay cảnh B-roll tương ứng nội dung lời thoại";
        let voiceover = rest;

        const cueMatch = rest.match(/\(Visual Cue:\s*(.*?)\)/i);
        if (cueMatch) {
          visualCue = cueMatch[1].trim();
          voiceover = rest.replace(cueMatch[0], "").trim();
        }

        const timeMatch = sectionHeader.match(/(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})/);
        const timeRange = timeMatch ? timeMatch[1] : `${idx * 15}s - ${(idx + 1) * 15}s`;

        return {
          id: `scene-${idx + 1}`,
          timeRange,
          section: sectionHeader.replace(/\/\/.*$/, "").trim(),
          voiceover,
          visualCue,
        };
      })
      .filter(Boolean) as StoryboardScene[];
  };

  const storyboardScenes = parseStoryboardScenes();

  const handleCopyScript = () => {
    navigator.clipboard.writeText(scriptText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="flex-1 flex flex-col min-h-0 border-nle-border bg-nle-panel overflow-hidden shadow-xl">
      {/* Top Header */}
      <CardHeader className="py-2.5 px-3.5 border-b border-nle-border flex flex-row items-center justify-between shrink-0">
        <div className="min-w-0">
          <CardTitle className="text-xs font-bold text-white flex items-center space-x-1.5 truncate">
            <BookOpen className="w-4 h-4 text-nle-cyan shrink-0" />
            <span className="truncate">Kịch Bản: {topic}</span>
            <Badge variant="cyan" className="text-[10px] shrink-0 font-mono">
              {lines.length} Dòng
            </Badge>
            <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/30 shrink-0 uppercase">
              {platform} • {targetDuration}
            </Badge>
          </CardTitle>
          <p className="text-[11px] text-gray-400 mt-0.5 truncate">
            Bôi đen văn bản hoặc click số dòng để AI Copilot chỉnh sửa đúng phạm vi đó
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {/* View Mode Toggle */}
          <div className="flex items-center space-x-1 bg-nle-surface p-0.5 rounded-lg border border-nle-border text-xs">
            <button
              onClick={() => setViewMode("raw")}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                viewMode === "raw" ? "bg-nle-panel text-white font-bold shadow-sm" : "text-gray-400 hover:text-white"
              }`}
            >
              Văn bản (Đánh số dòng)
            </button>
            <button
              onClick={() => setViewMode("storyboard")}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                viewMode === "storyboard" ? "bg-nle-panel text-nle-cyan font-bold shadow-sm" : "text-gray-400 hover:text-white"
              }`}
            >
              Thẻ phân cảnh (Storyboard Feed)
            </button>
          </div>

          {onOpenHistory && (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenHistory}
              className="text-[11px] border-nle-border text-amber-300 hover:text-white h-7 px-2"
              title="Xem lịch sử các phiên bản từng phân đoạn"
            >
              <History className="w-3.5 h-3.5 mr-1 text-amber-400" />
              Lịch sử {historyCount !== undefined && historyCount > 0 ? `(${historyCount})` : ""}
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyScript}
            className="text-[11px] border-nle-border text-gray-300 hover:text-white h-7 px-2"
          >
            {copied ? <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 mr-1" />}
            {copied ? "Đã chép" : "Sao chép"}
          </Button>

          {onScoreVirality && (
            <Button
              variant="neon"
              size="sm"
              onClick={onScoreVirality}
              className="text-[11px] h-7 px-2.5 font-semibold"
            >
              <Flame className="w-3.5 h-3.5 mr-1 fill-current" />
              Chấm Điểm Virality
            </Button>
          )}
        </div>
      </CardHeader>

      {/* Editor Main Content Area */}
      <CardContent className="flex-1 p-3 flex flex-col justify-between min-h-0 overflow-hidden">
        {viewMode === "raw" ? (
          <div className="flex-1 flex overflow-hidden border border-nle-border rounded-lg bg-nle-surface/50 relative">
            {/* Line Number Gutter */}
            <div
              ref={gutterRef}
              className="w-12 py-3 px-1 bg-black/40 border-r border-nle-border select-none text-right font-mono text-[11px] text-gray-500 overflow-hidden space-y-[2px]"
            >
              {lines.map((_, idx) => {
                const lineNum = idx + 1;
                const isSelected =
                  targetScope.type !== "full" &&
                  lineNum >= targetScope.startLine &&
                  lineNum <= targetScope.endLine;

                return (
                  <div
                    key={idx}
                    onClick={() => handleLineGutterClick(idx)}
                    className={`cursor-pointer px-1 rounded transition-colors leading-5 ${
                      isSelected
                        ? "bg-nle-cyan text-black font-bold"
                        : "hover:text-gray-200 hover:bg-white/5"
                    }`}
                    title={`Click để chọn dòng ${lineNum}`}
                  >
                    {lineNum}
                  </div>
                );
              })}
            </div>

            {/* Script Text Area */}
            <textarea
              ref={textareaRef}
              value={scriptText}
              onChange={(e) => onScriptTextChange(e.target.value)}
              onScroll={handleScroll}
              onSelect={handleSelectText}
              onKeyUp={handleSelectText}
              onMouseUp={handleSelectText}
              spellCheck={false}
              className="flex-1 p-3 bg-transparent text-xs text-gray-100 placeholder-gray-500 focus:outline-none resize-none font-mono leading-5 overflow-y-auto"
              placeholder="Nhập hoặc để AI sinh kịch bản tại đây..."
            />
          </div>
        ) : (
          /* Single-Column Storyboard Feed View */
          <div className="flex-1 overflow-y-auto border border-nle-border rounded-lg bg-nle-panel p-3 space-y-3">
            {storyboardScenes.map((sc, idx) => (
              <div
                key={sc.id}
                className="p-3.5 rounded-lg border border-nle-border bg-nle-surface/80 hover:border-nle-cyan/40 transition-colors space-y-2.5 shadow-sm"
              >
                <div className="flex items-center justify-between border-b border-nle-border/60 pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-black bg-nle-cyan px-2 py-0.5 rounded">
                      Cảnh #{idx + 1}
                    </span>
                    <Badge variant="outline" className="text-[10px] text-amber-300 border-amber-500/30">
                      {sc.section}
                    </Badge>
                  </div>
                  <span className="text-[10px] font-mono text-gray-400">
                    ⏱️ {sc.timeRange}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded bg-nle-panel border border-nle-border/80 space-y-1">
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide flex items-center">
                      🎙️ Lời thoại Voiceover (TTS)
                    </span>
                    <p className="text-gray-100 font-sans leading-relaxed text-[12px]">
                      {sc.voiceover || <span className="text-gray-500 italic">(Chưa có lời thoại)</span>}
                    </p>
                  </div>

                  <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-500/30 space-y-1">
                    <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wide flex items-center">
                      🎬 Chỉ dẫn Hình ảnh Visual Cue
                    </span>
                    <p className="text-emerald-300 text-[11px] font-sans italic">
                      {sc.visualCue || <span className="text-emerald-600/70 italic">(Chưa có chỉ dẫn khung hình)</span>}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Mandatory Human Review Gate 1 Banner */}
        <div className="mt-3 p-2.5 bg-nle-surface/90 border border-amber-500/40 rounded-lg flex flex-wrap items-center justify-between gap-2 shrink-0">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="source-rights-gate"
              checked={sourceRightsConfirmed}
              onChange={onConfirmSourceRights}
              className="rounded border-nle-border text-nle-cyan focus:ring-0 w-4 h-4 bg-nle-panel cursor-pointer"
            />
            <label htmlFor="source-rights-gate" className="text-xs text-gray-200 cursor-pointer">
              {/* Ticking this saves the script with the confirmation attached; the
                  backend records it, which is what actually opens Gate 1. */}
              Xác nhận bản quyền nguồn tư liệu hợp pháp (Source Rights Confirmed - Không vi phạm bản quyền)
            </label>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onSaveScript}
              disabled={!onSaveScript || isSaving}
              title="Lưu kịch bản lên server trước khi duyệt Gate 1"
              className="text-xs h-8 border-nle-border text-gray-200 hover:text-white"
            >
              {isSaving ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5 mr-1.5" />
              )}
              Lưu Kịch Bản
            </Button>

            <Button
              variant="default"
              size="sm"
              onClick={onApproveGate1}
              disabled={!sourceRightsConfirmed || isApproving}
              className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs h-8 px-4 shadow-lg shadow-emerald-500/20"
            >
              {isApproving ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
              )}
              <span>Gate 1: Duyệt Kịch Bản & Chuyển Bước 2</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
