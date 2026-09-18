"use client";

import React, { useState, useEffect } from "react";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useAgentBridge } from "@/hooks/useAgentBridge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Bot,
  Copy,
  Check,
  X,
  FileText,
  Sparkles,
  Send,
  Loader2,
  CheckCircle2,
  Cpu,
} from "lucide-react";

export function AgentBridgeModal() {
  const { isAgentBridgeModalOpen, setAgentBridgeModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { catalogQuery, getBrief, importResultMutation } = useAgentBridge(currentProject?.id);

  const [selectedAgent, setSelectedAgent] = useState<string>("claude");
  const [briefMarkdown, setBriefMarkdown] = useState<string>("");
  const [isLoadingBrief, setIsLoadingBrief] = useState(false);
  const [importText, setImportText] = useState("");
  const [copiedBrief, setCopiedBrief] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  useEffect(() => {
    if (isAgentBridgeModalOpen && currentProject?.id) {
      setIsLoadingBrief(true);
      getBrief(selectedAgent)
        .then((md) => setBriefMarkdown(md))
        .catch(() => setBriefMarkdown(`# Production Brief for ${currentProject.name}\n\nAgent: ${selectedAgent}\nTopic: ${currentProject.topic}`))
        .finally(() => setIsLoadingBrief(false));
    }
  }, [isAgentBridgeModalOpen, selectedAgent, currentProject?.id]);

  if (!isAgentBridgeModalOpen) return null;

  const handleCopyBrief = () => {
    navigator.clipboard.writeText(briefMarkdown);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2000);
  };

  const handleImportResult = async () => {
    if (!importText.trim()) return;
    setImportStatus("Đang bóc tách phản hồi của Agent và nhập vào pipeline...");
    try {
      await importResultMutation.mutateAsync({
        markdown_response: importText,
        agent: selectedAgent,
      });
      setImportStatus("✅ Đã nhập thành công kịch bản và phân cảnh mới vào dự án!");
      setImportText("");
      setTimeout(() => setImportStatus(null), 3000);
    } catch (e: any) {
      setImportStatus(`Lỗi phân tích: ${e.message || "Không tìm thấy block script hợp lệ"}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-3xl bg-nle-surface border-nle-border shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
          <div className="flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-nle-cyan" />
            <div>
              <CardTitle className="text-sm font-bold text-white">
                Cầu Nối Đa AI Agent (External AI Agent Bridge)
              </CardTitle>
              <p className="text-[11px] text-gray-400">
                Xuất brief.md cho Claude Code, Gemini, Codex, DeepSeek và nhập lại kịch bản/timeline
              </p>
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setAgentBridgeModalOpen(false)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        {/* Modal Content */}
        <CardContent className="p-4 space-y-3 flex-1 overflow-y-auto min-h-0 text-xs">
          {importStatus && (
            <div className="p-2 rounded bg-nle-panel border border-nle-cyan/40 text-nle-cyan font-semibold text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{importStatus}</span>
            </div>
          )}

          {/* Agent Selection & Catalog Badges */}
          <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-gray-300">Chọn AI Agent mục tiêu:</span>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="bg-nle-base border border-nle-border rounded px-2.5 py-1 text-xs text-nle-cyan font-bold"
                >
                  <option value="claude">Anthropic Claude 3.5 Sonnet / Claude Code</option>
                  <option value="gemini">Google Gemini 2.0 / Flash Thinker</option>
                  <option value="codex">OpenAI Codex / GPT-4o Cinematic</option>
                  <option value="deepseek">DeepSeek V3 / R1 Reasoner</option>
                </select>
              </div>

              <Badge variant="emerald" className="text-[10px]">
                API Bridge Online
              </Badge>
            </div>

            <div className="flex flex-wrap gap-2 text-[10px] text-gray-400">
              <span className="bg-nle-base px-2 py-0.5 rounded border border-nle-border">
                Claude: Văn phong & Cảm xúc
              </span>
              <span className="bg-nle-base px-2 py-0.5 rounded border border-nle-border">
                Gemini: Khung cảnh & Thị giác
              </span>
              <span className="bg-nle-base px-2 py-0.5 rounded border border-nle-border">
                Codex: JSON Timeline & Toán học
              </span>
              <span className="bg-nle-base px-2 py-0.5 rounded border border-nle-border">
                DeepSeek: Phản biện & Quét đạo văn
              </span>
            </div>
          </div>

          {/* Section 1: Live brief.md Preview & Copy */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="font-semibold text-gray-300 flex items-center">
                <FileText className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
                Hồ sơ nhiệm vụ chuẩn Markdown (brief.md Preview):
              </label>

              <Button
                size="sm"
                variant="outline"
                onClick={handleCopyBrief}
                className="h-7 text-xs border-nle-border text-nle-cyan hover:bg-nle-cyan/10"
              >
                {copiedBrief ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                {copiedBrief ? "Đã sao chép!" : "Copy brief.md"}
              </Button>
            </div>

            {isLoadingBrief ? (
              <div className="h-36 flex items-center justify-center bg-nle-base rounded-lg border border-nle-border">
                <Loader2 className="w-5 h-5 text-nle-cyan animate-spin" />
              </div>
            ) : (
              <textarea
                value={briefMarkdown}
                readOnly
                rows={7}
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2.5 text-[11px] font-mono text-gray-300 select-all focus:outline-none resize-none"
              />
            )}
          </div>

          {/* Section 2: Import Agent Response */}
          <div className="space-y-1.5">
            <label className="font-semibold text-gray-300 block">
              Dán phản hồi của Agent vào đây (Markdown / JSON Block):
            </label>
            <textarea
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              rows={6}
              placeholder="Dán toàn bộ kết quả trả lời của Claude / Gemini / DeepSeek (chứa block ```script hoặc ```json scenes)..."
              className="w-full bg-nle-base border border-nle-border rounded-lg p-2.5 text-xs font-mono text-gray-200 focus:border-nle-cyan focus:outline-none resize-y"
            />

            <Button
              size="sm"
              variant="neon"
              onClick={handleImportResult}
              disabled={importResultMutation.isPending || !importText.trim()}
              className="w-full text-xs h-8"
            >
              {importResultMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5 mr-1.5" />
              )}
              Bóc Tách & Nhập Kịch Bản Vào Pipeline
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
