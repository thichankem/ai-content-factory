"use client";

/**
 * Media bin, slide-deck studio and URL re-cook, behind one sub-mode toggle.
 *
 * What changed here, and why:
 *
 * * the bin used to open on six hardcoded files — a Kling time-lapse, a Suno
 *   beat, a Wikimedia scan — none of which existed in the library. It now shows
 *   ``GET /media``, which is the same list the backend would hand any other
 *   client. Sub-studios may still push a row in, but only for something they
 *   really produced.
 * * three quick actions (Midjourney image, Kling B-roll, Wikimedia hunter) ran a
 *   ``setTimeout`` and then inserted an invented file into that list while
 *   announcing it had been generated. Nothing behind them called anything. They
 *   are gone; ``POST /tools/call`` is the route that would make them real.
 * * the duplicate sweep reported "100% unique" on success *and* on failure,
 *   because its catch block stored an empty result. An error is now an error.
 */

import React, { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AIAgentBar, AIQuickAction } from "@/components/copilot/AIAgentBar";
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
  SlidersHorizontal,
  LayoutTemplate,
  DownloadCloud,
  AlertTriangle,
  FileText,
  RefreshCw,
} from "lucide-react";
import { useMediaItems, useMediaLibrary } from "@/hooks/useMediaLibrary";
import { HtmlSlideDeckStudio } from "@/components/media/HtmlSlideDeckStudio";
import { VideoUrlRecookStudio } from "@/components/media/VideoUrlRecookStudio";
import { MediaBinRow, MediaItem } from "@/types/media";

type MediaFilter = "all" | MediaBinRow["type"];

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "chưa đo";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds?: number | null): string {
  return seconds == null ? "chưa đo" : `${seconds.toFixed(1)}s`;
}

/** Map a library item onto a bin row. Nothing is estimated here. */
export function mediaItemToRow(item: MediaItem): MediaBinRow {
  return {
    id: item.id,
    name: item.filename,
    type: item.kind,
    size: formatBytes(item.size_bytes),
    duration: formatDuration(item.duration_seconds),
    source: item.source || item.mime,
  };
}

