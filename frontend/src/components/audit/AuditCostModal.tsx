"use client";

/**
 * Cost Guard and provenance audit trail.
 *
 * Two corrections, both against the real backend:
 *
 * * **Money.** There is no usage ledger — ``/cost/check`` prices a *proposed*
 *   plan of calls and reports the configured budget, and that is all. The screen
 *   used to show a hardcoded "$0.42 of $5.00", a progress bar and a
 *   per-provider spend breakdown that existed nowhere in the system. It now
 *   prices a plan the operator types.
 * * **The audit list.** It used to fall back to four invented entries when the
 *   log was empty — complete with fabricated hashes, one of them claiming
 *   ``SOURCE_RIGHTS_CONFIRMED`` for a record that never happened. An empty log
 *   now says so. The hash column stays, because ``services/qa.py`` genuinely
 *   derives ``sha256_hash`` from each entry's own content.
 */

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores/useUIStore";
import { useAuditCost } from "@/hooks/useAuditCost";
import {
  DollarSign,
  History,
  PieChart,
  AlertTriangle,
  Loader2,
  Calculator,
  ShieldCheck,
} from "lucide-react";

/**
 * The step names the cost guard prices.
 *
 * Kept in step with ``UNIT_COSTS_USD`` in ``content_factory/cost_guard.py`` —
 * a step the guard has no unit cost for contributes exactly zero, so offering it
 * here would only mislead.
 */
const COST_STEPS = [
  { id: "vision", label: "Vision (phân tích khung hình)" },
  { id: "audio_llm", label: "Audio LLM (phân tích thoại/nhạc)" },
  { id: "tts", label: "TTS (giọng đọc)" },
  { id: "stt", label: "STT (bóc băng)" },
  { id: "embedding", label: "Embedding (tri thức)" },
] as const;

type CostStepId = (typeof COST_STEPS)[number]["id"];

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

