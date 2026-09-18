"use client";

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useThumbnails } from "@/hooks/useThumbnails";
import { Sparkles, Image as ImageIcon, Flame, Check, Loader2 } from "lucide-react";

export function ThumbnailModal() {
  const { isThumbnailModalOpen, setThumbnailModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { generateThumbnailsMutation } = useThumbnails();

  const [selectedStyle, setSelectedStyle] = useState("neon_gamer");
  const [candidates, setCandidates] = useState<any[]>([
    { id: "c1", style: "Neon Gamer", ctr: "15.8%", text: "BÍ MẬT 3 GIÂY ĐẦU" },
    { id: "c2", style: "Tech Minimal", ctr: "12.4%", text: "ALGORITHM HACK" },
    { id: "c3", style: "Vlog Bold", ctr: "14.1%", text: "ĐỪNG LÀM ĐIỀU NÀY!" },
  ]);

  const handleGenerate = async () => {
    try {
      const res = await generateThumbnailsMutation.mutateAsync({
        topic: currentProject?.topic || "Viral Video Creation",
        style: selectedStyle,
      });
      if (res.candidates && res.candidates.length > 0) {
        setCandidates(res.candidates);
      }
    } catch (e) {
      console.error(e);
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
            Trích xuất khung hình tối ưu, tạo văn bản viral typography và dự đoán tỷ lệ click qua thumbnail.
          </DialogDescription>
        </DialogHeader>

        {/* Style Selector */}
        <div className="flex items-center justify-between py-2 border-b border-nle-border">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400">Phong cách:</span>
            {["neon_gamer", "tech_minimal", "vlog_bold"].map((s) => (
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

        {/* Thumbnail Cards Grid */}
        <div className="grid grid-cols-3 gap-3 my-2">
          {candidates.map((item, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden flex flex-col hover:border-nle-cyan transition-all group cursor-pointer"
            >
              {/* Preview Box */}
              <div className="aspect-[9/16] bg-gradient-to-br from-nle-base to-nle-surface flex flex-col items-center justify-center p-3 relative text-center">
                <Badge variant="cyan" className="absolute top-2 left-2 text-[10px]">
                  {item.style || "AI Poster"}
                </Badge>
                <div className="absolute top-2 right-2 flex items-center space-x-1 bg-black/70 px-1.5 py-0.5 rounded text-[10px] text-nle-amber font-bold">
                  <Flame className="w-3 h-3 fill-current" />
                  <span>{item.ctr || "14.5% CTR"}</span>
                </div>

                <div className="w-10 h-10 rounded-full bg-nle-cyan/10 flex items-center justify-center mb-2">
                  <ImageIcon className="w-5 h-5 text-nle-cyan" />
                </div>
                <span className="font-extrabold text-sm text-transparent bg-clip-text bg-gradient-to-r from-nle-cyan to-white uppercase leading-tight drop-shadow-md">
                  {item.text}
                </span>
              </div>

              {/* Action */}
              <div className="p-2 border-t border-nle-border bg-nle-surface/80 flex items-center justify-between">
                <span className="text-[10px] text-gray-400">Khung hình #{idx + 1}</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[10px] px-2 border-nle-border hover:border-nle-cyan text-nle-cyan"
                  onClick={() => alert("Đã chọn thumbnail này làm poster chính và chuyển sang Photo Lab!")}
                >
                  <Check className="w-3 h-3 mr-1" />
                  Chọn & Dùng
                </Button>
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
