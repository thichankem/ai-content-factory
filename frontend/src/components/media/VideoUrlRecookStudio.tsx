"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useUIStore } from "@/stores/useUIStore";
import { useTimelineStore } from "@/stores/useTimelineStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useProjects } from "@/hooks/useProjects";
import { useMediaRecook } from "@/hooks/useMediaLibrary";
import { makeScenes } from "@/lib/scenes";
import { MediaItem, ReCookMode, TranscriptSegment } from "@/types/media";
import {
  DownloadCloud,
  Link as LinkIcon,
  Sparkles,
  FileText,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Zap,
  Layers,
  ArrowRight,
  ShieldCheck,
  Flame,
  Volume2,
  Clock,
  Film,
  Scissors,
} from "lucide-react";

interface VideoUrlRecookStudioProps {
  /** Called with the library item once a clip has really been ingested. */
  onAddMediaAsset?: (asset: MediaItem) => void;
}

/** ``"45s"`` → ``45``. ``undefined`` lets the backend pick its own default. */
function parseDurationSeconds(value: string): number | undefined {
  const seconds = Number.parseInt(value.replace(/[^\d]/g, ""), 10);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : undefined;
}

/** `null` stays `null`: the backend did not measure a duration. */
function formatDuration(seconds?: number | null): string {
  return seconds == null ? "chưa đo" : `${seconds.toFixed(1)}s`;
}

