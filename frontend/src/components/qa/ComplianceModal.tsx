"use client";

/**
 * QA hub: platform format, brand consistency, copyright clearance.
 *
 * The three checks below are advisory and never approve a project — the two
 * human gates stay the only paths forward. Three things the earlier version
 * asserted that the backend never said:
 *
 * * the platform panel printed "Video hoàn toàn tuân thủ tỷ lệ 9:16, âm lượng
 *   chuẩn và vùng an toàn" whenever ``issues`` was empty, on inputs the studio
 *   made up (every check was sent ``45s`` and ``9:16`` regardless of platform or
 *   project). The measurements now come from the project, and the panel reports
 *   the findings the engine returned.
 * * the brand panel printed a fixed sentence about ``#00f0ff`` and Inter — the
 *   same two values it had just sent — no matter what came back.
 * * the copyright panel claimed "Toàn bộ tư liệu đều có nguồn gốc xuất xứ sạch
 *   và xác thực SHA-256" for ``["asset_01", "asset_02"]``, two ids that do not
 *   exist, and for a check that hashes nothing: the engine compares each
 *   candidate string against a ``protected`` list. It now scans the project's
 *   actually-ingested assets and says how many it cleared.
 */

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/stores/useUIStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useQA } from "@/hooks/useQA";
import { useExternalIngestion } from "@/hooks/useExternalIngestion";
import {
  BrandVerdict,
  CopyrightVerdict,
  PlatformVerdict,
  QaFinding,
} from "@/types/qa";
import {
  ShieldCheck,
  Palette,
  FileCheck,
  AlertTriangle,
  Loader2,
  CheckCircle2,
} from "lucide-react";

const PLATFORMS = ["tiktok", "shorts", "reels", "youtube"] as const;

/** The aspect ratio each platform reviews against. */
const ASPECT_BY_PLATFORM: Record<string, string> = {
  tiktok: "9:16",
  shorts: "9:16",
  reels: "9:16",
  youtube: "16:9",
};

type Severity = QaFinding["severity"];

/** `QaFinding.severity` is `IssueSeverity` plus the engine's own "pass"/"fail". */
function severityVariant(severity: Severity): "emerald" | "amber" | "destructive" {
  if (severity === "pass" || severity === "info") return "emerald";
  if (severity === "warning") return "amber";
  return "destructive";
}

