"use client";

/**
 * Thumbnail candidate studio.
 *
 * What the screen used to show: three cards, hardcoded in this file, each with an
 * invented CTR ("15.8%", "12.4%", "14.1%") and invented copy ("BÍ MẬT 3 GIÂY
 * ĐẦU"), presented as the engine's output before it had been asked anything — and
 * the copy also survived a failed generation, because the catch block logged and
 * kept the fake grid. Every card's "Chọn & Dùng" button then called ``alert()``
 * claiming the frame had become the poster.
 *
 * What the engine actually returns is ``ThumbnailCandidate``: a *backend* path,
 * a timestamp, a score and a CTR prediction. No route serves those files yet, so
 * this screen shows the measurements and says so rather than drawing a preview it
 * does not have. There is likewise no route that sets a poster, which is why the
 * select action is disabled instead of announcing a change nothing made.
 */

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useThumbnails, ThumbnailOutcome } from "@/hooks/useThumbnails";
import {
  Sparkles,
  Image as ImageIcon,
  Flame,
  Loader2,
  AlertTriangle,
  Clapperboard,
} from "lucide-react";

const STYLES = ["neon_gamer", "tech_minimal", "vlog_bold"] as const;

function formatTimestamp(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const mm = String(Math.floor(whole / 60)).padStart(2, "0");
  const ss = String(whole % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function ThumbnailModal() {
  const { isThumbnailModalOpen, setThumbnailModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { generateThumbnailsMutation } = useThumbnails();

  const [selectedStyle, setSelectedStyle] = useState<string>(STYLES[0]);
  /** ``null`` until a generation has actually run. */
  const [outcome, setOutcome] = useState<ThumbnailOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setError(null);
    try {
      const res = await generateThumbnailsMutation.mutateAsync({
        topic: currentProject?.topic || undefined,
        project_id: currentProject?.id,
        style: selectedStyle,
      });
      setOutcome(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setOutcome(null);
    }
  };

  return (
    <Dialog open={isThumbnailModalOpen} onOpenChange={setThumbnailModalOpen}>
      <DialogContent className="max-w-3xl bg-nle-surface border-nle-border text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center text-lg">
            <Sparkles className="w-5 h-5 text-nle-cyan mr-2" />
            <span>AI Auto-Thumbnail & Dự đoán CTR (CTR Studio)</span>
          </DialogTitle>
          <DialogDescription>
            Trích xuất khung hình từ video của dự án, chấm điểm và dự đoán tỷ lệ click của từng
            ứng viên.
          </DialogDescription>
        </DialogHeader>

        {/* Style Selector */}
        <div className="flex items-center justify-between py-2 border-b border-nle-border">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400">Phong cách:</span>
            {STYLES.map((s) => (
              <button
                key={s}
                onClick={() => setSelectedStyle(s)}
                className={`text-xs px-2.5 py-1 rounded-md border transition-all uppercase ${
                  selectedStyle === s
                    ? "bg-nle-cyan/20 border-nle-cyan text-nle-cyan font-semibold"
                    : "border-nle-border text-gray-400 hover:text-white"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            ))}
          </div>

          <Button
            size="sm"
            variant="neon"
            onClick={handleGenerate}
            disabled={generateThumbnailsMutation.isPending}
            className="text-xs"
          >
            {generateThumbnailsMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 mr-1" />
            )}
            Tạo Thumbnail Mới
          </Button>
        </div>

        {error && (
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start">
            <AlertTriangle className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
            <span>
              Không tạo được ứng viên: <strong>{error}</strong>
            </span>
          </div>
        )}

        {!outcome && !error && (
          <div className="p-8 text-center text-xs text-gray-500 border border-dashed border-nle-border rounded-lg">
            <ImageIcon className="w-5 h-5 mx-auto mb-2 text-gray-600" />
            Chưa có ứng viên nào. Chọn phong cách rồi bấm &quot;Tạo Thumbnail Mới&quot;.
          </div>
        )}

        {outcome && outcome.candidates.length === 0 && (
          <div className="p-6 text-center text-xs text-gray-400 border border-dashed border-nle-border rounded-lg">
            <Clapperboard className="w-5 h-5 mx-auto mb-2 text-gray-600" />
            Engine không trả về ứng viên nào.
            {outcome.emptyReason && (
              <span className="block mt-1 text-amber-300">{outcome.emptyReason}</span>
            )}
          </div>
        )}

        {outcome && outcome.candidates.length > 0 && (
          <>
            <p className="text-[11px] text-gray-500">
              Ứng viên được ghi vào thư mục tạm của backend và chưa có route phục vụ chúng, nên màn
              hình này hiển thị số đo thay vì ảnh xem trước.
            </p>
            <div className="grid grid-cols-3 gap-3 my-2">
              {outcome.candidates.map((candidate, idx) => (
                <div
                  key={`${candidate.path}-${idx}`}
                  className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden flex flex-col"
                >
                  {/* No preview: the file is on the backend filesystem. */}
                  <div className="aspect-[16/9] bg-gradient-to-br from-nle-base to-nle-surface flex flex-col items-center justify-center p-3 relative text-center gap-1">
                    <Badge variant="cyan" className="absolute top-2 left-2 text-[10px]">
                      {formatTimestamp(candidate.timestamp_seconds)}
                    </Badge>
                    <div className="absolute top-2 right-2 flex items-center space-x-1 bg-black/70 px-1.5 py-0.5 rounded text-[10px] text-nle-amber font-bold">
                      <Flame className="w-3 h-3 fill-current" />
                      <span>{(candidate.ctr_prediction * 100).toFixed(1)}% CTR dự đoán</span>
                    </div>

                    <ImageIcon className="w-6 h-6 text-nle-cyan/40" />
                    <span className="font-mono text-[10px] text-gray-400">
                      điểm {candidate.score.toFixed(2)}
                    </span>
                  </div>

                  {/* Action */}
                  <div className="p-2 border-t border-nle-border bg-nle-surface/80 flex items-center justify-between">
                    <span
                      className="text-[10px] text-gray-500 font-mono truncate"
                      title={candidate.path}
                    >
                      khung #{idx + 1}
                    </span>
                    {/* No route sets a project poster yet, so this stays disabled. */}
                    <Button
                      size="sm"
                      variant="outline"
                      disabled
                      title="Chưa có endpoint đặt poster cho dự án"
                      className="h-7 text-[10px] px-2 border-nle-border opacity-60"
                    >
                      Chọn & Dùng
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
