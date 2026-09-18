"use client";

import React, { useState } from "react";
import { useUIStore } from "@/stores/useUIStore";
import { useProjects } from "@/hooks/useProjects";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  FolderPlus,
  X,
  Sparkles,
  Loader2,
  Clock,
  Globe,
  FileText,
} from "lucide-react";

export function NewProjectModal() {
  const { isNewProjectModalOpen, setNewProjectModalOpen } = useUIStore();
  const { createProjectMutation } = useProjects();

  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("vi");
  const [duration, setDuration] = useState(45);
  const [stylePreset, setStylePreset] = useState("storytelling");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isNewProjectModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !topic.trim()) {
      setErrorMsg("Vui lòng điền đầy đủ tiêu đề và chủ đề kịch bản.");
      return;
    }

    try {
      await createProjectMutation.mutateAsync({
        name,
        topic: `${topic} [Style: ${stylePreset}]`,
        target_language: targetLanguage,
        duration_target_seconds: Number(duration),
      });
      setNewProjectModalOpen(false);
      setName("");
      setTopic("");
      setErrorMsg(null);
    } catch (error) {
      setErrorMsg(
        error instanceof Error ? error.message : "Không thể khởi tạo dự án mới."
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-md bg-nle-surface border-nle-border shadow-2xl overflow-hidden">
        <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between bg-nle-panel">
          <div className="flex items-center space-x-2">
            <FolderPlus className="w-5 h-5 text-nle-cyan" />
            <CardTitle className="text-sm font-bold text-white">
              Tạo Dự Án Sản Xuất Mới
            </CardTitle>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setNewProjectModalOpen(false)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="p-4 space-y-3 text-xs">
            {errorMsg && (
              <div className="p-2 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
                {errorMsg}
              </div>
            )}

            <div>
              <label className="text-gray-300 font-semibold block mb-1">
                Tiêu đề dự án (Production Title):
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ví dụ: Bí Mật Edward Bernays 1928..."
                required
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white focus:border-nle-cyan focus:outline-none"
              />
            </div>

            <div>
              <label className="text-gray-300 font-semibold block mb-1">
                Chủ đề / Góc tiếp cận (Topic & Core Angle):
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                rows={3}
                placeholder="Ví dụ: Cách thức thí nghiệm tâm lý truyền thông thay đổi thói quen mua sắm toàn cầu..."
                required
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white focus:border-nle-cyan focus:outline-none resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-300 font-semibold block mb-1 flex items-center">
                  <Globe className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
                  Ngôn ngữ đích:
                </label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white"
                >
                  <option value="vi">Tiếng Việt (vi-VN)</option>
                  <option value="en">English (en-US)</option>
                  <option value="ja">Japanese (ja-JP)</option>
                  <option value="ko">Korean (ko-KR)</option>
                </select>
              </div>

              <div>
                <label className="text-gray-300 font-semibold block mb-1 flex items-center">
                  <Clock className="w-3.5 h-3.5 mr-1 text-amber-400" />
                  Thời lượng mục tiêu:
                </label>
                <input
                  type="number"
                  value={duration}
                  min={10}
                  max={1800}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white"
                />
              </div>
            </div>

            <div>
              <label className="text-gray-300 font-semibold block mb-1 flex items-center">
                <FileText className="w-3.5 h-3.5 mr-1 text-nle-violet" />
                Phong cách kịch bản (Script Style Preset):
              </label>
              <select
                value={stylePreset}
                onChange={(e) => setStylePreset(e.target.value)}
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white"
              >
                <option value="storytelling">Storytelling (Kể chuyện truyền cảm hứng)</option>
                <option value="educational">Educational (Giải thích khoa học dễ hiểu)</option>
                <option value="news">News Flash (Tin tức nhanh & kịch tính)</option>
                <option value="dramatic">Dramatic Mystery (Bí ẩn & giật gân)</option>
                <option value="minimalist">Minimalist (Ngắn gọn, súc tích)</option>
              </select>
            </div>

            <Button
              type="submit"
              variant="neon"
              disabled={createProjectMutation.isPending}
              className="w-full text-xs h-8 mt-2"
            >
              {createProjectMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
              )}
              Khởi Tạo Dự Án Pipeline
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