export function AuditCostModal() {
  const { isAuditModalOpen, setAuditModalOpen } = useUIStore();
  const { auditQuery, costCheckMutation } = useAuditCost();

  const [plan, setPlan] = useState<Record<CostStepId, number>>({
    vision: 0,
    audio_llm: 0,
    tts: 0,
    stt: 0,
    embedding: 0,
  });

  const entries = auditQuery.data ?? [];
  const cost = costCheckMutation.data;

  const handlePricePlan = () => {
    // Only send the steps the operator actually asked to price.
    const calls: Record<string, number> = {};
    for (const step of COST_STEPS) {
      if (plan[step.id] > 0) calls[step.id] = plan[step.id];
    }
    costCheckMutation.mutate({ calls });
  };

  return (
    <Dialog open={isAuditModalOpen} onOpenChange={setAuditModalOpen}>
      <DialogContent className="max-w-2xl bg-nle-surface border-nle-border text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center text-lg">
            <DollarSign className="w-5 h-5 text-nle-amber mr-2" />
            <span>Cost Guard & Provenance Audit Trail</span>
          </DialogTitle>
          <DialogDescription>
            Ước lượng chi phí một kế hoạch gọi model trước khi chạy, và đọc nhật ký truy vết
            (append-only, ghi bởi backend).
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="cost" className="w-full">
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="cost" className="flex items-center text-xs">
              <PieChart className="w-3.5 h-3.5 mr-1 text-nle-amber" />
              Ước lượng Chi phí (Cost Guard)
            </TabsTrigger>
            <TabsTrigger value="audit" className="flex items-center text-xs">
              <History className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
              Nhật ký Kiểm toán (Audit Trail)
            </TabsTrigger>
          </TabsList>

          {/* Cost Guard Tab */}
          <TabsContent value="cost" className="space-y-3 mt-3">
            <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2">
              <span className="text-[11px] font-semibold text-gray-300 block">
                Kế hoạch cần định giá (số lần gọi mỗi bước):
              </span>
              <div className="space-y-1.5">
                {COST_STEPS.map((step) => (
                  <div key={step.id} className="flex items-center justify-between text-xs">
                    <label htmlFor={`cost-${step.id}`} className="text-gray-300">
                      {step.label}
                    </label>
                    <input
                      id={`cost-${step.id}`}
                      type="number"
                      min={0}
                      value={plan[step.id]}
                      onChange={(e) =>
                        setPlan((prev) => ({
                          ...prev,
                          [step.id]: Math.max(0, Number(e.target.value) || 0),
                        }))
                      }
                      className="w-20 bg-nle-base border border-nle-border rounded px-2 py-1 text-right font-mono text-xs text-white focus:border-nle-cyan focus:outline-none"
                    />
                  </div>
                ))}
              </div>

              <Button
                size="sm"
                variant="neon"
                onClick={handlePricePlan}
                disabled={costCheckMutation.isPending}
                className="text-xs h-7 w-full"
              >
                {costCheckMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <Calculator className="w-3.5 h-3.5 mr-1" />
                )}
                Ước lượng chi phí
              </Button>
            </div>

            {costCheckMutation.isError && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start">
                <AlertTriangle className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
                <span>
                  Không ước lượng được:{" "}
                  <strong>
                    {costCheckMutation.error instanceof Error
                      ? costCheckMutation.error.message
                      : String(costCheckMutation.error)}
                  </strong>
                </span>
              </div>
            )}

            {!cost && !costCheckMutation.isError && (
              <div className="p-5 rounded-lg bg-nle-panel border border-dashed border-nle-border text-center text-gray-500 text-xs">
                Nhập số lần gọi rồi bấm ước lượng. Đây là ước lượng cho kế hoạch bạn nhập — hệ thống
                chưa có sổ ghi chi tiêu thực tế.
              </div>
            )}

            {cost && (
              <>
                <div className="p-4 rounded-lg bg-nle-panel border border-nle-border space-y-3">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-semibold text-white">Chi phí ước tính</span>
                    <span className="font-mono text-nle-cyan text-lg">
                      {formatUsd(cost.estimated_total_usd)}
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px] text-gray-400">
                    <span>Ngưỡng ngân sách đã cấu hình: {formatUsd(cost.budget_limit)}</span>
                    {cost.exceeds_budget ? (
                      <Badge variant="amber" className="text-[10px]">
                        Vượt ngân sách
                      </Badge>
                    ) : (
                      <Badge variant="emerald" className="text-[10px]">
                        Trong ngân sách
                      </Badge>
                    )}
                  </div>
                </div>

                {cost.needs_confirmation && (
                  <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start">
                    <ShieldCheck className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
                    <span>
                      Kế hoạch này cần người vận hành xác nhận trước khi chạy (vượt ngưỡng{" "}
                      {formatUsd(cost.budget_limit)}).
                    </span>
                  </div>
                )}

                {Object.keys(cost.by_service).length > 0 && (
                  <div className="grid grid-cols-3 gap-2 text-center">
                    {Object.entries(cost.by_service).map(([service, usd]) => (
                      <div key={service} className="p-2.5 rounded bg-nle-panel border border-nle-border">
                        <span className="text-[10px] text-gray-400 uppercase block truncate">
                          {service}
                        </span>
                        <span className="font-mono text-xs font-bold text-white">
                          {formatUsd(usd)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* Audit Trail Tab */}
          <TabsContent value="audit" className="mt-3">
            {auditQuery.isLoading ? (
              <div className="p-6 text-center text-xs text-gray-400 flex items-center justify-center">
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Đang đọc nhật ký…
              </div>
            ) : auditQuery.isError ? (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start">
                <AlertTriangle className="w-4 h-4 mr-1.5 shrink-0 mt-0.5" />
                <span>Không đọc được nhật ký: {auditQuery.error.message}</span>
              </div>
            ) : entries.length === 0 ? (
              <div className="p-6 rounded-lg bg-nle-panel border border-dashed border-nle-border text-center text-xs text-gray-500">
                Nhật ký trống. Các mục sẽ xuất hiện ở đây sau khi backend ghi nhận một can thiệp.
              </div>
            ) : (
              <div className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden max-h-60 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-[11px]">Thời gian</TableHead>
                      <TableHead className="text-[11px]">Tác nhân</TableHead>
                      <TableHead className="text-[11px]">Hành động</TableHead>
                      <TableHead className="text-[11px]">Chi tiết</TableHead>
                      <TableHead className="text-[11px]">Mã SHA-256</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entries.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="font-mono text-[11px] text-gray-400">
                          {entry.timestamp}
                        </TableCell>
                        <TableCell className="text-[11px] text-nle-cyan">{entry.actor}</TableCell>
                        <TableCell className="text-[11px] font-semibold text-white">
                          {entry.action}
                        </TableCell>
                        <TableCell className="text-[10px] text-gray-500">
                          {entry.detail ?? entry.prompt ?? entry.project_id ?? "—"}
                        </TableCell>
                        <TableCell
                          className="font-mono text-[10px] text-gray-500"
                          title={entry.sha256_hash}
                        >
                          {entry.sha256_hash.slice(0, 10)}…
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
