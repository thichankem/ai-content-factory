"use client";

import React, { useEffect, useRef, useState } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useWorkflowDAG } from "@/hooks/useWorkflowDAG";
import {
  Workflow,
  WorkflowBlockDef,
  WorkflowChecklist,
  WorkflowEdge,
  WorkflowNode,
} from "@/types/workflow";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileCheck,
  GitBranch,
  Loader2,
  Play,
  Plus,
  Save,
  ShieldCheck,
  Terminal,
  Trash2,
} from "lucide-react";

/**
 * The graph a project starts from when the server holds no saved flow.
 *
 * The labels are the backend's block vocabulary (`WorkflowNodeType`): a previous
 * version of this file invented its own (`script_draft`, `ffmpeg_render`,
 * `omni_publish`, …), so every node it submitted was rejected by the API and the
 * canvas rendered blank labels. Both gates are one `gate` block whose `stage`
 * parameter decides which review it represents.
 */
const STARTER_NODES: WorkflowNode[] = [
  { id: "node-research", type: "research", label: "Research Engine", x: 40, y: 80, enabled: true, params: {} },
  { id: "node-script", type: "script", label: "Script Drafting", x: 230, y: 80, enabled: true, params: {} },
  { id: "node-gate1", type: "gate", label: "Gate 1: Duyệt kịch bản", x: 420, y: 80, enabled: true, params: { stage: "script" } },
  { id: "node-tts", type: "voiceover", label: "Neural Voiceover", x: 610, y: 40, enabled: true, params: {} },
  { id: "node-media", type: "ingest_external", label: "Nạp media AI", x: 610, y: 150, enabled: true, params: {} },
  { id: "node-timeline", type: "scenes", label: "Ghép timeline", x: 800, y: 90, enabled: true, params: {} },
  { id: "node-render", type: "render_plan", label: "Render plan", x: 990, y: 90, enabled: true, params: {} },
  { id: "node-gate2", type: "gate", label: "Gate 2: Duyệt video", x: 1180, y: 90, enabled: true, params: { stage: "video" } },
  { id: "node-publish", type: "publish", label: "Xuất bản đa kênh", x: 1370, y: 90, enabled: true, params: {} },
];

const STARTER_EDGES: WorkflowEdge[] = [
  { id: "e1", source: "node-research", target: "node-script" },
  { id: "e2", source: "node-script", target: "node-gate1" },
  { id: "e3", source: "node-gate1", target: "node-tts" },
  { id: "e4", source: "node-gate1", target: "node-media" },
  { id: "e5", source: "node-tts", target: "node-timeline" },
  { id: "e6", source: "node-media", target: "node-timeline" },
  { id: "e7", source: "node-timeline", target: "node-render" },
  { id: "e8", source: "node-render", target: "node-gate2" },
  { id: "e9", source: "node-gate2", target: "node-publish" },
];

