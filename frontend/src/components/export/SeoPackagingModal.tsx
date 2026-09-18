"use client";

/**
 * SEO packaging studio.
 *
 * Every number on this screen comes from a `SeoReport` the engine returned. The
 * earlier version shipped a hand-written `SeoScoreResult` — a score of 84.5, six
 * invented dimensions and two invented fixes — and rendered it before the
 * operator asked for anything, badged "Đo lường thật". Its catch blocks also
 * fabricated improvements when the request failed, so a broken engine looked
 * like a working one. There is no placeholder report now: an unscored pack shows
 * an empty state.
 */

import React, { useState } from "react";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useSEO } from "@/hooks/useSEO";
import { SeoReport, SeoSignal, SeoSignalStatus } from "@/types/seo";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Target,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  X,
  RefreshCw,
  Loader2,
  BarChart3,
  ShieldAlert,
} from "lucide-react";

type SeoPlatform = "youtube" | "shorts" | "tiktok";

const PLATFORMS: Array<{ id: SeoPlatform; label: string }> = [
  { id: "tiktok", label: "📱 TikTok 9:16" },
  { id: "shorts", label: "⚡ YouTube Shorts" },
  { id: "youtube", label: "🎬 YouTube 16:9" },
];

const STATUS_VARIANT: Record<SeoSignalStatus, "emerald" | "amber" | "destructive" | "outline"> = {
  ok: "emerald",
  warn: "amber",
  fail: "destructive",
  unknown: "outline",
};

function scoreVariant(score: number): "emerald" | "amber" | "destructive" {
  if (score >= 80) return "emerald";
  if (score >= 60) return "amber";
  return "destructive";
}

