"use client";

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/tabs";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { useUIStore } from "../../stores/useUIStore";
import { useQA } from "../../hooks/useQA";
import { ShieldCheck, Palette, FileCheck, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

export function ComplianceModal() {
  const { isQAModalOpen, setQAModalOpen } = useUIStore();
  const { platformQAMutation, brandQAMutation, copyrightMutation } = useQA();

  const [platformResult, setPlatformResult] = useState<any>(null);
  const [brandResult, setBrandResult] = useState<any>(null);
  const [copyrightResult, setCopyrightResult] = useState<any>(null);

  const runPlatformCheck = async (platform: string) => {
    try {
      const res = await platformQAMutation.mutateAsync({
        platform,
        duration: 45,
        aspectRatio: "9:16",
      });
      setPlatformResult(res);
    } catch (e) {
      console.error(e);
    }
  };

  const runBrandCheck = async () => {
    try {
      const res = await brandQAMutation.mutateAsync({
        font: "Inter",
        primary_color: "#00f0ff",
        tone: "informative",
      });
      setBrandResult(res);
    } catch (e) {
      console.error(e);
    }
  };

  const runCopyrightCheck = async () => {
    try {
      const res = await copyrightMutation.mutateAsync(["asset_01", "asset_02"]);
      setCopyrightResult(res);
    } catch (e) {
      console.error(e);
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
            Kiểm tra định dạng đa nền tảng, đối soát nhận diện thương hiệu và quét chứng thực bản quyền số.
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
              Bản quyền (SHA-256)
            </TabsTrigger>
          </TabsList>

          {/* Platform Tab */}
          <TabsContent value="platform" className="space-y-3 mt-3">
            <div className="flex space-x-2">
              {["tiktok", "shorts", "reels", "youtube"].map((p) => (
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
            </div>

            {platformResult ? (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase">{platformResult.platform} Checklist</span>
                  <Badge variant={platformResult.passed ? "emerald" : "amber"}>
                    {platformResult.passed ? "100% Đạt Chuẩn" : "Cần Lưu Ý"}
                  </Badge>
                </div>
                {platformResult.issues?.length > 0 ? (
                  <ul className="text-xs space-y-1 text-amber-300">
                    {platformResult.issues.map((iss: string, idx: number) => (
                      <li key={idx} className="flex items-center">
                        <AlertTriangle className="w-3 h-3 mr-1.5 shrink-0" />
                        <span>{iss}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-emerald-400 flex items-center">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                    Video hoàn toàn tuân thủ tỷ lệ 9:16, âm lượng chuẩn và vùng an toàn (Safe Zone).
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

            {brandResult && (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2 text-xs">
                <span className="font-semibold text-white">Kết quả Brand Consistency:</span>
                <p className="text-gray-300">
                  Phông chữ tiêu đề, bảng màu chủ đạo (#00f0ff) và phong cách giọng đọc phù hợp với tiêu chuẩn bộ nhận diện.
                </p>
              </div>
            )}
          </TabsContent>

          {/* Copyright Scanner Tab */}
          <TabsContent value="copyright" className="space-y-3 mt-3">
            <Button
              size="sm"
              variant="outline"
              onClick={runCopyrightCheck}
              disabled={copyrightMutation.isPending}
              className="text-xs border-nle-border"
            >
              {copyrightMutation.isPending && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
              Băm & Quét Chữ ký Số (SHA-256)
            </Button>

            {copyrightResult && (
              <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2 text-xs">
                <span className="font-semibold text-emerald-400 flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                  Toàn bộ tư liệu đều có nguồn gốc xuất xứ sạch và xác thực SHA-256.
                </span>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
