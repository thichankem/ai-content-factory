"use client";

import React, { useState } from "react";
import { SectionHistoryEntry } from "../../types/script";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  History,
  RotateCcw,
  Copy,
  Check,
  Trash2,
  Camera,
  X,
  Clock,
  Sparkles,
  FileText,
  Flame,
  CornerDownRight,
} from "lucide-react";

interface ScriptSectionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  historyEntries: SectionHistoryEntry[];
  onRestoreEntry: (entry: SectionHistoryEntry) => void;
  onSaveManualSnapshot: (note: string, sectionKey: string) => void;
  onClearHistory?: () => void;
  onDeleteEntry?: (id: string) => void;
}

export function ScriptSectionHistoryModal({
  isOpen,
  onClose,
  historyEntries,
  onRestoreEntry,
  onSaveManualSnapshot,
  onClearHistory,
  onDeleteEntry,
}: ScriptSectionHistoryModalProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [snapshotNote, setSnapshotNote] = useState("");
  const [snapshotSection, setSnapshotSection] = useState("full");
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false);

  if (!isOpen) return null;

  const filteredEntries = historyEntries.filter((e) => {
    if (selectedFilter === "all") return true;
    return e.sectionKey === selectedFilter;
  });

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreateSnapshot = () => {
    if (!snapshotNote.trim()) return;
    onSaveManualSnapshot(snapshotNote.trim(), snapshotSection);
    setSnapshotNote("");
    setIsCreatingSnapshot(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-3">
      <Card className="w-full max-w-4xl max-h-[85vh] flex flex-col border-nle-border bg-nle-panel shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <CardHeader className="py-3 px-4 border-b border-nle-border bg-nle-surface flex flex-row items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-nle-cyan/20 border border-nle-cyan/40 flex items-center justify-center text-nle-cyan">
              <History className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-bold text-white flex items-center space-x-2">
                <span>Lịch Sử Phiên Bản & Bản Nháp Phân Đoạn</span>
                <Badge variant="cyan" className="text-[10px] font-mono">
                  {historyEntries.length} Bản lưu
                </Badge>
              </CardTitle>
              <p className="text-[11px] text-gray-400">
                Theo dõi, so sánh và khôi phục riêng lẻ từng đoạn Hook, Nội dung, Cú lật, hoặc toàn bộ kịch bản
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCreatingSnapshot(!isCreatingSnapshot)}
              className="text-xs border-nle-border text-gray-200 hover:text-white h-8 px-2.5"
            >
              <Camera className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
              <span>Lưu Bản Nháp</span>
            </Button>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-white hover:bg-nle-border transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </CardHeader>

        {/* Snapshot Creation Mini-Form */}
        {isCreatingSnapshot && (
          <div className="p-3 bg-nle-surface/90 border-b border-nle-border flex flex-wrap items-center gap-2 shrink-0 animate-in slide-in-from-top-2 duration-150">
            <span className="text-xs font-semibold text-gray-300">Ghi chú bản nháp:</span>
            <input
              type="text"
              value={snapshotNote}
              onChange={(e) => setSnapshotNote(e.target.value)}
              placeholder="Ví dụ: 'Hook trước khi chỉnh giật gân', 'Đoạn cú lật tỷ lệ nước 1:1.15'..."
              className="flex-1 min-w-[200px] bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-white placeholder-gray-500"
            />
            <select
              value={snapshotSection}
              onChange={(e) => setSnapshotSection(e.target.value)}
              className="bg-nle-panel border border-nle-border rounded-lg p-1.5 text-xs text-gray-300"
            >
              <option value="full">Toàn bộ kịch bản</option>
              <option value="hook">Chỉ đoạn [Hook 3s]</option>
              <option value="evidence">Chỉ đoạn [Bằng chứng / Nội dung]</option>
              <option value="turn">Chỉ đoạn [Cú lật Turn]</option>
              <option value="cta">Chỉ đoạn [Payoff & CTA]</option>
            </select>
            <Button
              variant="neon"
              size="sm"
              onClick={handleCreateSnapshot}
              disabled={!snapshotNote.trim()}
              className="text-xs h-8 px-3"
            >
              Lưu Ngay
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCreatingSnapshot(false)}
              className="text-xs h-8 px-2 text-gray-400"
            >
              Hủy
            </Button>
          </div>
        )}

        {/* Section Filter Tabs */}
        <div className="p-2.5 bg-black/40 border-b border-nle-border flex items-center space-x-1 overflow-x-auto shrink-0 scrollbar-none">
          <span className="text-[11px] text-gray-400 font-semibold px-2 shrink-0">Lọc theo phần:</span>
          {[
            { id: "all", label: "Tất cả các phần" },
            { id: "hook", label: "[Hook 3s]" },
            { id: "evidence", label: "[Bằng chứng / Nội dung]" },
            { id: "turn", label: "[Cú lật Turn]" },
            { id: "cta", label: "[Payoff & CTA]" },
            { id: "full", label: "[Toàn kịch bản]" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setSelectedFilter(f.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors shrink-0 ${
                selectedFilter === f.id
                  ? "bg-nle-cyan text-black font-bold shadow-sm"
                  : "bg-nle-surface text-gray-300 hover:text-white border border-nle-border"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Entries List */}
        <CardContent className="flex-1 p-3 overflow-y-auto space-y-3 min-h-0">
          {filteredEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center text-gray-400">
              <History className="w-10 h-10 text-gray-600 mb-2" />
              <p className="text-xs font-medium">Chưa có bản lưu lịch sử nào cho phần này.</p>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Khi bạn hoặc AI Chatbot sửa kịch bản, các phiên bản sẽ tự động được ghi nhớ tại đây.
              </p>
            </div>
          ) : (
            filteredEntries.map((entry) => (
              <div
                key={entry.id}
                className="p-3 rounded-xl bg-nle-surface/80 border border-nle-border hover:border-nle-cyan/40 transition-all space-y-2 text-xs"
              >
                {/* Entry Top Metadata Bar */}
                <div className="flex flex-wrap items-center justify-between gap-1.5 border-b border-nle-border/60 pb-2">
                  <div className="flex items-center space-x-2">
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-bold ${
                        entry.sectionKey === "hook"
                          ? "border-amber-400/40 text-amber-300 bg-amber-400/10"
                          : entry.sectionKey === "turn"
                          ? "border-rose-400/40 text-rose-300 bg-rose-400/10"
                          : entry.sectionKey === "cta"
                          ? "border-emerald-400/40 text-emerald-300 bg-emerald-400/10"
                          : "border-nle-cyan/40 text-nle-cyan bg-nle-cyan/10"
                      }`}
                    >
                      {entry.sectionLabel}
                    </Badge>

                    <span className="font-mono text-gray-400 text-[11px]">
                      Phiên bản #{entry.version}
                    </span>

                    <span className="text-[10px] text-gray-400 flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {entry.timestamp}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono text-gray-400">
                      {entry.wordCount} từ ~ {entry.estimatedSeconds.toFixed(1)}s
                    </span>

                    <Badge
                      variant="secondary"
                      className="text-[9px] bg-black/30 border border-nle-border"
                    >
                      {entry.author === "ai"
                        ? "🤖 AI Chatbot"
                        : entry.author === "snapshot"
                        ? "📸 Bản nháp thủ công"
                        : "✍️ Người dùng"}
                    </Badge>
                  </div>
                </div>

                {/* Summary / Note */}
                {entry.summary && (
                  <p className="text-[11px] text-nle-cyan font-medium flex items-center">
                    <CornerDownRight className="w-3 h-3 mr-1 shrink-0" />
                    <span>{entry.summary}</span>
                  </p>
                )}

                {/* Content Preview Box */}
                <div className="p-2.5 rounded-lg bg-nle-panel border border-nle-border text-[11px] font-mono text-gray-200 whitespace-pre-line leading-relaxed max-h-36 overflow-y-auto">
                  {entry.text}
                </div>

                {/* Actions Bottom Bar */}
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center space-x-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(entry.id, entry.text)}
                      className="text-[11px] h-7 px-2 border-nle-border text-gray-300 hover:text-white"
                    >
                      {copiedId === entry.id ? (
                        <Check className="w-3 h-3 mr-1 text-emerald-400" />
                      ) : (
                        <Copy className="w-3 h-3 mr-1" />
                      )}
                      {copiedId === entry.id ? "Đã chép" : "Sao chép"}
                    </Button>

                    {onDeleteEntry && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDeleteEntry(entry.id)}
                        className="text-[11px] h-7 px-2 text-gray-500 hover:text-rose-400"
                      >
                        <Trash2 className="w-3 h-3 mr-1" />
                        Xóa
                      </Button>
                    )}
                  </div>

                  <Button
                    variant="neon"
                    size="sm"
                    onClick={() => {
                      onRestoreEntry(entry);
                      onClose();
                    }}
                    className="text-[11px] h-7 px-3 font-semibold shadow-sm"
                  >
                    <RotateCcw className="w-3 h-3 mr-1.5" />
                    Khôi Phục Đoạn Này Về Kịch Bản
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
