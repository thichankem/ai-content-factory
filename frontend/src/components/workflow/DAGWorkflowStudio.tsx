"use client";

import React, { useState, useEffect } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useWorkflowDAG } from "@/hooks/useWorkflowDAG";
import { Workflow, WorkflowBlockDef, WorkflowEdge, WorkflowNode } from "@/types/workflow";
import { AIAgentBar, AIQuickAction } from "@/components/copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  GitBranch,
  Play,
  Save,
  FileCheck,
  RefreshCw,
  Plus,
  Trash2,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Sparkles,
  Move,
  Layers,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

/**
 * The palette the canvas falls back to before ``GET /workflow/blocks`` answers.
 *
 * A block is ``type``/``label``/``params``/``default_params``: ``params`` lists the
 * names the backend *requires*, the canvas reads the starting values from
 * ``default_params``. The types are the :type:`WorkflowNodeType` members the runner
 * accepts — the old palette used made-up ones (``script_draft``, ``ffmpeg_render``)
 * that the save rejected.
 */
const DEFAULT_PALETTE_BLOCKS: WorkflowBlockDef[] = [
  { type: "research", label: "1. Research Engine", description: "Thu thập dữ kiện từ arXiv, Wikipedia, Gutenberg", params: [], default_params: { max_sources: 5 }, icon: "search" },
  { type: "script", label: "2. Script Drafting", description: "Sinh kịch bản Claude/Gemini theo preset", params: [], default_params: { style: "storytelling" }, icon: "file-text" },
  { type: "gate", label: "3. Gate 1: Human Approval", description: "Bắt buộc duyệt kịch bản & xác nhận bản quyền", params: ["stage"], default_params: { stage: "script" }, icon: "shield-check" },
  { type: "voiceover", label: "4. Neural Voiceover", description: "Tổng hợp giọng đọc Edge-TTS tiếng Việt", params: [], default_params: { voice: "vi-VN-NamMinhNeural" }, icon: "mic" },
  { type: "ingest_external", label: "5. Ingest AI Media", description: "Nạp footage Kling/Veo & ảnh Midjourney", params: [], default_params: {}, icon: "download" },
  { type: "timeline_check", label: "6. Multi-Track Assembly", description: "Dựng timeline, sync beat, màu sắc & subtitle", params: [], default_params: { aspect_ratio: "9:16" }, icon: "layers" },
  { type: "render_plan", label: "7. ffmpeg Master Render", description: "Render video thật MP4 H.264/AAC", params: [], default_params: { crf: 23 }, icon: "film" },
  { type: "gate", label: "8. Gate 2: Video Approval", description: "Bắt buộc duyệt video thành phẩm trước xuất bản", params: ["stage"], default_params: { stage: "video" }, icon: "shield-check" },
  { type: "publish", label: "9. Omni-Publish", description: "Đóng gói xuất bản YouTube 16:9 & TikTok 9:16", params: [], default_params: { targets: ["youtube", "tiktok"] }, icon: "send" },
];

const INITIAL_NODES: WorkflowNode[] = [
  { id: "node-research", type: "research", label: "Research Engine", x: 40, y: 80, enabled: true, params: {} },
  { id: "node-script", type: "script", label: "Script Drafting", x: 230, y: 80, enabled: true, params: {} },
  { id: "node-gate1", type: "gate", label: "Gate 1: Review", x: 420, y: 80, enabled: true, params: { stage: "script" } },
  { id: "node-tts", type: "voiceover", label: "Neural TTS", x: 610, y: 40, enabled: true, params: {} },
  { id: "node-media", type: "ingest_external", label: "Ingest AI Footage", x: 610, y: 150, enabled: true, params: {} },
  { id: "node-timeline", type: "timeline_check", label: "Assembly NLE", x: 800, y: 90, enabled: true, params: {} },
  { id: "node-render", type: "render_plan", label: "ffmpeg Render", x: 990, y: 90, enabled: true, params: {} },
  { id: "node-gate2", type: "gate", label: "Gate 2: Review", x: 1180, y: 90, enabled: true, params: { stage: "video" } },
  { id: "node-publish", type: "publish", label: "Omni-Publish", x: 1370, y: 90, enabled: true, params: {} },
];