export function SeoPackagingModal() {
  const { isSeoModalOpen, setSeoModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { projectSeoMutation, optimizeMutation } = useSEO(currentProject?.id);

  const [platform, setPlatform] = useState<SeoPlatform>("tiktok");
  const [title, setTitle] = useState(currentProject?.name ?? "");
  const [tags, setTags] = useState("");
  const [description, setDescription] = useState("");

  /** `null` until the operator runs an audit — never a stand-in for a real one. */
  const [report, setReport] = useState<SeoReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizedFixes, setOptimizedFixes] = useState<string[] | null>(null);

  if (!isSeoModalOpen) return null;

  const handleRunAudit = async () => {
    setError(null);
    try {
      const res = await projectSeoMutation.mutateAsync({
        platform,
        title,
        description,
        tags: tags.split(/[\s,]+/).filter(Boolean),
      });
      setReport(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setReport(null);
    }
  };

  const handleOptimizePack = async () => {
    setIsOptimizing(true);
    setError(null);
    setOptimizedFixes(null);
    try {
      const res = await optimizeMutation.mutateAsync({
        platform,
        pack: {
          title,
          description,
          tags: tags.split(/[\s,]+/).filter(Boolean),
          duration_seconds: currentProject?.duration_target_seconds ?? 45,
          aspect_ratio: platform === "youtube" ? "16:9" : "9:16",
        },
      });
      // `pack` is the rewritten pack and `after` the engine's re-score of it.
      setTitle(res.pack.title);
      setDescription(res.pack.description);
      setTags(res.pack.tags.join(" "));
      setOptimizedFixes(res.applied_fixes);
      setReport(res.after);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsOptimizing(false);
    }
  };

  const blocking = report?.blocking ?? [];
  const quickWins = report?.quick_wins ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-2xl bg-nle-surface border-nle-border shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <CardHeader className="py-3 px-4 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
          <div className="flex items-center space-x-2">
            <Target className="w-5 h-5 text-nle-cyan" />
            <div>
              <CardTitle className="text-sm font-bold text-white">
                SEO Packaging & 70-Signal Scoring Studio
              </CardTitle>
              <p className="text-[11px] text-gray-400">
                Chấm điểm thuật toán YouTube 16:9, Shorts, TikTok trên bộ tín hiệu thật của engine
              </p>
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSeoModalOpen(false)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        {/* Platform Selection */}
        <div className="flex border-b border-nle-border bg-nle-base px-4 py-2 justify-between items-center text-xs">
          <div className="flex space-x-1">
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPlatform(p.id)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                  platform === p.id
                    ? "bg-nle-cyan text-black"
                    : "text-gray-400 hover:text-white bg-nle-panel"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <Button
            size="sm"
            variant="neon"
            onClick={handleOptimizePack}
            disabled={isOptimizing || !title.trim()}
            className="text-xs h-7"
          >
            {isOptimizing ? (
              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 mr-1" />
            )}
            1-Click AI Tối Ưu
          </Button>
        </div>

        {/* Modal Content */}
        <CardContent className="p-4 space-y-3 flex-1 overflow-y-auto min-h-0 text-xs">
          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start">
              <AlertTriangle className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
              <span>
                Không chấm được điểm: <strong>{error}</strong>
              </span>
            </div>
          )}

          {optimizedFixes && optimizedFixes.length > 0 && (
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs space-y-1">
              <span className="font-semibold block">
                Engine đã viết lại gói xuất bản ({optimizedFixes.length} thay đổi):
              </span>
              <ul className="list-disc list-inside space-y-0.5 text-emerald-200/90">
                {optimizedFixes.map((change, idx) => (
                  <li key={idx}>{change}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Editable Pack Fields */}
          <div className="space-y-2">
            <div>
              <label className="text-gray-300 font-semibold block mb-1">Tiêu đề video (Title):</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Nhập tiêu đề sẽ xuất bản…"
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white focus:border-nle-cyan focus:outline-none font-medium"
              />
            </div>

            <div>
              <label className="text-gray-300 font-semibold block mb-1">
                Mô tả (Description):
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Dòng mô tả sẽ xuất bản…"
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white focus:border-nle-cyan focus:outline-none resize-none"
              />
            </div>

            <div>
              <label className="text-gray-300 font-semibold block mb-1">
                Hashtags & Tags (cách nhau bởi dấu cách):
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="#fyp #xuhuong"
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-nle-cyan font-mono focus:border-nle-cyan focus:outline-none"
              />
            </div>
          </div>

          {!report ? (
            <div className="p-6 rounded-lg bg-nle-panel border border-dashed border-nle-border text-center space-y-1">
              <BarChart3 className="w-5 h-5 mx-auto text-gray-500" />
              <p className="text-gray-300 font-semibold">Chưa có báo cáo SEO cho gói này</p>
              <p className="text-gray-500">
                Bấm &quot;Chấm Điểm SEO&quot; để engine đối chiếu gói xuất bản với bộ tín hiệu của nền
                tảng.
              </p>
            </div>
          ) : (
            <>
              {/* Score Hero Banner */}
              <div className="p-3 rounded-lg bg-gradient-to-r from-nle-panel via-nle-base to-nle-panel border border-nle-border flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-mono text-gray-400 block">
                    Tổng Điểm Thuật Toán (SEO Score) — {report.label}
                  </span>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-black text-white">{report.score.toFixed(1)}</span>
                    <span className="text-xs text-gray-400">/ 100</span>
                    <Badge variant={scoreVariant(report.score)} className="text-[10px]">
                      Hạng {report.grade}
                    </Badge>
                    <span className="text-[10px] text-gray-500 font-mono">
                      độ tin cậy {(report.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleRunAudit}
                  disabled={projectSeoMutation.isPending}
                  className="text-xs border-nle-border h-7 text-gray-300 hover:text-white"
                >
                  {projectSeoMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin text-nle-cyan" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
                  )}
                  Chấm Lại Điểm
                </Button>
              </div>

              {report.verdict && (
                <p className="text-gray-300 px-1 leading-relaxed">{report.verdict}</p>
              )}

              {/* The engine caps the score when a dimension is unmeasurable. */}
              {report.capped && (
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-start">
                  <ShieldAlert className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
                  <span>
                    Điểm đã bị giới hạn
                    {report.cap_reason ? `: ${report.cap_reason}` : ""}. Chấm thêm tín hiệu còn thiếu
                    để có điểm thật.
                  </span>
                </div>
              )}

              {/* Weighted dimensions */}
              {report.dimensions.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="font-semibold text-gray-300 block">
                    Chi tiết các nhóm tín hiệu (Signal Breakdown):
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {report.dimensions.map((dim) => (
                      <div
                        key={dim.key}
                        className="p-2 rounded bg-nle-panel border border-nle-border space-y-1 text-xs"
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-gray-200 font-medium truncate">{dim.label}</span>
                          <span className="font-bold font-mono text-emerald-400">
                            {dim.score.toFixed(1)}/100
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-nle-base rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-400 rounded-full"
                            style={{ width: `${Math.max(0, Math.min(100, dim.score))}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-gray-400 block">
                          trọng số {(dim.weight * 100).toFixed(0)}% • đo được{" "}
                          {(dim.coverage * 100).toFixed(0)}% tín hiệu
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Blocking signals — these hold the pack back regardless of score */}
              {blocking.length > 0 && (
                <div className="p-3 rounded-lg bg-nle-panel border border-rose-500/30 space-y-2">
                  <span className="font-bold text-white flex items-center">
                    <AlertTriangle className="w-3.5 h-3.5 mr-1 text-rose-400" />
                    Tín hiệu chặn xuất bản ({blocking.length}):
                  </span>
                  <div className="space-y-1">
                    {blocking.map((signal: SeoSignal) => (
                      <div
                        key={signal.id}
                        className="p-2 rounded bg-nle-base border border-nle-border flex items-start justify-between text-xs"
                      >
                        <div className="pr-2">
                          <span className="text-gray-200 font-medium block">{signal.label}</span>
                          <span className="text-[10px] text-gray-400 block">{signal.detail}</span>
                          {signal.fix && (
                            <span className="text-[10px] text-nle-cyan/90 block">
                              Cách sửa: {signal.fix}
                            </span>
                          )}
                        </div>
                        <Badge variant={STATUS_VARIANT[signal.status]} className="text-[10px] shrink-0">
                          {signal.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Measured quick wins */}
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                <span className="font-bold text-white flex items-center justify-between">
                  <span className="flex items-center">
                    <TrendingUp className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                    Chỉnh Sửa Đo Được Giúp Tăng Điểm Nhiều Nhất:
                  </span>
                  {report.projected_score > report.score && (
                    <span className="text-[10px] font-mono text-gray-400">
                      dự kiến {report.projected_score.toFixed(1)}
                    </span>
                  )}
                </span>

                {quickWins.length === 0 ? (
                  <p className="text-gray-500">
                    Engine không tìm thấy chỉnh sửa nào còn đo được cho gói này.
                  </p>
                ) : (
                  <div className="space-y-1">
                    {quickWins.map((win) => (
                      <div
                        key={win.signal_id}
                        className="p-2 rounded bg-nle-base border border-nle-border flex items-start justify-between text-xs"
                      >
                        <div className="pr-2">
                          <span className="text-gray-200 font-medium block">{win.label}</span>
                          <span className="text-[10px] text-gray-400 block">{win.fix}</span>
                        </div>
                        <Badge variant="emerald" className="text-[10px] shrink-0 font-mono">
                          +{win.points} pts
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {report.notes.length > 0 && (
                <ul className="text-[10px] text-gray-500 space-y-0.5 px-1">
                  {report.notes.map((note, idx) => (
                    <li key={idx}>• {note}</li>
                  ))}
                </ul>
              )}
            </>
          )}

          {/* Audit trigger lives here too, so the empty state is actionable. */}
          {!report && (
            <Button
              size="sm"
              variant="neon"
              onClick={handleRunAudit}
              disabled={projectSeoMutation.isPending}
              className="w-full text-xs h-8"
            >
              {projectSeoMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
              ) : (
                <BarChart3 className="w-3.5 h-3.5 mr-1" />
              )}
              Chấm Điểm SEO
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