export function DAGWorkflowStudio() {
  const { currentProject } = useProjectStore();
  const {
    blocksQuery,
    workflowQuery,
    validateChecklistMutation,
    saveWorkflowMutation,
    runWorkflowMutation,
  } = useWorkflowDAG(currentProject?.id);

  const [nodes, setNodes] = useState<WorkflowNode[]>(STARTER_NODES);
  const [edges, setEdges] = useState<WorkflowEdge[]>(STARTER_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("node-script");
  const [runInputs, setRunInputs] = useState('{\n  "topic": "",\n  "style": "storytelling"\n}');
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [checklist, setChecklist] = useState<WorkflowChecklist | null>(null);

  // Seed the canvas from the saved flow once per project. Re-seeding on every
  // refetch would discard whatever the operator is dragging.
  const seededFor = useRef<string | null>(null);
  useEffect(() => {
    const projectId = currentProject?.id ?? null;
    if (!projectId || seededFor.current === projectId) return;
    if (workflowQuery.data) {
      setNodes(workflowQuery.data.nodes);
      setEdges(workflowQuery.data.edges);
      seededFor.current = projectId;
    }
  }, [currentProject?.id, workflowQuery.data]);

  const palette: WorkflowBlockDef[] = blocksQuery.data ?? [];
  const selectedNode = nodes.find((node) => node.id === selectedNodeId);

  /** The document the backend validates and stores. */
  const buildWorkflow = (): Workflow => ({
    name: currentProject ? `${currentProject.name} flow` : "Production flow",
    nodes,
    edges,
    version: workflowQuery.data?.version ?? 0,
    updated_at: workflowQuery.data?.updated_at ?? new Date().toISOString(),
  });

  const log = (...lines: string[]) => setExecutionLogs((prev) => [...prev, ...lines]);

  const handleAddBlock = (blockDef: WorkflowBlockDef) => {
    const newId = `node-${Date.now()}`;
    setNodes((prev) => [
      ...prev,
      {
        id: newId,
        type: blockDef.type,
        label: blockDef.label,
        x: 100 + (prev.length % 5) * 60,
        y: 120 + (prev.length % 3) * 50,
        enabled: true,
        params: { ...blockDef.default_params },
      },
    ]);
    setSelectedNodeId(newId);
  };

  const handleDeleteSelected = () => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.filter((node) => node.id !== selectedNodeId));
    setEdges((prev) =>
      prev.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId)
    );
    setSelectedNodeId(null);
  };

  const handleRunChecklist = async () => {
    log("[Audit] Đang kiểm tra DAG trước khi lưu...");
    try {
      const result = await validateChecklistMutation.mutateAsync({ workflow: buildWorkflow() });
      setChecklist(result);
      log(
        result.ready
          ? `✅ [Audit] Đạt: ${result.node_count} khối, ${result.edge_count} liên kết, không có vấn đề.`
          : `⚠️ [Audit] Có ${result.issues.length} vấn đề cần xử lý trước khi chạy.`
      );
    } catch (error) {
      // Reporting a pass here would tell the operator the flow is safe when it
      // was never checked at all.
      log(`❌ [Audit] Không kiểm tra được: ${describeError(error)}`);
    }
  };

  const handleSaveDAG = async () => {
    try {
      await saveWorkflowMutation.mutateAsync({ workflow: buildWorkflow() });
      log("💾 [Save] Đã lưu DAG lên máy chủ.");
    } catch (error) {
      log(`❌ [Save] Lưu thất bại: ${describeError(error)}`);
    }
  };

  const handleExecuteWorkflow = async () => {
    setIsExecuting(true);
    log("🚀 [Run] Đang khởi chạy workflow trên backend...");
    try {
      const run = await runWorkflowMutation.mutateAsync({ background: false });
      log(
        ...run.steps.map(
          (step) =>
            `[${step.status}] ${step.label} (${step.type}) — ${step.duration_ms}ms${
              step.error ? ` — lỗi: ${step.error}` : ""
            }`
        )
      );
      log(
        run.status === "completed"
          ? `🏁 [Run] Hoàn tất ${run.steps.length} bước.`
          : `⚠️ [Run] Trạng thái: ${run.status}${run.message ? ` — ${run.message}` : ""}`
      );
    } catch (error) {
      log(`❌ [Run] Thất bại: ${describeError(error)}`);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-hidden">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl px-4 py-2 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
            <GitBranch className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-white tracking-wide flex items-center space-x-2">
              <span>Visual DAG Pipeline Orchestrator</span>
              <Badge variant="cyan" className="text-[9px] font-mono">
                Directed Acyclic Graph
              </Badge>
            </h2>
            <p className="text-[11px] text-gray-400">
              Định tuyến luồng sản xuất qua đồ thị phi chu trình, tuân thủ 2 cổng duyệt bắt buộc
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleRunChecklist}
            disabled={validateChecklistMutation.isPending}
            className="text-xs border-nle-border h-8 text-gray-300 hover:text-white"
          >
            <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
            Checklist Audit
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleSaveDAG}
            disabled={saveWorkflowMutation.isPending}
            className="text-xs border-nle-border h-8 text-gray-300 hover:text-white"
          >
            <Save className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
            Save DAG
          </Button>

          <Button
            size="sm"
            variant="neon"
            onClick={handleExecuteWorkflow}
            disabled={isExecuting || !currentProject}
            className="text-xs h-8"
          >
            {isExecuting ? (
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
            )}
            Execute Run
          </Button>
        </div>
      </div>

      {/* Main 3-Column Workbench: Palette (Left) · Interactive Canvas (Center) · Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0 overflow-hidden">
        {/* LEFT COLUMN: Block Palette & Run Inputs (3 cols) */}
        <div className="lg:col-span-3 flex flex-col space-y-3 min-h-0 overflow-y-auto">
          {/* Palette List — served by GET /workflow/blocks */}
          <Card className="p-3 bg-nle-surface border-nle-border flex flex-col space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center justify-between">
              <span>Khối Chức Năng (Palette)</span>
              <span className="text-[10px] text-gray-400 font-mono">{palette.length} Blocks</span>
            </span>

            {blocksQuery.isLoading && (
              <span className="text-[11px] text-gray-400 italic flex items-center">
                <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                Đang tải palette từ backend...
              </span>
            )}

            {blocksQuery.isError && (
              <span className="text-[11px] text-rose-400">
                Không tải được palette: {describeError(blocksQuery.error)}
              </span>
            )}

            <div className="space-y-1.5">
              {palette.map((block) => (
                <div
                  key={block.type}
                  onClick={() => handleAddBlock(block)}
                  className="p-2 rounded-lg bg-nle-panel border border-nle-border hover:border-nle-cyan/50 cursor-pointer flex items-center justify-between transition-all group select-none"
                  title={block.description}
                >
                  <div className="space-y-0.5 min-w-0 pr-2">
                    <span className="text-xs font-bold text-gray-200 group-hover:text-white truncate block">
                      {block.label}
                    </span>
                    <span className="text-[10px] text-gray-400 truncate block">
                      {block.description}
                    </span>
                  </div>
                  <Plus className="w-4 h-4 text-gray-500 group-hover:text-nle-cyan shrink-0" />
                </div>
              ))}
            </div>
          </Card>

          {/* Run Inputs JSON */}
          <Card className="p-3 bg-nle-surface border-nle-border space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider">
              Run Inputs (JSON Config)
            </span>
            <textarea
              value={runInputs}
              onChange={(e) => setRunInputs(e.target.value)}
              rows={4}
              spellCheck={false}
              className="w-full bg-nle-base border border-nle-border rounded-lg p-2 text-xs font-mono text-gray-300 focus:border-nle-cyan focus:outline-none resize-none"
            />
          </Card>
        </div>

        {/* CENTER COLUMN: SVG Connected DAG Canvas (6 cols) */}
        <div className="lg:col-span-6 flex flex-col bg-nle-base border border-nle-border rounded-xl relative overflow-hidden min-h-0">
          {/* Canvas Background Grid */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage: "radial-gradient(#00f0ff 1px, transparent 1px)",
              backgroundSize: "20px 20px",
            }}
          />

          {/* SVG Link Curves */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
            <defs>
              <linearGradient id="dagCableGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#00f0ff" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
            </defs>

            {edges.map((edge) => {
              const srcNode = nodes.find((n) => n.id === edge.source);
              const tgtNode = nodes.find((n) => n.id === edge.target);
              if (!srcNode || !tgtNode) return null;

              const x1 = (srcNode.x % 500) + 120;
              const y1 = (srcNode.y % 280) + 25;
              const x2 = tgtNode.x % 500;
              const y2 = (tgtNode.y % 280) + 25;
              const cx = (x1 + x2) / 2;

              return (
                <path
                  key={edge.id}
                  d={`M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`}
                  stroke="url(#dagCableGrad)"
                  strokeWidth="2.5"
                  fill="none"
                />
              );
            })}
          </svg>

          {/* Canvas Interactive Nodes Area */}
          <div className="relative w-full h-full overflow-auto p-4 min-h-[360px]">
            {nodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isGate = node.type === "gate";

              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  style={{
                    left: `${node.x % 500}px`,
                    top: `${node.y % 280}px`,
                  }}
                  className={`absolute w-36 p-2 rounded-lg border cursor-pointer select-none transition-all shadow-lg ${
                    isSelected
                      ? "border-nle-cyan bg-nle-panel ring-2 ring-nle-cyan/20 shadow-nle-cyan/10"
                      : isGate
                      ? "border-amber-500/60 bg-nle-surface/95"
                      : "border-nle-border bg-nle-surface/90 hover:border-gray-500"
                  }`}
                >
                  <div className="flex items-center justify-between pb-1 border-b border-nle-border text-[9px] font-mono">
                    <span className={isGate ? "text-amber-400 font-bold" : "text-gray-400"}>
                      {isGate ? "GATE" : "BLOCK"}
                    </span>
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isGate ? "bg-amber-400" : "bg-emerald-400"
                      } animate-pulse`}
                    />
                  </div>

                  <span className="text-[11px] font-bold text-white block mt-1 truncate">
                    {node.label}
                  </span>

                  <div className="flex justify-between items-center text-[8px] text-gray-500 font-mono mt-1 pt-1 border-t border-nle-border/40">
                    <span>{node.type}</span>
                    <span className={node.enabled ? "text-emerald-400" : "text-gray-500"}>
                      {node.enabled ? "ON" : "OFF"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Canvas Footer Toolbar */}
          <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center bg-nle-panel/80 backdrop-blur border border-nle-border rounded-lg px-3 py-1.5 text-xs text-gray-400">
            <span>
              {nodes.length} Khối · {edges.length} Liên kết
            </span>
            {selectedNode && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDeleteSelected}
                className="h-6 text-[11px] text-red-400 hover:bg-red-500/10"
              >
                <Trash2 className="w-3 h-3 mr-1" />
                Xoá Khối Đang Chọn
              </Button>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Inspector & Checklist (3 cols) */}
        <div className="lg:col-span-3 flex flex-col space-y-3 min-h-0 overflow-y-auto">
          {/* Node Inspector */}
          <Card className="p-3 bg-nle-surface border-nle-border space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider">
              Khối Thuộc Tính (Inspector)
            </span>

            {selectedNode ? (
              <div className="space-y-2 text-xs">
                <div>
                  <label className="text-gray-400 text-[10px]">Tên khối:</label>
                  <input
                    type="text"
                    value={selectedNode.label}
                    onChange={(e) => {
                      const value = e.target.value;
                      setNodes((prev) =>
                        prev.map((n) => (n.id === selectedNode.id ? { ...n, label: value } : n))
                      );
                    }}
                    className="w-full bg-nle-base border border-nle-border rounded px-2 py-1 text-xs text-white"
                  />
                </div>

                <div>
                  <label className="text-gray-400 text-[10px]">Loại block:</label>
                  <div className="font-mono text-nle-cyan bg-nle-panel px-2 py-1 rounded border border-nle-border text-[11px]">
                    {selectedNode.type}
                  </div>
                </div>

                <label className="flex items-center space-x-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={selectedNode.enabled}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setNodes((prev) =>
                        prev.map((n) => (n.id === selectedNode.id ? { ...n, enabled } : n))
                      );
                    }}
                  />
                  <span className="text-[11px]">Bật khối này khi chạy</span>
                </label>

                <div>
                  <label className="text-gray-400 text-[10px]">Cấu hình tham số (JSON):</label>
                  <textarea
                    value={JSON.stringify(selectedNode.params, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        setNodes((prev) =>
                          prev.map((n) => (n.id === selectedNode.id ? { ...n, params: parsed } : n))
                        );
                      } catch {
                        // Keep the previous params while the operator is mid-edit.
                      }
                    }}
                    rows={4}
                    className="w-full bg-nle-base border border-nle-border rounded p-2 text-[11px] font-mono text-gray-300"
                  />
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic p-3 text-center">
                Nhấp chuột vào một khối trên canvas để chỉnh sửa thuộc tính.
              </div>
            )}
          </Card>

          {/* Pre-Save Checklist Card — the verdict comes from the backend auditor */}
          <Card className="p-3 bg-nle-surface border-nle-border space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
              Pre-Save Checklist Audit
            </span>

            {!checklist ? (
              <div className="text-[11px] text-gray-500 italic">
                Chưa chạy kiểm tra. Bấm “Checklist Audit” để backend thẩm định DAG hiện tại.
              </div>
            ) : (
              <div className="space-y-1 text-xs">
                <div className="flex items-center justify-between p-1.5 rounded bg-nle-panel text-gray-300">
                  <span>Tổng thể</span>
                  <span
                    className={checklist.ready ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}
                  >
                    {checklist.ready ? "Sẵn sàng chạy" : "Cần xử lý"}
                  </span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-nle-panel text-gray-300">
                  <span>Khối / Liên kết</span>
                  <span className="font-mono text-gray-200">
                    {checklist.node_count} / {checklist.edge_count}
                  </span>
                </div>

                {checklist.issues.length === 0 ? (
                  <div className="text-[11px] text-emerald-400">Không phát hiện vấn đề.</div>
                ) : (
                  <ul className="space-y-1">
                    {checklist.issues.map((issue, index) => (
                      <li
                        key={`${issue.code}-${index}`}
                        className={`p-1.5 rounded bg-nle-panel border border-nle-border/60 ${
                          issue.severity === "error"
                            ? "text-rose-400"
                            : issue.severity === "warning"
                            ? "text-amber-400"
                            : "text-gray-300"
                        }`}
                      >
                        <span className="font-mono text-[10px] mr-1">[{issue.code}]</span>
                        {issue.message}
                        {issue.hint && (
                          <span className="block text-[10px] text-gray-500 mt-0.5">
                            Gợi ý: {issue.hint}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* BOTTOM CONSOLE & EXECUTION STREAM TERMINAL */}
      <Card className="h-32 bg-nle-base border-nle-border flex flex-col shrink-0 overflow-hidden">
        <div className="px-3 py-1.5 border-b border-nle-border bg-nle-panel flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 text-gray-300 font-semibold">
            <Terminal className="w-3.5 h-3.5 text-nle-cyan" />
            <span>Console & Execution Stream Terminal</span>
          </div>
          <span className="text-[10px] text-gray-400 font-mono">
            {isExecuting ? "Executing pipeline..." : "Idle"}
          </span>
        </div>

        <div className="p-2.5 font-mono text-[11px] text-gray-300 overflow-y-auto space-y-0.5 leading-relaxed">
          {executionLogs.length === 0 ? (
            <div className="text-gray-500 italic">
              Chưa có hoạt động. Kết quả kiểm tra và chạy workflow sẽ hiện ở đây.
            </div>
          ) : (
            executionLogs.map((line, index) => (
              <div
                key={index}
                className={
                  line.includes("❌")
                    ? "text-rose-400"
                    : line.includes("✅")
                    ? "text-emerald-400"
                    : line.includes("⚠️")
                    ? "text-amber-400"
                    : ""
                }
              >
                {line}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

/** A readable message from an unknown thrown value. */
function describeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return typeof error === "string" ? error : JSON.stringify(error);
}