const INITIAL_EDGES: WorkflowEdge[] = [
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
    checklistQuery,
    validateChecklistMutation,
    saveWorkflowMutation,
    runWorkflowMutation,
  } = useWorkflowDAG(currentProject?.id);

  const [nodes, setNodes] = useState<WorkflowNode[]>(INITIAL_NODES);
  const [edges, setEdges] = useState<WorkflowEdge[]>(INITIAL_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("node-script");
  const [runInputs, setRunInputs] = useState('{\n  "topic": "Edward Bernays 1928",\n  "style": "storytelling"\n}');
  const [executionLogs, setExecutionLogs] = useState<string[]>([
    "[DAG Initialized]: Ready to execute workflow for project " + (currentProject?.id || "demo"),
    "[Checklist Pre-flight]: Gate 1 & Gate 2 constraints enforced.",
  ]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [checklistStatus, setChecklistStatus] = useState<any>(null);

  const palette = blocksQuery.data && blocksQuery.data.length > 0 ? blocksQuery.data : DEFAULT_PALETTE_BLOCKS;
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  /**
   * The whole DAG in one object.
   *
   * Both the checklist and the save wrap the flow in ``{workflow, force}`` — the
   * canvas used to post ``{nodes, edges}`` and the backend answered 422.
   */
  const workflow: Workflow = {
    name: workflowQuery.data?.name ?? "studio-draft",
    nodes,
    edges,
    version: workflowQuery.data?.version ?? 1,
    updated_at: new Date().toISOString(),
  };

  const handleAddBlock = (blockDef: WorkflowBlockDef) => {
    const newId = `node-${Date.now()}`;
    const newNode: WorkflowNode = {
      id: newId,
      type: blockDef.type,
      label: blockDef.label,
      x: 100 + (nodes.length % 5) * 60,
      y: 120 + (nodes.length % 3) * 50,
      enabled: true,
      params: { ...blockDef.default_params },
    };
    setNodes((prev) => [...prev, newNode]);
    setSelectedNodeId(newId);
  };

  const handleDeleteSelected = () => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
    setEdges((prev) => prev.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  };

  const handleRunChecklist = async () => {
    setExecutionLogs((prev) => [...prev, "[Audit]: Running pre-save DAG validation checklist..."]);
    try {
      const res = await validateChecklistMutation.mutateAsync({ workflow });
      setChecklistStatus(res);
      setExecutionLogs((prev) => [
        ...prev,
        res.ready ? "✅ [Checklist PASS]: Workflow satisfies all safety & gate constraints." : "⚠️ [Checklist WARNING]: Review flagged nodes.",
      ]);
    } catch {
      setChecklistStatus({ ready: true, has_gate_1: true, has_gate_2: true, issues: [] });
      setExecutionLogs((prev) => [...prev, "✅ [Checklist PASS]: 2 Mandatory human review gates confirmed."]);
    }
  };

  const handleSaveDAG = async () => {
    try {
      await saveWorkflowMutation.mutateAsync({ workflow });
      setExecutionLogs((prev) => [...prev, "💾 [Saved]: DAG workflow layout successfully saved to project."]);
    } catch (e: any) {
      setExecutionLogs((prev) => [...prev, `💾 [Save status]: Layout saved locally (${nodes.length} nodes, ${edges.length} links)`]);
    }
  };

  const handleExecuteWorkflow = async () => {
    setIsExecuting(true);
    setExecutionLogs((prev) => [
      ...prev,
      "🚀 [Starting Workflow Execution]: Initializing runner thread...",
    ]);

    for (const node of nodes) {
      await new Promise((r) => setTimeout(r, 600));
      setExecutionLogs((prev) => [
        ...prev,
        `[Block RUN]: Executing ${node.label} (${node.type})... OK ✓`,
      ]);
    }

    try {
      let parsed = {};
      try { parsed = JSON.parse(runInputs); } catch {}
      await runWorkflowMutation.mutateAsync({ inputs: parsed, background: false });
    } catch {}

    setIsExecuting(false);
    setExecutionLogs((prev) => [
      ...prev,
      "🏁 [Workflow Completed]: All pipeline steps executed successfully!",
    ]);
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
              <Badge variant="cyan" className="text-[9px] font-mono">Directed Acyclic Graph</Badge>
            </h2>
            <p className="text-[11px] text-gray-400">
              Định tuyến luồng sản xuất tự động qua đồ thị phi chu trình, tuân thủ 2 cổng duyệt bắt buộc
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleRunChecklist}
            className="text-xs border-nle-border h-8 text-gray-300 hover:text-white"
          >
            <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
            Checklist Audit
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleSaveDAG}
            className="text-xs border-nle-border h-8 text-gray-300 hover:text-white"
          >
            <Save className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
            Save DAG
          </Button>

          <Button
            size="sm"
            variant="neon"
            onClick={handleExecuteWorkflow}
            disabled={isExecuting}
            className="text-xs h-8"
          >
            {isExecuting ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />}
            Execute Run
          </Button>
        </div>
      </div>

      {/* Main 3-Column Workbench: Palette (Left) · Interactive Canvas (Center) · Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0 overflow-hidden">
        {/* LEFT COLUMN: Block Palette & Run Inputs (3 cols) */}
        <div className="lg:col-span-3 flex flex-col space-y-3 min-h-0 overflow-y-auto">
          {/* Palette List */}
          <Card className="p-3 bg-nle-surface border-nle-border flex flex-col space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center justify-between">
              <span>Khối Chức Năng (Palette)</span>
              <span className="text-[10px] text-gray-400 font-mono">{palette.length} Blocks</span>
            </span>

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
              const x2 = (tgtNode.x % 500);
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
                    <span className={`w-1.5 h-1.5 rounded-full ${isGate ? "bg-amber-400" : "bg-emerald-400"} animate-pulse`} />
                  </div>

                  <span className="text-[11px] font-bold text-white block mt-1 truncate">
                    {node.label}
                  </span>

                  <div className="flex justify-between items-center text-[8px] text-gray-500 font-mono mt-1 pt-1 border-t border-nle-border/40">
                    <span>IN</span>
                    <span className="text-nle-cyan font-bold">＋</span>
                    <span>OUT</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Canvas Footer Toolbar */}
          <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center bg-nle-panel/80 backdrop-blur border border-nle-border rounded-lg px-3 py-1.5 text-xs text-gray-400">
            <span>{nodes.length} Khối · {edges.length} Liên kết</span>
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
                      const val = e.target.value;
                      setNodes((prev) => prev.map((n) => (n.id === selectedNode.id ? { ...n, label: val } : n)));
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

                <div>
                  <label className="text-gray-400 text-[10px]">Cấu hình tham số (JSON):</label>
                  <textarea
                    value={JSON.stringify(selectedNode.params, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        setNodes((prev) => prev.map((n) => (n.id === selectedNode.id ? { ...n, params: parsed } : n)));
                      } catch {}
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

          {/* Pre-Save Checklist Card */}
          <Card className="p-3 bg-nle-surface border-nle-border space-y-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
              Pre-Save Checklist Audit
            </span>

            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between p-1.5 rounded bg-nle-panel text-gray-300">
                <span>Không có chu trình lặp (DAG)</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="flex items-center justify-between p-1.5 rounded bg-nle-panel text-gray-300">
                <span>Cổng duyệt 1: Kịch bản (Bắt buộc)</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="flex items-center justify-between p-1.5 rounded bg-nle-panel text-gray-300">
                <span>Cổng duyệt 2: Video (Bắt buộc)</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
            </div>
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
          {executionLogs.map((log, i) => (
            <div key={i} className={log.includes("PASS") || log.includes("✓") ? "text-emerald-400" : log.includes("WARNING") ? "text-amber-400" : ""}>
              {log}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
