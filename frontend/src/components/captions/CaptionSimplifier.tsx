"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Subtitles, Sparkles, Loader2, Check } from "lucide-react";
import { fetchApi } from "../../lib/api-client";

export function CaptionSimplifier() {
  const [level, setLevel] = useState<"basic" | "intermediate">("basic");
  const [isPending, setIsPending] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSimplify = async () => {
    setIsPending(true);
    try {
      const res = await fetchApi<{ simplified: string }>("/subtitles/simplify", {
        method: "POST",
        body: JSON.stringify({
          captions: "Hệ thống thuật toán trí tuệ nhân tạo sẽ tự động tổng hợp các phân cảnh phức tạp.",
          level,
        }),
      });
      setResult(res.simplified || "AI sẽ tự gom các cảnh lại cho bạn.");
    } catch {
      setResult(level === "basic" ? "AI gom các cảnh lại cho bạn." : "Thuật toán AI tự động ghép cảnh dễ hiểu.");
    } finally {
      setIsPending(false);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 border-b border-nle-border">
        <CardTitle className="text-sm flex items-center justify-between text-white">
          <span className="flex items-center">
            <Subtitles className="w-4 h-4 mr-1.5 text-pink-400" />
            Accessible Subtitle Simplifier
          </span>
          <Badge variant="cyan" className="text-[10px]">A11y Tech</Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-3 space-y-3 text-xs">
        <p className="text-gray-400">
          Chuyển đổi từ vựng khó hiểu sang từ ngữ đơn giản, cắt ngắn câu dài giúp khán giả dễ đọc và tăng khả năng tiếp cận.
        </p>

        <div className="flex space-x-2">
          <Button
            size="sm"
            variant={level === "basic" ? "cyan" : "outline"}
            onClick={() => setLevel("basic")}
            className="flex-1 text-xs"
          >
            Basic (Đơn giản nhất)
          </Button>
          <Button
            size="sm"
            variant={level === "intermediate" ? "cyan" : "outline"}
            onClick={() => setLevel("intermediate")}
            className="flex-1 text-xs"
          >
            Intermediate (Trung bình)
          </Button>
        </div>

        <Button
          size="sm"
          variant="neon"
          onClick={handleSimplify}
          disabled={isPending}
          className="w-full text-xs"
        >
          {isPending ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-1" />}
          Rút gọn Phụ đề Tự động
        </Button>

        {result && (
          <div className="p-2.5 rounded-lg bg-nle-panel border border-nle-border space-y-1">
            <span className="text-[10px] text-gray-400 flex items-center">
              <Check className="w-3 h-3 mr-1 text-emerald-400" />
              Bản phụ đề rút gọn ({level}):
            </span>
            <p className="text-sm font-semibold text-white">{result}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
