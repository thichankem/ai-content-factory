"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  GitBranch,
  Play,
  Sparkles,
  Layers,
  Activity,
  Sliders,
  Maximize2,
  Minimize2,
  Eye,
  Plus,
  Zap,
} from "lucide-react";

interface FusionNode {
  id: string;
  name: string;
  type: "input" | "ai" | "effect" | "merge" | "output";
  x: number;
  y: number;
  status: "active" | "cached" | "idle";
  params: Record<string, string | number>;
}

const DEFAULT_NODES: FusionNode[] = [
  { id: "node-in1", name: "MediaIn1 (Base 4K)", type: "input", x: 40, y: 50, status: "cached", params: { res: "3840x2160", fps: "60" } },
  { id: "node-mask", name: "MagicMask AI (Neural Cutout)", type: "ai", x: 220, y: 50, status: "active", params: { model: "DepthMap v2", feather: "4.5px" } },
  { id: "node-lut", name: "LumetriColor (Cyberpunk)", type: "effect", x: 220, y: 160, status: "cached", params: { lut: "Cyberpunk.cube", gain: "1.2" } },
  { id: "node-in2", name: "MediaIn2 (B-Roll City)", type: "input", x: 40, y: 160, status: "cached", params: { res: "1080x1920", alpha: "Yes" } },
  { id: "node-merge", name: "Merge1 (Composite Over)", type: "merge", x: 420, y: 100, status: "active", params: { operator: "Over", blend: "1.0" } },
  { id: "node-out", name: "MediaOut1 (Master Stream)", type: "output", x: 600, y: 100, status: "active", params: { colorSpace: "Rec.709", bitDepth: "10-bit" } },
];

