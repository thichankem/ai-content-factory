"use client";

import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/tabs";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "../ui/table";
import { Progress } from "../ui/progress";
import { Badge } from "../ui/badge";
import { useUIStore } from "../../stores/useUIStore";
import { useAuditCost } from "../../hooks/useAuditCost";
import { DollarSign, History, ShieldCheck, PieChart } from "lucide-react";

export function AuditCostModal() {
  const { isAuditModalOpen, setAuditModalOpen } = useUIStore();
  const { auditQuery } = useAuditCost();

  const [budgetLimit] = useState(5.0); // $5.00 limit
  const [spent] = useState(0.42); // $0.42 spent
  const percentage = Math.min(100, (spent / budgetLimit) * 100);

  const mockAuditLogs = [
    { id: "aud_01", time: "14:28:10", actor: "human_operator", action: "GATE_1_SCRIPT_APPROVED", hash: "a71f02b9..." },
    { id: "aud_02", time: "14:27:45", actor: "ai_copilot", action: "TIMELINE_COMMAND_APPLIED", hash: "99e4cc18..." },
    { id: "aud_03", time: "14:25:30", actor: "human_operator", action: "SOURCE_RIGHTS_CONFIRMED", hash: "3c88bb01..." },
    { id: "aud_04", time: "14:20:12", actor: "template_engine", action: "SCRIPT_DRAFT_GENERATED", hash: "ff2011ea..." },
  ];

  const auditData = auditQuery.data && auditQuery.data.length > 0 ? auditQuery.data : mockAuditLogs;

  return (
    <Dialog open={isAuditModalOpen} onOpenChange={setAuditModalOpen}>
      <DialogContent className="max-w-2xl bg-nle-surface border-nle-border text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center text-lg">
            <DollarSign className="w-5 h-5 text-nle-amber mr-2" />
            <span>Cost Guard & Provenance Audit Trail</span>
          </DialogTitle>
          <DialogDescription>
            Kiểm soát chi phí tiêu thụ token/API và truy vết toàn bộ lịch sử can thiệp có mã băm bảo mật.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="cost" className="w-full">
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="cost" className="flex items-center text-xs">
              <PieChart className="w-3.5 h-3.5 mr-1 text-nle-amber" />
              Giám sát Ngân sách (Cost Guard)
            </TabsTrigger>
            <TabsTrigger value="audit" className="flex items-center text-xs">
              <History className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
              Nhật ký Kiểm toán (Audit Trail)
            </TabsTrigger>
          </TabsList>

          {/* Cost Guard Tab */}
          <TabsContent value="cost" className="space-y-4 mt-3">
            <div className="p-4 rounded-lg bg-nle-panel border border-nle-border space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="font-semibold text-white">Ngân sách Dự án</span>
                <span className="font-mono text-nle-cyan">${spent.toFixed(2)} / ${budgetLimit.toFixed(2)}</span>
              </div>
              <Progress value={percentage} className="h-2.5" />
              <div className="flex justify-between text-[11px] text-gray-400">
                <span>Đã dùng {percentage.toFixed(1)}%</span>
                <Badge variant="emerald" className="text-[10px]">An toàn trong ngưỡng</Badge>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2.5 rounded bg-nle-panel border border-nle-border">
                <span className="text-[10px] text-gray-400 uppercase block">Claude / GPT Tier</span>
                <span className="font-mono text-xs font-bold text-white">$0.28</span>
              </div>
              <div className="p-2.5 rounded bg-nle-panel border border-nle-border">
                <span className="text-[10px] text-gray-400 uppercase block">Whisper / TTS</span>
                <span className="font-mono text-xs font-bold text-white">$0.14</span>
              </div>
              <div className="p-2.5 rounded bg-nle-panel border border-nle-border">
                <span className="text-[10px] text-gray-400 uppercase block">Local Engine</span>
                <span className="font-mono text-xs font-bold text-emerald-400">Miễn phí ($0.00)</span>
              </div>
            </div>
          </TabsContent>

          {/* Audit Trail Tab */}
          <TabsContent value="audit" className="mt-3">
            <div className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden max-h-60 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px]">Thời gian</TableHead>
                    <TableHead className="text-[11px]">Tác nhân</TableHead>
                    <TableHead className="text-[11px]">Hành động</TableHead>
                    <TableHead className="text-[11px]">Mã SHA-256</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditData.map((row: any, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-[11px] text-gray-400">{row.time || row.timestamp}</TableCell>
                      <TableCell className="text-[11px] text-nle-cyan">{row.actor}</TableCell>
                      <TableCell className="text-[11px] font-semibold text-white">{row.action}</TableCell>
                      <TableCell className="font-mono text-[10px] text-gray-500">{row.hash || row.sha256_hash}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