function formatResolution(media: MediaItem): string {
  return media.width && media.height ? `${media.width}x${media.height}` : "chưa đo";
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "chưa đo";
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatClock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const mm = String(Math.floor(whole / 60)).padStart(2, "0");
  const ss = String(whole % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function formatSegmentRange(segment: TranscriptSegment): string {
  return `${formatClock(segment.start_seconds)} - ${formatClock(segment.end_seconds)}`;
}

export function VideoUrlRecookStudio({ onAddMediaAsset }: VideoUrlRecookStudioProps) {
  const { setActiveTab } = useUIStore();
  const { setScenes } = useTimelineStore();
  const { currentProject } = useProjectStore();
  const { saveScriptMutation } = useProjects();
  const { ingestMutation, recookMutation } = useMediaRecook();

  const [inputUrl, setInputUrl] = useState("");
  /*
   * Nothing is pre-filled and nothing is invented. This screen used to open on a
   * hand-written "How Neural Networks Work in 60 Seconds" item — title, duration,
   * resolution, size, transcript and four timed segments — presented as an
   * already-ingested clip, and its re-cook output was a second hardcoded script.
   * Both now start empty and are filled only by a server response.
   */
  const [downloadedMedia, setDownloadedMedia] = useState<MediaItem | null>(null);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  // Re-Cook Settings
  const [recookMode, setRecookMode] = useState<ReCookMode>("balanced");
  const [recookStyle, setRecookStyle] = useState<"viral-hook" | "storytelling" | "shocking-facts">("viral-hook");
  const [targetDuration, setTargetDuration] = useState("45s");

  // Re-cooked Output — the script the backend wrote, or nothing at all.
  const [recookedScript, setRecookedScript] = useState<string>("");
  const [recookedProjectId, setRecookedProjectId] = useState<string | null>(null);
  const [recookError, setRecookError] = useState<string | null>(null);

  const isIngesting = ingestMutation.isPending;
  const isRecooking = recookMutation.isPending;

  /**
   * Download the reference clip through the backend.
   *
   * Replaces a raw ``fetch`` to a hardcoded ``http://127.0.0.1:8000`` whose
   * non-OK branch, and whose catch block, both fabricated a clip — a title, a
   * duration, a resolution and a Vietnamese transcript — and announced success.
   * A failure now reads as a failure.
   */
  const handleIngestUrl = async () => {
    const url = inputUrl.trim();
    if (!url) return;
    setIngestStatus(null);
    setIngestError(null);
    try {
      const media = await ingestMutation.mutateAsync({ url, language: "vi" });
      setDownloadedMedia(media);
      onAddMediaAsset?.(media);
      setIngestStatus(
        media.transcription
          ? `Đã nạp ${media.filename} vào Kho Tư Liệu kèm bản bóc tách lời thoại.`
          : `Đã nạp ${media.filename} vào Kho Tư Liệu. Chưa có bản bóc tách lời thoại — chạy phiên âm cho tư liệu này nếu cần kịch bản nguồn.`
      );
    } catch (error) {
      setDownloadedMedia(null);
      setIngestError(
        `Không nạp được video từ URL: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };

  /**
   * Re-cut the ingested clip into a new project.
   *
   * This used to pick one of three hardcoded scripts by mode, after a
   * ``setTimeout``, and reset a "copy risk" number to zero. The real endpoint
   * returns the new project *and* the script it wrote, so both are recorded here.
   */
  const handleRunRecook = async () => {
    if (!downloadedMedia) {
      setRecookError("Chưa nạp được video nào — không có gì để tái cấu trúc.");
      return;
    }
    setRecookError(null);
    try {
      const result = await recookMutation.mutateAsync({
        mediaId: downloadedMedia.id,
        payload: {
          new_title: downloadedMedia.filename,
          mode: recookMode,
          script_style: recookStyle,
          target_seconds: parseDurationSeconds(targetDuration),
          language: "vi",
        },
      });
      setRecookedScript(result.script);
      setRecookedProjectId(result.project_id);
    } catch (error) {
      setRecookedScript("");
      setRecookedProjectId(null);
      setRecookError(
        `Tái cấu trúc thất bại: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };

  /**
   * Hand the re-cooked script to the Script Studio.
   *
   * The re-cook endpoint already created a project and already wrote the script
   * to it server-side, so the only local work left is to select that project and
   * lay down placeholder scenes for the timeline. The previous version wrote the
   * script into the browser store only — under a locally-minted ``draft-`` id —
   * so the script was there to look at and nowhere to be found.
   */
  const handleApplyToScriptAndTimeline = () => {
    if (!recookedScript.trim()) {
      setRecookError("Chưa có kịch bản tái cấu trúc để chuyển sang Script Studio.");
      return;
    }
    setScenes(
      makeScenes([
        { label: "Scene 1: Viral Hook", duration: 3.5, text: "Hook giật gân 3 giây đầu", grade: "cyberpunk" },
        { label: "Scene 2: Core Proof", duration: 12.0, text: "Bằng chứng & Giải mã cơ chế", grade: "teal-orange" },
        { label: "Scene 3: Unexpected Turn", duration: 10.0, text: "Cú lật bất ngờ, xóa tan định kiến", grade: "noir" },
        { label: "Scene 4: Call To Action", duration: 6.5, text: "Kêu gọi hành động & Tương tác", grade: "none" },
      ])
    );
    setActiveTab("script");
  };

  return (
    <div className="flex flex-col h-full space-y-3 overflow-y-auto">
      {/* Top Header Card */}
      <div className="bg-nle-panel border border-nle-border rounded-xl p-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-lg bg-nle-surface flex items-center justify-center text-rose-400 border border-nle-border">
            <DownloadCloud className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-xs text-white flex items-center space-x-1.5">
              <span>External Video Ingestion &amp; Content Re-Cook Engine</span>
              <Badge variant="violet" className="text-[9px] uppercase px-1">
                AI Transformer
              </Badge>
            </h3>
            <p className="text-[11px] text-gray-400">
              Khai thác video từ link bên ngoài (TikTok, YouTube, Shorts, MP4) • Bóc tách lời thoại • Tái cấu trúc &amp; biến tấu kịch bản độc quyền (0% Copy-Risk)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge variant="cyan" className="text-xs px-2.5 py-1 flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
            <span>Anti-Plagiarism Guaranteed</span>
          </Badge>
        </div>
      </div>

      {/* URL Input Bar */}
      <div className="bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col space-y-2">
        <label className="text-xs font-semibold text-gray-300 flex items-center space-x-1.5">
          <LinkIcon className="w-3.5 h-3.5 text-nle-cyan" />
          <span>Nhập Đường Dẫn Video (URL Extractor):</span>
        </label>

        <div className="flex items-center space-x-2">
          <div className="relative flex-1">
            <Input
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="Dán link TikTok, YouTube Shorts, Reels, hoặc liên kết file .mp4..."
              className="bg-nle-base border-nle-border text-xs pr-20 font-mono text-gray-200 h-9"
            />
          </div>

          <Button
            size="sm"
            variant="neon"
            disabled={isIngesting}
            onClick={handleIngestUrl}
            className="h-9 text-xs shrink-0"
          >
            {isIngesting ? (
              <span className="flex items-center">
                <RotateCcw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Đang Tải...
              </span>
            ) : (
              <span className="flex items-center">
                <DownloadCloud className="w-3.5 h-3.5 mr-1.5" />
                Trích Xuất &amp; Nạp Tư Liệu
              </span>
            )}
          </Button>
        </div>

        {/* Quick Suggestions */}
        <div className="flex items-center space-x-2 pt-1">
          <span className="text-[10px] text-gray-500 font-semibold">Gợi ý mẫu:</span>
          <button
            onClick={() => setInputUrl("https://www.tiktok.com/@techinsider/video/7289123456789")}
            className="text-[10px] text-nle-cyan/80 hover:text-nle-cyan hover:underline bg-nle-panel px-2 py-0.5 rounded"
          >
            📱 TikTok AI Tech Explainer (9:16)
          </button>
          <button
            onClick={() => setInputUrl("https://www.youtube.com/shorts/sample_history_video")}
            className="text-[10px] text-nle-cyan/80 hover:text-nle-cyan hover:underline bg-nle-panel px-2 py-0.5 rounded"
          >
            🎥 YouTube Shorts History Doc
          </button>
        </div>

        {ingestStatus && (
          <div className="text-xs text-emerald-400 bg-emerald-950/30 border border-emerald-500/30 p-2 rounded-lg flex items-center space-x-1.5 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{ingestStatus}</span>
          </div>
        )}
      </div>

      {/* Main Dual Workspace: Left Video Deconstruction & Transcript | Right AI Re-Cook Studio */}
      {downloadedMedia && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 flex-1">
          {/* Left Column: Video Info & Raw Transcript (5 Cols) */}
          <div className="lg:col-span-5 bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col space-y-3 overflow-y-auto">
            <div className="flex items-center justify-between pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center space-x-1.5">
                <Film className="w-3.5 h-3.5 text-nle-cyan" />
                <span>Video Gốc Đã Khai Thác</span>
              </span>
              <Badge variant="outline" className="text-[9px] font-mono text-emerald-400 border-emerald-500/30">
                {formatResolution(downloadedMedia)}
              </Badge>
            </div>

            {/* Video Meta Box */}
            <div className="bg-nle-base rounded-lg p-3 border border-nle-border space-y-1.5">
              <div className="text-xs font-bold text-gray-200 line-clamp-1">{downloadedMedia.filename}</div>
              <div className="flex items-center space-x-3 text-[11px] text-gray-400">
                <span className="flex items-center"><Clock className="w-3 h-3 mr-1 text-gray-500" />{formatDuration(downloadedMedia.duration_seconds)}</span>
                <span className="flex items-center"><Layers className="w-3 h-3 mr-1 text-gray-500" />{formatBytes(downloadedMedia.size_bytes)}</span>
                <span className="text-nle-cyan">{downloadedMedia.source || downloadedMedia.mime}</span>
              </div>
            </div>

            {/* Timed Segments List — straight from the library item. */}
            <div className="flex-1 flex flex-col space-y-1.5">
              <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                <span>Lời Thoại Bóc Tách</span>
                <Badge variant="cyan" className="text-[9px]">
                  {downloadedMedia.transcript_segments.length} đoạn
                </Badge>
              </span>

              {downloadedMedia.transcript_segments.length === 0 ? (
                <p className="text-[11px] text-gray-500 p-2 rounded bg-nle-base border border-dashed border-nle-border">
                  Tư liệu này chưa được phiên âm. Chạy phiên âm (STT) trong Media Library rồi tải lại
                  màn hình này để có lời thoại theo mốc thời gian.
                </p>
              ) : (
                <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                  {downloadedMedia.transcript_segments.map((seg: TranscriptSegment, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-nle-base border border-nle-border/60 text-xs flex flex-col space-y-1"
                    >
                      <span className="text-[10px] font-mono text-nle-cyan font-semibold">
                        {formatSegmentRange(seg)}
                      </span>
                      <p className="text-gray-300 text-[11px] leading-relaxed">{seg.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: AI Re-Cook Transformer Studio (7 Cols) */}
          <div className="lg:col-span-7 bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col space-y-3 overflow-y-auto">
            <div className="flex items-center justify-between pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                <span>AI Content Re-Cook • Xào Nấu &amp; Tái Bản Quyền Kịch Bản</span>
              </span>

              {/*
                The copy-risk meter that used to sit here showed "Trùng Lặp: 0%"
                — hardcoded, from a state variable nothing ever wrote to. There is
                no similarity score in the re-cook contract, so the badge is gone
                rather than permanently reassuring.
              */}
              <Badge variant="outline" className="text-[10px] text-gray-400 border-nle-border">
                {recookedProjectId
                  ? `Dự án đã tạo: ${recookedProjectId}`
                  : "Chưa tái cấu trúc"}
              </Badge>
            </div>

            {/* Transform Controls Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 bg-nle-base p-2.5 rounded-lg border border-nle-border text-xs">
              {/* Mode */}
              <div>
                <label className="text-[10px] text-gray-400 font-semibold block mb-1">Chế Độ Biến Tấu:</label>
                <select
                  value={recookMode}
                  onChange={(e) => setRecookMode(e.target.value as any)}
                  className="w-full bg-nle-panel border border-nle-border rounded px-2 py-1 text-xs text-white outline-none"
                >
                  <option value="balanced">⚖️ Cân Bằng (Balanced)</option>
                  <option value="condense">✂️ Rút Gọn Cô Đọng (Condense)</option>
                  <option value="expand">📈 Mở Rộng Phân Tích (Expand)</option>
                </select>
              </div>

              {/* Style */}
              <div>
                <label className="text-[10px] text-gray-400 font-semibold block mb-1">Văn Phong (Hook Style):</label>
                <select
                  value={recookStyle}
                  onChange={(e) => setRecookStyle(e.target.value as any)}
                  className="w-full bg-nle-panel border border-nle-border rounded px-2 py-1 text-xs text-white outline-none"
                >
                  <option value="viral-hook">🔥 Giật Gân 3s (Viral Hook)</option>
                  <option value="storytelling">📖 Kể Chuyện Kịch Tính (Story)</option>
                  <option value="shocking-facts">⚡ Sự Thật Gây Sốc (Facts)</option>
                </select>
              </div>

              {/* Target Duration */}
              <div>
                <label className="text-[10px] text-gray-400 font-semibold block mb-1">Thời Lượng Dự Kiến:</label>
                <select
                  value={targetDuration}
                  onChange={(e) => setTargetDuration(e.target.value)}
                  className="w-full bg-nle-panel border border-nle-border rounded px-2 py-1 text-xs text-white outline-none"
                >
                  <option value="30s">30 Giây (TikTok Fast)</option>
                  <option value="45s">45 Giây (Chuẩn Giữ Chân)</option>
                  <option value="60s">60 Giây (Full Short)</option>
                  <option value="90s">90 Giây (Mở Rộng)</option>
                </select>
              </div>
            </div>

            {/* Run Re-Cook Button */}
            <div className="flex justify-between items-center">
              <span className="text-[11px] text-gray-400">
                Tự động thay thế cấu trúc câu, đảo lật góc nhìn &amp; tạo Hook độc quyền:
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={isRecooking}
                onClick={handleRunRecook}
                className="text-xs border-rose-500/40 text-rose-300 hover:bg-rose-950/30"
              >
                {isRecooking ? (
                  <span className="flex items-center"><RotateCcw className="w-3 h-3 mr-1 animate-spin" /> Đang Xào Nấu...</span>
                ) : (
                  <span className="flex items-center"><Sparkles className="w-3 h-3 mr-1 text-rose-400" /> Tái Cấu Trúc Script Ngay</span>
                )}
              </Button>
            </div>

            {/* Re-Cooked Script Editor / Preview */}
            <div className="flex-1 flex flex-col space-y-1">
              <textarea
                value={recookedScript}
                onChange={(e) => setRecookedScript(e.target.value)}
                rows={9}
                className="w-full flex-1 p-3 bg-nle-base border border-nle-border rounded-lg text-xs text-gray-200 font-sans leading-relaxed resize-none outline-none focus:border-nle-cyan/50"
              />
            </div>

            {/* Action Bar: Send to Script and Production Timeline */}
            <div className="pt-2 border-t border-nle-border flex flex-col sm:flex-row items-center justify-between gap-2">
              <div className="flex items-center space-x-2 text-[11px] text-gray-400">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Sẵn sàng đưa vào Pipeline sản xuất 2 cửa duyệt</span>
              </div>

              <Button
                size="sm"
                variant="neon"
                onClick={handleApplyToScriptAndTimeline}
                className="text-xs font-bold w-full sm:w-auto"
              >
                <Zap className="w-3.5 h-3.5 mr-1.5" />
                Chuyển Sang Kịch Bản Để Sản Xuất Video Mới
                <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
