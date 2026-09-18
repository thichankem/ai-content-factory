"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useUIStore } from "../../stores/useUIStore";
import { useTimelineStore } from "../../stores/useTimelineStore";
import { useProjectStore } from "../../stores/useProjectStore";
import { useTimelineCommands } from "../../hooks/useTimelineCommands";
import { Sparkles, X, ArrowRight, CornerDownLeft, Loader2 } from "lucide-react";

export function CommandBarModal() {
  const { isCommandBarOpen, setCommandBarOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { scenes } = useTimelineStore();
  const { commandMutation } = useTimelineCommands();
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const quickChips = [
    "Tăng tốc cảnh intro lên 1.5x",
    "Cắt bỏ cảnh 2",
    "Giảm âm lượng nhạc nền 50%",
    "Đồng bộ nhịp điệu beat sync",
    "Fit toàn bộ timeline về 45s",
  ];

  const handleExecute = async (cmdText: string) => {
    if (!cmdText.trim()) return;
    setStatusMessage(null);

    const videoProject = currentProject?.video_project || {
      scenes: scenes.length > 0 ? scenes : [
        { index: 0, label: "Hook", duration: 3.5, text: "Hook mở đầu" },
        { index: 1, label: "Body", duration: 15.0, text: "Thân bài nội dung" },
        { index: 2, label: "Payoff", duration: 5.0, text: "Lời kết CTA" },
      ],
      aspect_ratio: "9:16",
      target_duration_seconds: 45,
    };

    try {
      const res = await commandMutation.mutateAsync({
        command: cmdText,
        videoProject,
      });
      setStatusMessage(res.message || `Đã thực thi thành công: ${res.parsed_command.intent}`);
      setInput("");
    } catch (err: any) {
      setStatusMessage(`Lỗi thực thi: ${err.message}`);
    }
  };

  return (
    <AnimatePresence>
      {isCommandBarOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/75 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: "spring", stiffness: 350, damping: 25 }}
            className="w-full max-w-2xl border border-nle-border bg-nle-surface rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Input Header */}
            <div className="flex items-center px-4 py-3 border-b border-nle-border bg-nle-panel/60">
              <Sparkles className="w-5 h-5 text-nle-cyan mr-3 animate-pulse" />
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleExecute(input);
                  }
                  if (e.key === "Escape") {
                    setCommandBarOpen(false);
                  }
                }}
                placeholder="Nhập yêu cầu AI Co-Pilot (ví dụ: 'Tăng tốc cảnh intro 1.5x', 'Cắt cảnh 2')..."
                className="w-full bg-transparent border-0 text-white placeholder-gray-500 focus:outline-none text-sm"
                autoFocus
              />
              <button
                onClick={() => setCommandBarOpen(false)}
                className="text-gray-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Suggestions Chips */}
            <div className="p-3 bg-nle-base/50 flex flex-wrap gap-1.5 border-b border-nle-border">
              <span className="text-[11px] text-gray-400 self-center mr-1">Gợi ý:</span>
              {quickChips.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setInput(chip);
                    handleExecute(chip);
                  }}
                  className="text-xs px-2.5 py-1 rounded-full bg-nle-panel border border-nle-border text-gray-300 hover:text-nle-cyan hover:border-nle-cyan/40 transition-colors flex items-center"
                >
                  <span>{chip}</span>
                  <ArrowRight className="w-2.5 h-2.5 ml-1 opacity-60" />
                </button>
              ))}
            </div>

            {/* Result / Status Area */}
            {statusMessage && (
              <div className="p-3 bg-nle-panel/80 border-b border-nle-border text-xs text-nle-cyan flex items-center justify-between">
                <span>{statusMessage}</span>
                <CornerDownLeft className="w-3.5 h-3.5 opacity-60" />
              </div>
            )}

            {/* Footer */}
            <div className="px-4 py-2 bg-nle-surface flex items-center justify-between text-[11px] text-gray-500">
              <div className="flex items-center space-x-2">
                <span>⚡ AI Timeline Engine (Bilingual VI/EN)</span>
              </div>
              <div className="flex items-center space-x-2">
                {commandMutation.isPending && (
                  <span className="flex items-center text-nle-cyan">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    Đang xử lý...
                  </span>
                )}
                <span>Nhấn <kbd className="bg-nle-panel px-1 py-0.5 rounded border border-nle-border text-gray-300">Enter</kbd> để chạy</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
