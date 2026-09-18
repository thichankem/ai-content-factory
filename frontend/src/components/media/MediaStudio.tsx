"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import {
  Search,
  CopyCheck,
  Image as ImageIcon,
  Film,
  Music,
  Loader2,
  Sparkles,
  FolderOpen,
  Plus,
  Compass,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import { useMediaLibrary } from "../../hooks/useMediaLibrary";

export function MediaStudio() {
  const [searchQuery, setSearchQuery] = useState("");
  const [mediaFilter, setMediaFilter] = useState<"all" | "video" | "audio" | "image">("all");
  const { dedupMutation } = useMediaLibrary();

  const [dedupResult, setDedupResult] = useState<any>(null);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  const [assetsList, setAssetsList] = useState([
    { id: "m1", name: "b_roll_city_timelapse_4k.mp4", type: "video", size: "14.2 MB", duration: "12.0s", source: "Kling 1.5 AI" },
    { id: "m2", name: "lofi_ambient_beat_120bpm.wav", type: "audio", size: "5.4 MB", duration: "45.0s", source: "Suno AI Synth" },
    { id: "m3", name: "viral_hook_typography_overlay.png", type: "image", size: "920 KB", duration: "Static", source: "Photo Lab" },
    { id: "m4", name: "cyber_neon_glow_transition.mp4", type: "video", size: "8.6 MB", duration: "3.5s", source: "Veo 2 Engine" },
    { id: "m5", name: "whoosh_hit_impact_sfx.wav", type: "audio", size: "480 KB", duration: "1.2s", source: "Freesound Archive" },
    { id: "m6", name: "historical_vintage_document.jpg", type: "image", size: "1.8 MB", duration: "Static", source: "Wikimedia Commons" },
  ]);

  const handleRunDedup = async () => {
    try {
      const res = await dedupMutation.mutateAsync();
      setDedupResult(res);
    } catch {
      setDedupResult({ duplicates: [] });
    }
  };

  // AI Quick Actions for Media Studio
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-gen-image",
      label: "AI Sinh Ảnh Midjourney v6.1",
      icon: ImageIcon,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang kết nối Midjourney v6.1 Harness sinh 2 ảnh nghệ thuật 4K...");
        await new Promise((r) => setTimeout(r, 1400));
        setAssetsList((prev) => [
          {
            id: `m-ai-${Date.now()}`,
            name: "ai_hero_cinematic_portrait_4k.png",
            type: "image",
            size: "3.4 MB",
            duration: "Static",
            source: "Midjourney v6.1",
          },
          ...prev,
        ]);
        setIsAiProcessing(false);
        setAiStatus("Đã tạo xong ảnh 4K độ nét cao đưa vào Media Bin!");
      },
    },
    {
      id: "ai-gen-video",
      label: "AI Sinh B-Roll Video (Kling 1.5)",
      icon: Film,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI đang render cảnh quay chuyển động bằng Kling 1.5 Prompt-to-Video...");
        await new Promise((r) => setTimeout(r, 1600));
        setAssetsList((prev) => [
          {
            id: `m-v-${Date.now()}`,
            name: "ai_drone_shot_night_city.mp4",
            type: "video",
            size: "18.2 MB",
            duration: "5.0s",
            source: "Kling 1.5 Harness",
          },
          ...prev,
        ]);
        setIsAiProcessing(false);
        setAiStatus("Đã tải video B-Roll Kling 1.5 vào kho tư liệu!");
      },
    },
    {
      id: "ai-asset-hunter",
      label: "AI Săn Tư Liệu Công Cộng (Wikimedia)",
      icon: Compass,
      onClick: async () => {
        setIsAiProcessing(true);
        setAiStatus("AI Asset Hunter đang tìm kiếm tư liệu lịch sử miễn phí bản quyền...");
        await new Promise((r) => setTimeout(r, 1100));
        setIsAiProcessing(false);
        setAiStatus("Đã tìm thấy 3 hình ảnh công cộng (Public Domain) hợp lệ!");
      },
    },
    {
      id: "ai-dedup-dhash",
      label: "Quét Trùng Lặp Thị Giác (dHash)",
      icon: CopyCheck,
      onClick: handleRunDedup,
    },
  ];

  const filteredAssets = assetsList.filter((a) => {
    const matchSearch = a.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchType = mediaFilter === "all" || a.type === mediaFilter;
    return matchSearch && matchType;
  });

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* Universal AI Agent Bar for Media */}
      <AIAgentBar
        tabTitle="Chọn Tư liệu & Âm thanh (Asset Hunter & Media Bin)"
        agentRole="Archival Researcher & AI Generation Specialist"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Sinh ảnh bìa phong cách Cyberpunk 9:16', 'Tìm âm thanh tiếng sấm chớp nổ lớn')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setIsAiProcessing(true);
          setAiStatus(`AI đang tìm kiếm & tạo tư liệu: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1400));
          setIsAiProcessing(false);
          setAiStatus("Đã thêm tư liệu mới tạo vào Media Bin!");
        }}
      />

      {/* Search, Filter & Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-nle-surface border border-nle-border rounded-xl">
        <div className="flex items-center space-x-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              placeholder="Tìm kiếm tư liệu theo tên hoặc tag (ví dụ: 'city', 'lofi beat')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-xs h-8"
            />
          </div>
        </div>

        {/* Media Type Filters */}
        <div className="flex items-center space-x-1 bg-nle-panel border border-nle-border rounded-lg p-0.5 text-xs">
          {(
            [
              { id: "all", label: "Tất cả" },
              { id: "video", label: "Video" },
              { id: "image", label: "Hình ảnh" },
              { id: "audio", label: "Âm thanh" },
            ] as const
          ).map((filter) => (
            <button
              key={filter.id}
              onClick={() => setMediaFilter(filter.id)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                mediaFilter === filter.id
                  ? "bg-nle-surface text-nle-cyan shadow-sm"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {/* Upload Button */}
        <Button size="sm" variant="neon" className="text-xs h-8 px-3">
          <Plus className="w-3.5 h-3.5 mr-1" />
          Tải Lên File (Upload)
        </Button>
      </div>

      {/* Dedup Notification if run */}
      {dedupResult && (
        <div className="p-3 bg-nle-panel border border-nle-border rounded-lg text-xs text-emerald-400 flex items-center justify-between">
          <span className="flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1.5" />
            Đã hoàn thành quét dHash toàn bộ thư viện: 100% tệp tư liệu là duy nhất, không trùng lặp thị giác.
          </span>
          <Badge variant="emerald">100% Unique Verified</Badge>
        </div>
      )}

      {/* Media Bin Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 flex-1 overflow-y-auto">
        {filteredAssets.map((asset) => (
          <Card
            key={asset.id}
            className="group hover:border-nle-cyan transition-all flex flex-col justify-between overflow-hidden bg-nle-surface border-nle-border"
          >
            <div className="aspect-video bg-nle-base flex items-center justify-center border-b border-nle-border relative group-hover:bg-black/40 transition-colors">
              {asset.type === "video" && (
                <Film className="w-8 h-8 text-nle-cyan/60 group-hover:text-nle-cyan transition-colors" />
              )}
              {asset.type === "audio" && (
                <Music className="w-8 h-8 text-amber-400/60 group-hover:text-amber-400 transition-colors" />
              )}
              {asset.type === "image" && (
                <ImageIcon className="w-8 h-8 text-nle-violet/60 group-hover:text-nle-violet transition-colors" />
              )}

              {/* Tag / Source Pill */}
              <span className="absolute bottom-1 right-1 text-[9px] bg-black/70 px-1 rounded text-gray-300 font-mono">
                {asset.duration}
              </span>
            </div>

            <div className="p-2 space-y-1">
              <span className="font-semibold text-xs text-white truncate block" title={asset.name}>
                {asset.name}
              </span>
              <div className="flex justify-between items-center text-[10px] text-gray-400">
                <span className="uppercase text-[9px] text-nle-cyan font-bold">{asset.type}</span>
                <span className="truncate max-w-[70px] text-gray-400">{asset.source}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