function FindingList({ findings }: { findings: QaFinding[] }) {
  if (findings.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      {findings.map((finding, idx) => (
        <li
          key={`${finding.code}-${idx}`}
          className="p-2 rounded bg-nle-base border border-nle-border text-xs space-y-0.5"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-gray-400">{finding.code}</span>
            <Badge variant={severityVariant(finding.severity)} className="text-[10px]">
              {finding.severity}
            </Badge>
          </div>
          <span className="text-gray-200 block">{finding.message}</span>
          {finding.hint && (
            <span className="text-[10px] text-nle-cyan/90 block">Gợi ý: {finding.hint}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function Checklist({ heading, passed }: { heading: string; passed: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold uppercase">{heading}</span>
      <Badge variant={passed ? "emerald" : "amber"}>
        {passed ? "Đạt" : "Cần lưu ý"}
      </Badge>
    </div>
  );
}

export function ComplianceModal() {
  const { isQAModalOpen, setQAModalOpen } = useUIStore();
  const { currentProject } = useProjectStore();
  const { platformQAMutation, brandQAMutation, copyrightMutation } = useQA();
  const { assetsQuery } = useExternalIngestion(currentProject?.id);

  const [platformResult, setPlatformResult] = useState<PlatformVerdict | null>(null);
  const [brandResult, setBrandResult] = useState<BrandVerdict | null>(null);
  const [copyrightResult, setCopyrightResult] = useState<CopyrightVerdict | null>(null);

  const [fontsInput, setFontsInput] = useState("");
  const [paletteInput, setPaletteInput] = useState("");
  const [protectedInput, setProtectedInput] = useState("");

  /** The ids actually ingested for this project — the real candidates to clear. */
  const ingestedAssets = assetsQuery.data ?? [];

  const runPlatformCheck = async (platform: string) => {
    try {
      const res = await platformQAMutation.mutateAsync({
        platform,
        duration_seconds: currentProject?.duration_target_seconds ?? null,
        aspect_ratio: ASPECT_BY_PLATFORM[platform] ?? "9:16",
      });
      setPlatformResult(res);
    } catch {
      setPlatformResult(null);
    }
  };

  const runBrandCheck = async () => {
    const splitList = (value: string) =>
      value.split(/[\s,]+/).map((item) => item.trim()).filter(Boolean);
    try {
      const res = await brandQAMutation.mutateAsync({
        fonts: splitList(fontsInput),
        palette: splitList(paletteInput),
      });
      setBrandResult(res);
    } catch {
      setBrandResult(null);
    }
  };

  const runCopyrightCheck = async () => {
    const assetIds = ingestedAssets.map((asset) => asset.id);
    if (assetIds.length === 0) {
      setCopyrightResult(null);
      return;
    }
    try {
      const res = await copyrightMutation.mutateAsync({
        asset_ids: assetIds,
        protected: protectedInput
          .split(/[\s,]+/)
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setCopyrightResult(res);
    } catch {
      setCopyrightResult(null);
    }
  };

  return (
    <Dialog open={isQAModalOpen} onOpenChange={setQAModalOpen}>
      <DialogContent className="max-w-2xl bg-nle-surface border-nle-border text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center text-lg">
            <ShieldCheck className="w-5 h-5 text-nle-cyan mr-2" />
            <span>Trung tâm Kiểm định & Bản quyền (QA & Brand Hub)</span>
          </DialogTitle>
          <DialogDescription>
            Kiểm tra định dạng đa nền tảng, đối soát nhận diện thương hiệu và đối chiếu danh sách
            tư liệu được bảo vệ. Đây là lớp cảnh báo — hai cổng duyệt của con người vẫn là đường
            duy nhất đưa dự án tiến lên.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="platform" className="w-full">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="platform" className="flex items-center text-xs">
              <ShieldCheck className="w-3.5 h-3.5 mr-1" />
              Chuẩn Nền tảng
            </TabsTrigger>
            <TabsTrigger value="brand" className="flex items-center text-xs">
              <Palette className="w-3.5 h-3.5 mr-1" />
              Brand Kit
            </TabsTrigger>
            <TabsTrigger value="copyright" className="flex items-center text-xs">
              <FileCheck className="w-3.5 h-3.5 mr-1" />
              Bản quyền
            </TabsTrigger>
          </TabsList>

          {/* Platform Tab */}
          <TabsContent value="platform" className="space-y-3 mt-3">
            <div className="flex flex-wrap gap-2 items-center">
              {PLATFORMS.map((p) => (
                <Button
                  key={p}
                  size="sm"
                  variant="outline"
                  onClick={() => runPlatformCheck(p)}
                  disabled={platformQAMutation.isPending}
                  className="text-xs uppercase border-nle-border hover:border-nle-cyan"
                >
                  {p}
                </Button>
              ))}
              {currentProject && (
                <span className="text-[10px] text-gray-500 font-mono">
                  thời lượng dự án: {currentProject.duration_target_seconds}s
                </span>
              )}
            </div>

            {platformQAMutation.isError && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start">
                <AlertTriangle className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
                <span>
                  Không kiểm định được:{" "}
                  <strong>
                    {platformQAMutation.error instanceof Error
                      ? platformQAMutation.error.message
                      : String(platformQAMutation.error)}
                  </strong>
                </span>
              </div>
            )}

            {platformResult ? (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                <Checklist
                  heading={`${platformResult.platform} Checklist`}
                  passed={platformResult.passed}
                />

                <FindingList findings={platformResult.findings} />

                {platformResult.issues.length > 0 && (
                  <ul className="text-xs space-y-1 text-amber-300">
                    {platformResult.issues.map((issue, idx) => (
                      <li key={idx} className="flex items-start">
                        <AlertTriangle className="w-3 h-3 mr-1.5 shrink-0 mt-0.5" />
                        <span>{issue}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {platformResult.recommendations.length > 0 && (
                  <ul className="text-xs space-y-1 text-gray-300">
                    {platformResult.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start">
                        <CheckCircle2 className="w-3 h-3 mr-1.5 shrink-0 mt-0.5 text-nle-cyan" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {platformResult.findings.length === 0 &&
                  platformResult.issues.length === 0 && (
                    <p className="text-xs text-emerald-400 flex items-center">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                      Engine không trả về tín hiệu nào cho bộ tham số đã gửi.
                    </p>
                  )}
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-gray-400 border border-dashed border-nle-border rounded-lg">
                Chọn nền tảng ở trên để chạy kiểm định tự động.
              </div>
            )}
          </TabsContent>

          {/* Brand Kit Tab */}
          <TabsContent value="brand" className="space-y-3 mt-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-gray-300 block mb-1">
                  Phông chữ dùng trong video:
                </label>
                <input
                  type="text"
                  value={fontsInput}
                  onChange={(e) => setFontsInput(e.target.value)}
                  placeholder="Inter, Roboto…"
                  className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs text-white focus:border-nle-cyan focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] text-gray-300 block mb-1">
                  Bảng màu chủ đạo (hex):
                </label>
                <input
                  type="text"
                  value={paletteInput}
                  onChange={(e) => setPaletteInput(e.target.value)}
                  placeholder="#00f0ff #0b0d12"
                  className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs font-mono text-white focus:border-nle-cyan focus:outline-none"
                />
              </div>
            </div>

            <Button
              size="sm"
              variant="neon"
              onClick={runBrandCheck}
              disabled={brandQAMutation.isPending}
              className="text-xs"
            >
              {brandQAMutation.isPending && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
              Quét Nhận diện Thương hiệu
            </Button>

            {brandResult ? (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2 text-xs">
                <Checklist heading="Kết quả Brand Consistency" passed={brandResult.passed} />
                {brandResult.findings.length === 0 ? (
                  <p className="text-gray-500">
                    Engine không trả về tiêu chí nào cho bộ giá trị đã gửi. Nhập phông chữ và bảng
                    màu thực tế đang dùng trong video để có kết quả có nghĩa.
                  </p>
                ) : (
                  <ul className="space-y-1.5">
                    {brandResult.findings.map((finding, idx) => (
                      <li
                        key={`${finding.category}-${idx}`}
                        className="p-2 rounded bg-nle-base border border-nle-border space-y-0.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] text-gray-400">
                            {finding.category}
                          </span>
                          <Badge
                            variant={
                              finding.status === "pass"
                                ? "emerald"
                                : finding.status === "warn"
                                  ? "amber"
                                  : "destructive"
                            }
                            className="text-[10px]"
                          >
                            {finding.status}
                          </Badge>
                        </div>
                        <span className="text-gray-200 block">{finding.message}</span>
                        {finding.hint && (
                          <span className="text-[10px] text-nle-cyan/90 block">
                            Gợi ý: {finding.hint}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <div className="p-5 text-center text-xs text-gray-500 border border-dashed border-nle-border rounded-lg">
                Nhập phông chữ và bảng màu đang dùng rồi bấm quét.
              </div>
            )}
          </TabsContent>

          {/* Copyright Scanner Tab */}
          <TabsContent value="copyright" className="space-y-3 mt-3">
            <div className="p-2.5 rounded-lg bg-nle-panel border border-nle-border text-[11px] text-gray-400">
              Engine đối chiếu từng tư liệu của dự án với danh sách được bảo vệ bạn cung cấp bên
              dưới (mỗi dòng một fingerprint). Không có danh sách thì không tư liệu nào bị gắn cờ —
              và màn hình nói đúng như vậy thay vì kết luận "sạch".
            </div>

            <div>
              <label className="text-[11px] text-gray-300 block mb-1">
                Danh sách fingerprint được bảo vệ (cách nhau bởi dấu cách hoặc dòng):
              </label>
              <textarea
                rows={2}
                value={protectedInput}
                onChange={(e) => setProtectedInput(e.target.value)}
                placeholder="dán fingerprint của tư liệu đã có bản quyền…"
                className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs font-mono text-white focus:border-nle-cyan focus:outline-none resize-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={runCopyrightCheck}
                disabled={copyrightMutation.isPending || ingestedAssets.length === 0}
                className="text-xs border-nle-border"
              >
                {copyrightMutation.isPending && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                Quét {ingestedAssets.length} tư liệu của dự án
              </Button>
              <span className="text-[10px] text-gray-500">
                {ingestedAssets.length === 0
                  ? "Dự án chưa có tư liệu ngoài nào được nhập."
                  : `${ingestedAssets.length} id lấy từ /projects/{id}/external/assets`}
              </span>
            </div>

            {copyrightResult && (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2 text-xs">
                <Checklist heading="Kết quả đối chiếu" passed={copyrightResult.passed} />
                <p className="text-gray-400">
                  Đã đối chiếu {copyrightResult.checked} tư liệu. {" "}
                  {copyrightResult.findings.length > 0
                    ? `${copyrightResult.findings.length} tư liệu khớp fingerprint trong danh sách được bảo vệ.`
                    : "Không tư liệu nào khớp fingerprint trong danh sách được bảo vệ."}
                </p>
                <FindingList findings={copyrightResult.findings} />
                {copyrightResult.checked > 0 && (
                  <ul className="space-y-1">
                    {copyrightResult.fingerprints.map((row) => (
                      <li
                        key={row.asset_id}
                        className="p-1.5 rounded bg-nle-base border border-nle-border flex items-center justify-between font-mono text-[10px]"
                      >
                        <span className="text-gray-400 truncate">{row.asset_id}</span>
                        <Badge
                          variant={row.status === "flagged" ? "destructive" : "emerald"}
                          className="text-[10px]"
                        >
                          {row.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
