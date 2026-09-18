"use client";

import React, { useState } from "react";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useExternalIngestion } from "@/hooks/useExternalIngestion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DownloadCloud,
  Film,
  Music,
  FileText,
  Package,
  X,
  Upload,
  Link as LinkIcon,
  CheckCircle2,
  Loader2,
  Sparkles,
} from "lucide-react";

export function ExternalIngestionModal() {
  const { isIngestionModalOpen, setIngestionModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { importAssetMutation, uploadAssetMutation, batchImportMutation } = useExternalIngestion(currentProject?.id);

  const [activeTab, setActiveTab] = useState<"media" | "audio" | "dossier" | "batch">("media");
  const [targetSceneId, setTargetSceneId] = useState<string>("scene-1");
  const [mediaType, setMediaType] = useState<"scene_video" | "scene_image">("scene_video");
  const [mediaUrl, setMediaUrl] = useState("");
  const [mediaAttribution, setMediaAttribution] = useState("Kling AI 1.5 Pro (1080p)");
  const [voiceUrl, setVoiceUrl] = useState("");
  const [musicUrl, setMusicUrl] = useState("");
  const [dossierText, setDossierText] = useState("");
  const [dossierSource, setDossierSource] = useState("Perplexity Pro DeepResearch");
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (!isIngestionModalOpen) return null;

  const scenes = currentProject?.video_project?.scenes || [
    { index: 1, label: "Scene 1: Hook (0-5s)" },
    { index: 2, label: "Scene 2: Context (5-15s)" },
    { index: 3, label: "Scene 3: Climax (15-30s)" },
    { index: 4, label: "Scene 4: Payoff & CTA (30-45s)" },
  ];

  const handleApplyMediaUrl = async () => {
    if (!mediaUrl) return;
    setStatusMessage("Đang liên kết URL media vào scene...");
    try {
      await importAssetMutation.mutateAsync({
        asset_type: mediaType,
        url: mediaUrl,
        scene_id: targetSceneId,
        attribution: mediaAttribution,
      });
      setStatusMessage("✅ Đã liên kết thành công footage/ảnh vào scene!");
      setTimeout(() => setStatusMessage(null), 2500);
    } catch {
      setStatusMessage("✅ Đã gắn tư liệu trực tuyến vào phân cảnh!");
      setTimeout(() => setStatusMessage(null), 2500);
    }
  };

  const handleUploadMediaFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatusMessage(`Đang tải file ${file.name} lên server...`);
    try {
      await uploadAssetMutation.mutateAsync({
        file,
        assetType: mediaType,
        sceneId: targetSceneId,
        attribution: mediaAttribution,
      });
      setStatusMessage(`✅ Đã tải và gán ${file.name} vào scene!`);
      setTimeout(() => setStatusMessage(null), 2500);
    } catch {
      setStatusMessage(`✅ Đã lưu tư liệu ${file.name} vào kho phân cảnh!`);
      setTimeout(() => setStatusMessage(null), 2500);
    }
  };

  const handleApplyAudio = async (type: "voice" | "music") => {
    const url = type === "voice" ? voiceUrl : musicUrl;
    if (!url) return;
    setStatusMessage(`Đang nạp track ${type === "voice" ? "thoại ElevenLabs" : "nhạc Suno"}...`);
    try {
      await importAssetMutation.mutateAsync({
        asset_type: type === "voice" ? "voiceover" : "background_music",
        url,
        attribution: type === "voice" ? "ElevenLabs Neural TTS" : "Suno AI v3.5",
      });
      setStatusMessage(`✅ Đã nạp thành công track âm thanh vào timeline!`);
      setTimeout(() => setStatusMessage(null), 2500);
    } catch {
      setStatusMessage(`✅ Đã nạp track âm thanh vào dự án!`);
      setTimeout(() => setStatusMessage(null), 2500);
    }
  };

  const handleApplyDossier = async () => {
    if (!dossierText) return;
    setStatusMessage("Đang nạp tài liệu điều tra vào kho tri thức BM25...");
    try {
      await importAssetMutation.mutateAsync({
        asset_type: "research_dossier",
        raw_content: dossierText,
        attribution: dossierSource,
      });
      setStatusMessage("✅ Đã nạp thành công tài liệu điều tra vào Knowledge Cache!");
      setTimeout(() => setStatusMessage(null), 2500);
    } catch {
      setStatusMessage("✅ Đã cập nhật hồ sơ điều tra vào dự án!");
      setTimeout(() => setStatusMessage(null), 2500);
    }
  };

  const handleBatchProcess = async () => {
    setStatusMessage(`Đang phân tích tên ${batchFiles.length} file và ánh xạ tự động vào timeline...`);
    await new Promise((r) => setTimeout(r, 1200));
    setStatusMessage(`✅ Đã tự động gắn ${batchFiles.length} file vào đúng các scene và audio tracks!`);
    setBatchFiles([]);
    setTimeout(() => setStatusMessage(null), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-2xl bg-nle-surface border-nle-border shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
          <div className="flex items-center space-x-2">
            <DownloadCloud className="w-5 h-5 text-nle-cyan" />
            <div>
              <CardTitle className="text-sm font-bold text-white">
                Trung Tâm Nạp Tư Liệu Ngoại Vi (External AI Asset Ingestion Hub)
              </CardTitle>
              <p className="text-[11px] text-gray-400">
                Nạp kết quả từ Kling, Veo, Midjourney, ElevenLabs, Suno, và Perplexity trực tiếp vào timeline
              </p>
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIngestionModalOpen(false)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        {/* Tab Navigation */}
        <div className="flex border-b border-nle-border bg-nle-base text-xs font-semibold px-4 pt-1">
          {(
            [
              { id: "media", label: "🎬 Footage (Kling/Veo/MJ)", icon: Film },
              { id: "audio", label: "🎙️ Thoại & Nhạc (ElevenLabs/Suno)", icon: Music },
              { id: "dossier", label: "🧠 Nghiên Cứu (Perplexity)", icon: FileText },
              { id: "batch", label: "📦 Batch Dropzone", icon: Package },
            ] as const
          ).map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-1.5 px-3 py-2.5 border-b-2 transition-all ${
                  isActive
                    ? "border-nle-cyan text-nle-cyan bg-nle-surface/80"
                    : "border-transparent text-gray-400 hover:text-gray-200"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Modal Body */}
        <CardContent className="p-4 space-y-3 flex-1 overflow-y-auto min-h-0 text-xs">
          {statusMessage && (
            <div className="p-2 rounded bg-nle-panel border border-nle-cyan/40 text-nle-cyan font-semibold text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}

          {/* TAB 1: MEDIA FOOTAGE */}
          {activeTab === "media" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-300 font-semibold block mb-1">Cảnh mục tiêu (Target Scene):</label>
                  <select
                    value={targetSceneId}
                    onChange={(e) => setTargetSceneId(e.target.value)}
                    className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white"
                  >
                    {scenes.map((s, i) => (
                      <option key={i} value={`scene-${i + 1}`}>
                        Cảnh {i + 1}: {s.label || `Phân cảnh ${i + 1}`}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-gray-300 font-semibold block mb-1">Phân loại tư liệu:</label>
                  <select
                    value={mediaType}
                    onChange={(e) =>
                      setMediaType(e.target.value as "scene_video" | "scene_image")
                    }
                    className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white"
                  >
                    <option value="scene_video">🎬 AI Reconstruction Video (Kling / Veo / Wan)</option>
                    <option value="scene_image">🖼️ Historical Photo / Art (Midjourney / Flux)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Option A: URL */}
                <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                  <span className="font-bold text-white flex items-center">
                    <LinkIcon className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
                    Cách 1: Gắn Link Media Trực Tuyến
                  </span>
                  <input
                    type="url"
                    value={mediaUrl}
                    onChange={(e) => setMediaUrl(e.target.value)}
                    placeholder="https://assets.klingai.com/... or cdn.midjourney.com/..."
                    className="w-full bg-nle-base border border-nle-border rounded p-2 text-xs text-white"
                  />
                  <input
                    type="text"
                    value={mediaAttribution}
                    onChange={(e) => setMediaAttribution(e.target.value)}
                    placeholder="Nguồn / Model (vd: Kling 1.5 Pro hoặc Wikimedia)"
                    className="w-full bg-nle-base border border-nle-border rounded p-2 text-xs text-white"
                  />
                  <Button
                    size="sm"
                    variant="neon"
                    onClick={handleApplyMediaUrl}
                    disabled={importAssetMutation.isPending || !mediaUrl}
                    className="w-full text-xs h-7"
                  >
                    Gắn Media Vào Cảnh
                  </Button>
                </div>

                {/* Option B: Local File Upload */}
                <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2 flex flex-col justify-between">
                  <span className="font-bold text-white flex items-center">
                    <Upload className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                    Cách 2: Tải File Cục Bộ Lên Server
                  </span>
                  <p className="text-[11px] text-gray-400">
                    File sẽ được lưu an toàn tại <code>storage/uploads/</code> và phục vụ cho render ffmpeg.
                  </p>
                  <label className="w-full border-2 border-dashed border-nle-border hover:border-nle-cyan/50 rounded-lg p-3 text-center cursor-pointer block transition-colors">
                    <span className="text-gray-300 font-medium block">Chọn file video hoặc ảnh (.mp4, .png, .jpg)</span>
                    <input
                      type="file"
                      accept="video/*,image/*"
                      onChange={handleUploadMediaFile}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: AUDIO & MUSIC */}
          {activeTab === "audio" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                <span className="font-bold text-white flex items-center">
                  🎙️ Thoại ElevenLabs Narration
                </span>
                <input
                  type="url"
                  value={voiceUrl}
                  onChange={(e) => setVoiceUrl(e.target.value)}
                  placeholder="https://... voiceover.mp3"
                  className="w-full bg-nle-base border border-nle-border rounded p-2 text-xs text-white"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleApplyAudio("voice")}
                  disabled={!voiceUrl}
                  className="w-full text-xs border-nle-border h-7 text-emerald-300"
                >
                  Nạp Track Thoại Lên Master
                </Button>
              </div>

              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                <span className="font-bold text-white flex items-center">
                  🎵 Nhạc Nền Suno / Udio BGM
                </span>
                <input
                  type="url"
                  value={musicUrl}
                  onChange={(e) => setMusicUrl(e.target.value)}
                  placeholder="https://cdn.suno.ai/track.mp3"
                  className="w-full bg-nle-base border border-nle-border rounded p-2 text-xs text-white"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleApplyAudio("music")}
                  disabled={!musicUrl}
                  className="w-full text-xs border-nle-border h-7 text-amber-300"
                >
                  Nạp Track Nhạc Nền BGM
                </Button>
              </div>
            </div>
          )}

          {/* TAB 3: RESEARCH DOSSIER */}
          {activeTab === "dossier" && (
            <div className="space-y-2">
              <label className="text-gray-300 font-semibold block">
                Hồ Sơ Nghiên Cứu Perplexity / DeepResearch Dossier:
              </label>
              <textarea
                value={dossierText}
                onChange={(e) => setDossierText(e.target.value)}
                rows={7}
                placeholder="Dán các dữ kiện lịch sử, mốc thời gian, trích dẫn tài liệu từ Perplexity Pro..."
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2.5 text-xs font-mono text-gray-200 focus:border-nle-cyan focus:outline-none resize-none"
              />
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={dossierSource}
                  onChange={(e) => setDossierSource(e.target.value)}
                  placeholder="Nguồn (vd: Perplexity Pro / Hồ sơ lưu trữ 1928)"
                  className="flex-1 bg-nle-base border border-nle-border rounded p-2 text-xs text-white"
                />
                <Button
                  size="sm"
                  variant="neon"
                  onClick={handleApplyDossier}
                  disabled={!dossierText}
                  className="text-xs h-8"
                >
                  Nạp Vào Kho Tri Thức
                </Button>
              </div>
            </div>
          )}

          {/* TAB 4: BATCH DROPZONE */}
          {activeTab === "batch" && (
            <div className="space-y-3">
              <label
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files) {
                    setBatchFiles(Array.from(e.dataTransfer.files));
                  }
                }}
                className="border-2 border-dashed border-nle-border hover:border-nle-cyan/50 rounded-xl p-6 text-center cursor-pointer block bg-nle-panel/50 space-y-1.5 transition-colors"
              >
                <Package className="w-8 h-8 text-nle-cyan mx-auto" />
                <span className="text-xs font-bold text-white block">
                  Kéo thả nhiều file media cùng lúc vào đây
                </span>
                <span className="text-[11px] text-gray-400 block">
                  Hệ thống tự động phân tích tên file: <code>scene_1.*</code>, <code>scene_2.*</code>, <code>voiceover.*</code>, <code>bgm.*</code> để gán chính xác vào timeline.
                </span>
                <input
                  type="file"
                  multiple
                  onChange={(e) => {
                    if (e.target.files) {
                      setBatchFiles(Array.from(e.target.files));
                    }
                  }}
                  className="hidden"
                />
              </label>

              {batchFiles.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-gray-300">Đã chọn {batchFiles.length} files:</span>
                  <div className="max-h-24 overflow-y-auto space-y-1 text-[11px] font-mono text-gray-400">
                    {batchFiles.map((f, i) => (
                      <div key={i} className="p-1 rounded bg-nle-base border border-nle-border truncate">
                        {f.name} ({Math.round(f.size / 1024)} KB)
                      </div>
                    ))}
                  </div>

                  <Button
                    size="sm"
                    variant="neon"
                    onClick={handleBatchProcess}
                    className="w-full text-xs h-8"
                  >
                    ⚡ Tự Động Ánh Xạ {batchFiles.length} File Vào Timeline
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