export function FusionNodeCompositor() {
  const [nodes, setNodes] = useState<FusionNode[]>(DEFAULT_NODES);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("node-merge");
  const [isExecuting, setIsExecuting] = useState(false);
  const [renderMessage, setRenderMessage] = useState<string | null>(null);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || nodes[0];

  const handleExecuteGraph = async () => {
    setIsExecuting(true);
    setRenderMessage("DaVinci Neural Engine đang render luồng Node Compositing...");
    await new Promise((r) => setTimeout(r, 1400));
    setIsExecuting(false);
    setRenderMessage("✅ Kết xuất đồ thị Node Fusion hoàn tất: Sẵn sàng phát lại thời gian thực!");
  };

  return (
    <Card className="h-full flex flex-col bg-nle-surface border-nle-border overflow-hidden">
      {/* Top Header */}
      <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
        <div className="flex items-center space-x-2">
          <GitBranch className="w-4 h-4 text-emerald-400" />
          <CardTitle className="text-xs font-bold text-white tracking-wide">
            DaVinci Resolve Fusion 19 • Node Graph Compositor
          </CardTitle>
        </div>

        <div className="flex items-center space-x-2">
          <Badge variant="emerald" className="text-[9px] uppercase font-mono">
            Node-based VFX
          </Badge>
          <Button
            size="sm"
            variant="neon"
            onClick={handleExecuteGraph}
            disabled={isExecuting}
            className="text-[11px] h-6 px-2.5"
          >
            <Play className="w-3 h-3 mr-1 fill-current" />
            Render Node Tree
          </Button>
        </div>
      </CardHeader>

      {/* Main Row: Left Node Graph Canvas + Right Node Inspector */}
      <div className="flex-1 flex overflow-hidden">
        {/* Node Graph Interactive Canvas */}
        <div className="flex-1 bg-nle-base relative overflow-hidden flex items-center justify-center p-4">
          {/* Subtle Grid Pattern Background */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage: "radial-gradient(#00f0ff 1px, transparent 1px)",
              backgroundSize: "20px 20px",
            }}
          />

          {/* SVG Connecting Cables */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
            <defs>
              <linearGradient id="cableGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#00f0ff" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
            </defs>

            {/* In1 -> MagicMask */}
            <path d="M 160 80 C 190 80, 190 80, 220 80" stroke="url(#cableGrad)" strokeWidth="2.5" fill="none" />
            {/* In2 -> Lumetri */}
            <path d="M 160 190 C 190 190, 190 190, 220 190" stroke="url(#cableGrad)" strokeWidth="2.5" fill="none" />
            {/* MagicMask -> Merge */}
            <path d="M 340 80 C 380 80, 380 120, 420 120" stroke="url(#cableGrad)" strokeWidth="2.5" fill="none" />
            {/* Lumetri -> Merge */}
            <path d="M 340 190 C 380 190, 380 140, 420 140" stroke="url(#cableGrad)" strokeWidth="2.5" fill="none" />
            {/* Merge -> MediaOut */}
            <path d="M 540 130 C 570 130, 570 130, 600 130" stroke="#10b981" strokeWidth="3" fill="none" />
          </svg>

          {/* Draggable/Selectable Nodes Container */}
          <div className="relative w-full h-full max-w-2xl max-h-72">
            {nodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  style={{ left: `${node.x}px`, top: `${node.y}px` }}
                  className={`absolute w-32 p-2 rounded-lg border cursor-pointer select-none transition-all shadow-lg ${
                    isSelected
                      ? "border-emerald-400 bg-nle-panel ring-2 ring-emerald-400/20 shadow-emerald-400/10"
                      : "border-nle-border bg-nle-surface/90 hover:border-gray-500"
                  }`}
                >
                  <div className="flex items-center justify-between pb-1 border-b border-nle-border text-[9px] font-mono">
                    <span className="uppercase text-gray-400">{node.type}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  </div>

                  <span className="text-[11px] font-bold text-white block mt-1 truncate">
                    {node.name}
                  </span>

                  <div className="flex justify-between items-center text-[8px] text-gray-400 font-mono mt-1 pt-1 border-t border-nle-border/40">
                    <span>Input</span>
                    <span>Output</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Canvas Mini-map (DaVinci Fusion style top-right) */}
          <div className="absolute top-2 right-2 w-28 h-16 rounded border border-nle-border bg-nle-panel/80 p-1 pointer-events-none hidden sm:flex flex-col justify-between">
            <span className="text-[8px] font-mono text-gray-500">Navigator Map</span>
            <div className="flex space-x-1">
              <span className="w-2 h-1 bg-cyan-400 rounded-xs" />
              <span className="w-3 h-1 bg-emerald-400 rounded-xs" />
              <span className="w-2 h-1 bg-violet-400 rounded-xs" />
            </div>
          </div>
        </div>

        {/* Right: Selected Node Inspector (Tools & Modifiers) */}
        <div className="w-56 border-l border-nle-border bg-nle-panel p-3 flex flex-col justify-between text-xs shrink-0">
          <div className="space-y-2.5">
            <div className="pb-2 border-b border-nle-border">
              <span className="text-[10px] text-gray-400 uppercase font-mono">Thuộc tính Node</span>
              <h4 className="font-bold text-white text-xs truncate">{selectedNode.name}</h4>
            </div>

            <div className="space-y-2 text-[11px]">
              {Object.entries(selectedNode.params).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center text-gray-300">
                  <span className="capitalize">{k}:</span>
                  <span className="font-mono text-emerald-400 font-bold">{v}</span>
                </div>
              ))}
            </div>

            <div className="p-2 rounded bg-nle-base border border-nle-border space-y-1 text-[10px] text-gray-400">
              <span className="text-white font-semibold block">DaVinci Neural Engine:</span>
              <span>Tính toán GPU 32-bit float pipeline không suy hao chất lượng.</span>
            </div>
          </div>

          <Button variant="outline" size="sm" className="w-full text-xs border-nle-border">
            + Thêm Modifier FX
          </Button>
        </div>
      </div>

      {/* Bottom Notification */}
      {renderMessage && (
        <div className="p-2 bg-emerald-500/10 border-t border-emerald-500/20 text-emerald-400 text-[11px] flex items-center justify-between">
          <span>{renderMessage}</span>
          <Badge variant="emerald" className="text-[9px]">
            Fusion Active
          </Badge>
        </div>
      )}
    </Card>
  );
}