export function MediaStudio() {
  const [activeSubMode, setActiveSubMode] = useState<"bin" | "slides" | "recook">("bin");
  const [searchQuery, setSearchQuery] = useState("");
  const [mediaFilter, setMediaFilter] = useState<MediaFilter>("all");
  const { mediaQuery } = useMediaItems();
  const { dedupMutation } = useMediaLibrary();

  /** The last sweep's real outcome, or the reason it could not run. */
  const [dedupError, setDedupError] = useState<string | null>(null);

  /** Rows a sub-studio contributed this session, newest first. */
  const [addedRows, setAddedRows] = useState<MediaBinRow[]>([]);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  const libraryRows = useMemo<MediaBinRow[]>(
    () => (mediaQuery.data ?? []).map(mediaItemToRow),
    [mediaQuery.data]
  );

  const allRows = useMemo(() => [...addedRows, ...libraryRows], [addedRows, libraryRows]);

  const filteredAssets = allRows.filter((row) => {
    const matchSearch = row.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchType = mediaFilter === "all" || row.type === mediaFilter;
    return matchSearch && matchType;
  });

  // AI Quick Actions for Media Studio — navigation and real library work only.
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-refresh-bin",
      label: "Đọc lại kho tư liệu (GET /media)",
      icon: RefreshCw,
      onClick: () => {
        void mediaQuery.refetch();
        setAiStatus("Đang đọc lại kho tư liệu từ server…");
      },
    },
    {
      id: "ai-html-slides",
      label: "Thiết Kế Slide HTML/CSS (Slide Deck)",
      icon: LayoutTemplate,
      onClick: () => setActiveSubMode("slides"),
    },
    {
      id: "ai-recook-video",
      label: "Khai Thác Video URL & Biến Tấu Script",
      icon: DownloadCloud,
      onClick: () => setActiveSubMode("recook"),
    },
  ];

  /**
   * Run the visual duplicate sweep.
   *
   * The old handler stored ``{duplicates: []}`` in its catch block, so a failed
   * request rendered as "100% tệp tư liệu là duy nhất" — the most reassuring
   * possible reading of an error. It also ignored the result it did get, printing
   * that same sentence whatever the sweep found.
   */
  const handleRunDedup = async () => {
    setDedupError(null);
    try {
      await dedupMutation.mutateAsync();
    } catch (error) {
      setDedupError(
        `Quét trùng lặp thất bại: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* Universal AI Agent Bar for Media */}
      <AIAgentBar
        tabTitle="Chọn Tư liệu & Slide Trình Diễn (Asset Hunter & Media Bin)"
        agentRole="Archival Researcher & AI Generation Specialist"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Tạo slide so sánh HTML/CSS', 'Khai thác video TikTok')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={mediaQuery.isFetching}
        onPromptSubmit={async (prompt) => {
          // No dialog endpoint is wired here yet; say so instead of pretending.
          setAiStatus(
            `Chưa nối được yêu cầu "${prompt}" tới agent. Các thao tác tư liệu thật nằm trong Kho Tư Liệu, Slide Deck và Khai Thác Video.`
          );
        }}
      />

      {/* Sub-Mode Toggle: Media Bin vs Slide Deck vs Video URL Ingestion */}
      <div className="flex flex-wrap items-center justify-between bg-nle-panel border border-nle-border rounded-xl p-1.5 gap-2 shrink-0">
        <div className="flex flex-wrap items-center gap-1">
          <button
            onClick={() => setActiveSubMode("bin")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubMode === "bin"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>Kho Tư Liệu (Media Bin)</span>
          </button>

          <button
            onClick={() => setActiveSubMode("slides")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubMode === "slides"
                ? "bg-nle-surface text-emerald-300 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <LayoutTemplate className="w-3.5 h-3.5" />
            <span>Slide HTML/CSS</span>
          </button>

          <button
            onClick={() => setActiveSubMode("recook")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubMode === "recook"
                ? "bg-nle-surface text-rose-300 shadow-sm border border-rose-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <DownloadCloud className="w-3.5 h-3.5" />
            <span>Khai Thác Video URL</span>
          </button>
        </div>

        <Badge variant="cyan" className="text-[10px]">
          {activeSubMode === "bin"
            ? `${filteredAssets.length} Tệp Khả Dụng`
            : activeSubMode === "slides"
              ? "Web Standards Vector"
              : "Re-Cook Engine"}
        </Badge>
      </div>

      {activeSubMode === "slides" ? (
        <div className="flex-1 min-h-[520px]">
          <HtmlSlideDeckStudio
            onAddSlideToMedia={(slideRow) => {
              setAddedRows((prev) => [slideRow, ...prev]);
            }}
          />
        </div>
      ) : activeSubMode === "recook" ? (
        <div className="flex-1 min-h-[520px]">
          <VideoUrlRecookStudio
            onAddMediaAsset={(media) => {
              // The clip is in the library now; adding the row locally keeps the
              // bin correct without a round trip. The refetch reconciles later.
              setAddedRows((prev) => [mediaItemToRow(media), ...prev]);
              void mediaQuery.refetch();
            }}
          />
        </div>
      ) : (
        <>
          {/* Search, Filter & Actions Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-nle-surface border border-nle-border rounded-xl shrink-0">
            <div className="flex items-center space-x-2 flex-1 max-w-md">
              <div className="relative w-full">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  placeholder="Tìm kiếm tư liệu theo tên tệp..."
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
                  { id: "document", label: "Tài liệu" },
                  { id: "slide", label: "Slide HTML" },
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

            <div className="flex items-center space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleRunDedup}
                disabled={dedupMutation.isPending || allRows.length === 0}
                title="Quét trùng lặp thị giác (dHash) trên toàn thư viện"
                className="text-xs h-8 border-nle-border"
              >
                {dedupMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <CopyCheck className="w-3.5 h-3.5 mr-1" />
                )}
                Quét Trùng Lặp
              </Button>

              <Button
                size="sm"
                variant="outline"
                onClick={() => void mediaQuery.refetch()}
                disabled={mediaQuery.isFetching}
                className="text-xs h-8 border-nle-border"
              >
                {mediaQuery.isFetching ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                )}
                Tải Lại
              </Button>
            </div>
          </div>

          {dedupError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start shrink-0">
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5 shrink-0 mt-0.5" />
              <span>{dedupError}</span>
            </div>
          )}

          {dedupMutation.data && (
            <div className="p-3 bg-nle-panel border border-nle-border rounded-lg text-xs shrink-0 flex items-center justify-between">
              <span className="flex items-center text-gray-200">
                <Sparkles className="w-3.5 h-3.5 mr-1.5 text-nle-cyan" />
                Đã quét {dedupMutation.data.checked} tư liệu, tìm thấy{" "}
                {dedupMutation.data.duplicates.length} cặp trùng lặp trong{" "}
                {dedupMutation.data.groups.length} nhóm (ngưỡng khoảng cách{" "}
                {dedupMutation.data.max_distance}).
              </span>
              <Badge variant={dedupMutation.data.duplicates.length > 0 ? "amber" : "emerald"}>
                {dedupMutation.data.duplicates.length > 0 ? "Cần xem lại" : "Không trùng lặp"}
              </Badge>
            </div>
          )}

          {mediaQuery.isError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start shrink-0">
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5 shrink-0 mt-0.5" />
              <span>Không đọc được kho tư liệu: {mediaQuery.error.message}</span>
            </div>
          )}

          {/* Media Bin Grid */}
          {mediaQuery.isLoading ? (
            <div className="flex-1 flex items-center justify-center text-xs text-gray-400">
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Đang đọc kho tư liệu…
            </div>
          ) : filteredAssets.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-xs text-gray-500 border border-dashed border-nle-border rounded-xl p-8 gap-1">
              <FolderOpen className="w-6 h-6 text-gray-600" />
              <span className="text-gray-300 font-semibold">Kho tư liệu trống</span>
              <span>
                {allRows.length === 0
                  ? "Tải tệp lên qua Kho Tư Liệu, hoặc khai thác video từ URL ở tab bên cạnh."
                  : "Không tư liệu nào khớp bộ lọc hiện tại."}
              </span>
            </div>
          ) : (
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
                    {asset.type === "slide" && (
                      <LayoutTemplate className="w-8 h-8 text-emerald-400/60 group-hover:text-emerald-400 transition-colors" />
                    )}
                    {(asset.type === "document" || asset.type === "other") && (
                      <FileText className="w-8 h-8 text-gray-400/60 group-hover:text-gray-300 transition-colors" />
                    )}

                    {/* Duration / size pill */}
                    <span className="absolute bottom-1 right-1 text-[9px] bg-black/70 px-1 rounded text-gray-300 font-mono">
                      {asset.duration}
                    </span>
                  </div>

                  <div className="p-2 space-y-1">
                    <span className="font-semibold text-xs text-white truncate block" title={asset.name}>
                      {asset.name}
                    </span>
                    <div className="flex justify-between items-center text-[10px] text-gray-400">
                      <span className="uppercase text-[9px] text-nle-cyan font-bold">
                        {asset.type}
                      </span>
                      <span className="truncate max-w-[70px] text-gray-400" title={asset.source}>
                        {asset.size}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
