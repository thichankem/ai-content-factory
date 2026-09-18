"use client";

import React, { useState } from "react";
import { useVideoFXStore, LUTPreset } from "../../stores/useVideoFXStore";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Film,
  Activity,
  Zap,
  Gauge,
  Palette,
  Crosshair,
  RotateCcw,
  Sparkles,
  Scissors,
  Eye,
  Sliders,
  GitBranch,
} from "lucide-react";
import { FusionNodeCompositor } from "../fusion/FusionNodeCompositor";

export function VideoMotionFXStudio() {
  const {
    posX,
    posY,
    scale,
    rotation,
    opacity,
    selectedProperty,
    keyframes,
    speedRampPreset,
    speedPoints,
    lut,
    colorTemp,
    colorTint,
    exposure,
    contrast,
    colorSaturation,
    isAiProcessing,
    aiVideoStatus,
    setTransform,
    setSelectedProperty,
    setSpeedRampPreset,
    updateSpeedPoint,
    setLUT,
    setColorGrade,
    resetColorGrade,
    setAiVideoProcessing,
  } = useVideoFXStore();

  const [activeSubTab, setActiveSubTab] = useState<"motion" | "speed" | "color" | "fusion">("speed");

  // AI Quick Actions for Video FX
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-auto-reframe",
      label: "AI Auto-Reframe 9:16 (Bám chủ thể)",
      icon: Crosshair,
      onClick: async () => {
        setAiVideoProcessing(true, "AI đang nhận diện khuôn mặt và tracking chủ thể về trung tâm 9:16...");
        await new Promise((r) => setTimeout(r, 1400));
        setTransform("scale", 135);
        setTransform("posX", 10);
        setAiVideoProcessing(false, "Đã auto-reframe căn chính xác chủ thể!");
      },
    },
    {
      id: "ai-silence-cut",
      label: "AI Cắt Khoảng Lặng (Jump Cut 0.3s)",
      icon: Scissors,
      onClick: async () => {
        setAiVideoProcessing(true, "AI đang dò âm phổ và loại bỏ 4 khoảng lặng thừa...");
        await new Promise((r) => setTimeout(r, 1100));
        setAiVideoProcessing(false, "Đã cắt 4.2s khoảng lặng chết, nhịp video dồn dập hơn!");
      },
    },
    {
      id: "ai-optical-flow",
      label: "AI Optical Flow 60fps Smooth",
      icon: Sparkles,
      onClick: async () => {
        setAiVideoProcessing(true, "AI đang tính toán vector chuyển động Optical Flow...");
        await new Promise((r) => setTimeout(r, 1300));
        setAiVideoProcessing(false, "Đã nội suy khung hình 60fps siêu mượt!");
      },
    },
  ];

  const lutOptions: Array<{ id: LUTPreset; label: string; bg: string }> = [
    { id: "teal_orange", label: "Teal & Orange", bg: "from-cyan-900 to-amber-700" },
    { id: "cyberpunk", label: "Cyberpunk Neon", bg: "from-violet-900 to-cyan-700" },
    { id: "noir", label: "Film Noir 1940", bg: "from-neutral-900 to-stone-700" },
    { id: "vintage", label: "Vintage 35mm", bg: "from-amber-950 to-orange-800" },
    { id: "matrix", label: "Matrix Emerald", bg: "from-emerald-950 to-green-700" },
    { id: "clean", label: "Standard Clean", bg: "from-slate-900 to-gray-700" },
  ];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* AI Agent Bar for Video Motion FX */}
      <AIAgentBar
        tabTitle="Chỉnh sửa Video & Kỹ xảo (Motion FX Studio)"
        agentRole="Lead Motion & Colorist Artist"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Tạo camera shake giật nổ khi chuyển cảnh', 'Chỉnh màu u tối kiểu Batman')..."
        quickActions={quickActions}
        statusMessage={aiVideoStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setAiVideoProcessing(true, `AI đang xử lý video motion: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1500));
          setAiVideoProcessing(false, "Đã áp dụng hiệu ứng chuyển động và chỉnh màu từ AI Prompt!");
        }}
      />

      {/* Navigation Sub-Tabs: Motion Curves vs Speed Ramp vs Lumetri Color */}
      <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl p-1.5 shrink-0">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setActiveSubTab("speed")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubTab === "speed"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Gauge className="w-3.5 h-3.5 text-amber-400" />
            <span>CapCut Speed Ramping (Điều tốc)</span>
          </button>

          <button
            onClick={() => setActiveSubTab("motion")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubTab === "motion"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-nle-violet" />
            <span>After Effects Graph Editor (Keyframe Curves)</span>
          </button>

          <button
            onClick={() => setActiveSubTab("color")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubTab === "color"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Palette className="w-3.5 h-3.5 text-emerald-400" />
            <span>Premiere Lumetri Color & LUTs</span>
          </button>

          <button
            onClick={() => setActiveSubTab("fusion")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeSubTab === "fusion"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
            <span>DaVinci Fusion Node Graph</span>
          </button>
        </div>

        <Badge variant="cyan" className="text-[10px] hidden sm:inline-flex">
          GPU Accel On
        </Badge>
      </div>

      {/* Sub-Tab 1: CapCut Speed Ramping */}
      {activeSubTab === "speed" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[440px]">
          {/* Visual Speed Curve Viewport */}
          <div className="lg:col-span-8 bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-nle-border">
              <div>
                <h3 className="text-xs font-bold text-white flex items-center">
                  <Gauge className="w-4 h-4 mr-1.5 text-amber-400" />
                  Đường cong Điều tốc Biến thiên (Dynamic Speed Ramp)
                </h3>
                <p className="text-[11px] text-gray-400">
                  Tăng giảm tốc độ mượt mà từ 0.1x Slow-Mo đến 10x Fast-Forward theo phong cách CapCut Pro
                </p>
              </div>

              {/* Speed Presets */}
              <div className="flex items-center space-x-1 text-xs">
                {(["hero_bullet", "montage_fast", "flash_in"] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setSpeedRampPreset(p)}
                    className={`px-2 py-1 rounded text-[10px] uppercase font-bold transition-all ${
                      speedRampPreset === p
                        ? "bg-amber-400 text-black shadow-sm"
                        : "bg-nle-panel text-gray-400 hover:text-white border border-nle-border"
                    }`}
                  >
                    {p.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            {/* SVG Curve Graph Visualizer */}
            <div className="flex-1 my-3 bg-nle-base rounded-lg border border-nle-border p-4 relative flex items-center justify-center">
              {/* Speed Grid Lines */}
              <div className="absolute inset-0 p-4 flex flex-col justify-between pointer-events-none opacity-20">
                <div className="border-b border-dashed border-gray-400 text-[9px]">4.0x Fast</div>
                <div className="border-b border-dashed border-amber-400 text-[9px] text-amber-400">1.0x Normal</div>
                <div className="text-[9px]">0.2x Slow-Mo</div>
              </div>

              {/* Interactive Bezier Speed Curve */}
              <svg className="w-full h-44 overflow-visible">
                <defs>
                  <linearGradient id="speedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Path line */}
                <path
                  d={`M 20 ${140 - (speedPoints[0]?.speed || 1) * 25} C 120 ${
                    140 - (speedPoints[1]?.speed || 0.5) * 25
                  }, 240 ${140 - (speedPoints[2]?.speed || 2) * 25}, 400 ${
                    140 - (speedPoints[3]?.speed || 1) * 25
                  }`}
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3.5"
                  className="filter drop-shadow-md"
                />

                {/* Point nodes */}
                {speedPoints.map((pt, i) => {
                  const cx = 20 + i * 125;
                  const cy = Math.max(15, Math.min(140, 140 - pt.speed * 25));
                  return (
                    <g key={i}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r="7"
                        fill="#f59e0b"
                        stroke="#ffffff"
                        strokeWidth="2"
                        className="cursor-pointer hover:r-9 transition-all"
                      />
                      <text x={cx} y={cy - 12} fill="#ffffff" fontSize="10" textAnchor="middle" fontWeight="bold">
                        {pt.speed}x
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Controls for current speed points */}
            <div className="grid grid-cols-4 gap-2 pt-2 border-t border-nle-border">
              {speedPoints.map((pt, i) => (
                <div key={i} className="p-2 rounded bg-nle-panel border border-nle-border text-[11px] space-y-1">
                  <div className="flex justify-between text-gray-300">
                    <span>Điểm neo #{i + 1}</span>
                    <span className="font-mono text-amber-400 font-bold">{pt.speed}x</span>
                  </div>
                  <Slider
                    value={[pt.speed]}
                    min={0.1}
                    max={6}
                    step={0.1}
                    onValueChange={([val]) => updateSpeedPoint(i, val)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Right Side: Speed Info & Optical Flow Smooth Mode */}
          <Card className="lg:col-span-4 flex flex-col justify-between p-4 space-y-3">
            <div>
              <CardTitle className="text-xs font-bold text-white mb-1">
                Thuật toán Làm mượt Khung hình
              </CardTitle>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Khi giảm tốc độ dưới 1.0x, hệ thống kích hoạt <b>Optical Flow Frame Blending</b> để bù khung hình nhân tạo, triệt tiêu hiện tượng giật lag khung hình.
              </p>
            </div>

            <div className="p-3 bg-nle-panel border border-nle-border rounded-lg space-y-2 text-xs">
              <div className="flex justify-between items-center text-gray-200">
                <span>Chế độ Nội suy:</span>
                <Badge variant="cyan">Optical Flow AI</Badge>
              </div>
              <div className="flex justify-between items-center text-gray-200">
                <span>Giữ nguyên Cao độ giọng (Pitch Lock):</span>
                <span className="text-emerald-400 font-semibold">Bật (Active)</span>
              </div>
              <div className="flex justify-between items-center text-gray-200">
                <span>Chuyển động Motion Blur:</span>
                <span className="text-amber-400 font-semibold">180° Shutter Angle</span>
              </div>
            </div>

            <Button variant="neon" size="sm" className="w-full text-xs">
              Áp dụng Speed Ramp lên Clip
            </Button>
          </Card>
        </div>
      )}

      {/* Sub-Tab 2: After Effects Keyframe Graph Editor & Transform */}
      {activeSubTab === "motion" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[440px]">
          {/* Graph Editor Bezier Curves */}
          <div className="lg:col-span-8 bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-nle-border">
              <div>
                <h3 className="text-xs font-bold text-white flex items-center">
                  <Activity className="w-4 h-4 mr-1.5 text-nle-violet" />
                  After Effects Bezier Graph Editor
                </h3>
                <p className="text-[11px] text-gray-400">
                  Điều chỉnh tiếp tuyến Ease In / Ease Out của keyframe cho chuyển động gia tốc thực tế
                </p>
              </div>

              {/* Property Selector */}
              <div className="flex items-center space-x-1 text-xs">
                {(["scale", "opacity", "position", "rotation"] as const).map((prop) => (
                  <button
                    key={prop}
                    onClick={() => setSelectedProperty(prop)}
                    className={`px-2 py-1 rounded text-[10px] uppercase font-bold transition-all ${
                      selectedProperty === prop
                        ? "bg-nle-violet text-white shadow-sm"
                        : "bg-nle-panel text-gray-400 hover:text-white border border-nle-border"
                    }`}
                  >
                    {prop}
                  </button>
                ))}
              </div>
            </div>

            {/* Bezier Curve Canvas */}
            <div className="flex-1 my-3 bg-nle-base rounded-lg border border-nle-border p-4 relative flex items-center justify-center">
              <svg className="w-full h-44 overflow-visible">
                {/* Horizontal guide */}
                <line x1="0" y1="70" x2="500" y2="70" stroke="#252d43" strokeDasharray="4" />

                {/* Spline Bezier */}
                <path
                  d="M 30 110 C 100 110, 140 30, 240 30 C 340 30, 380 90, 470 90"
                  fill="none"
                  stroke="#8b5cf6"
                  strokeWidth="3"
                />

                {/* Keyframe nodes */}
                <circle cx="30" cy="110" r="6" fill="#8b5cf6" stroke="#ffffff" strokeWidth="2" />
                <circle cx="240" cy="30" r="6" fill="#8b5cf6" stroke="#ffffff" strokeWidth="2" />
                <circle cx="470" cy="90" r="6" fill="#8b5cf6" stroke="#ffffff" strokeWidth="2" />

                {/* Tangent handles */}
                <line x1="240" y1="30" x2="190" y2="30" stroke="#00f0ff" strokeWidth="1.5" />
                <circle cx="190" cy="30" r="4" fill="#00f0ff" />
                <line x1="240" y1="30" x2="290" y2="30" stroke="#00f0ff" strokeWidth="1.5" />
                <circle cx="290" cy="30" r="4" fill="#00f0ff" />
              </svg>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Đang hiệu chỉnh: <b>{selectedProperty.toUpperCase()}</b> Curve</span>
              <span className="text-nle-cyan">Tiếp tuyến Bezier: Smooth S-Curve</span>
            </div>
          </div>

          {/* Right Side: Transform Properties Inspector */}
          <Card className="lg:col-span-4 flex flex-col justify-between p-4 space-y-3">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <Sliders className="w-3.5 h-3.5 mr-1.5 text-nle-cyan" />
              Bảng Biến đổi (Transform Inspector)
            </CardTitle>

            <div className="space-y-2.5 text-xs">
              {/* Scale */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Phóng to (Scale)</span>
                  <span className="font-mono text-nle-cyan">{scale}%</span>
                </div>
                <Slider
                  value={[scale]}
                  min={50}
                  max={250}
                  step={1}
                  onValueChange={([val]) => setTransform("scale", val)}
                />
              </div>

              {/* Position X */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Tọa độ X</span>
                  <span className="font-mono text-nle-cyan">{posX}px</span>
                </div>
                <Slider
                  value={[posX]}
                  min={-200}
                  max={200}
                  step={1}
                  onValueChange={([val]) => setTransform("posX", val)}
                />
              </div>

              {/* Rotation */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Xoay góc (Rotation)</span>
                  <span className="font-mono text-nle-cyan">{rotation}°</span>
                </div>
                <Slider
                  value={[rotation]}
                  min={-180}
                  max={180}
                  step={1}
                  onValueChange={([val]) => setTransform("rotation", val)}
                />
              </div>

              {/* Opacity */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Độ mờ (Opacity)</span>
                  <span className="font-mono text-nle-cyan">{opacity}%</span>
                </div>
                <Slider
                  value={[opacity]}
                  min={0}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setTransform("opacity", val)}
                />
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setTransform("scale", 100);
                setTransform("posX", 0);
                setTransform("posY", 0);
                setTransform("rotation", 0);
                setTransform("opacity", 100);
              }}
              className="text-xs border-nle-border"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              Đặt lại Transform
            </Button>
          </Card>
        </div>
      )}

      {/* Sub-Tab 3: Premiere Lumetri Color & LUTs */}
      {activeSubTab === "color" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[440px]">
          {/* LUT Preset Selection Grid */}
          <div className="lg:col-span-7 bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold text-white flex items-center mb-1">
                <Palette className="w-4 h-4 mr-1.5 text-emerald-400" />
                Bộ Lọc Màu Điện Ảnh (Cinema LUTs)
              </h3>
              <p className="text-[11px] text-gray-400">
                Áp dụng bảng màu điện ảnh Premiere Pro Lumetri Color 3D LUT
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 my-3">
              {lutOptions.map((opt) => (
                <div
                  key={opt.id}
                  onClick={() => setLUT(opt.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all flex flex-col justify-between aspect-video ${
                    lut === opt.id
                      ? "border-emerald-400 ring-2 ring-emerald-400/20 shadow-lg"
                      : "border-nle-border hover:border-gray-500"
                  } bg-gradient-to-tr ${opt.bg}`}
                >
                  <span className="text-xs font-bold text-white drop-shadow">
                    {opt.label}
                  </span>
                  <div className="flex justify-between items-center text-[10px] text-white/80">
                    <span>3D LUT .cube</span>
                    {lut === opt.id && <span className="text-emerald-300 font-bold">✓ Active</span>}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-nle-border">
              <span className="text-gray-400">Không gian màu: <b>Rec.709 Standard Broadcast</b></span>
              <Button
                variant="outline"
                size="sm"
                onClick={resetColorGrade}
                className="text-[11px] h-6 px-2 border-nle-border"
              >
                <RotateCcw className="w-3 h-3 mr-1" />
                Đặt lại Màu gốc
              </Button>
            </div>
          </div>

          {/* Color Temperature & Lumetri Sliders */}
          <Card className="lg:col-span-5 flex flex-col justify-between p-4 space-y-3">
            <CardTitle className="text-xs font-bold text-white flex items-center">
              <Sliders className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              Lumetri Basic Correction
            </CardTitle>

            <div className="space-y-3 text-xs flex-1">
              {/* Temperature */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Nhiệt độ màu (Temperature)</span>
                  <span className="font-mono text-emerald-400">{colorTemp > 0 ? `+${colorTemp}` : colorTemp}</span>
                </div>
                <Slider
                  value={[colorTemp]}
                  min={-50}
                  max={50}
                  step={1}
                  onValueChange={([val]) => setColorGrade("colorTemp", val)}
                />
              </div>

              {/* Tint */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Sắc thái (Tint)</span>
                  <span className="font-mono text-emerald-400">{colorTint > 0 ? `+${colorTint}` : colorTint}</span>
                </div>
                <Slider
                  value={[colorTint]}
                  min={-50}
                  max={50}
                  step={1}
                  onValueChange={([val]) => setColorGrade("colorTint", val)}
                />
              </div>

              {/* Saturation */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Độ bão hòa (Saturation)</span>
                  <span className="font-mono text-emerald-400">{colorSaturation}%</span>
                </div>
                <Slider
                  value={[colorSaturation]}
                  min={50}
                  max={200}
                  step={1}
                  onValueChange={([val]) => setColorGrade("colorSaturation", val)}
                />
              </div>

              {/* Contrast */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Tương phản (Contrast)</span>
                  <span className="font-mono text-emerald-400">{contrast}</span>
                </div>
                <Slider
                  value={[contrast]}
                  min={-50}
                  max={50}
                  step={1}
                  onValueChange={([val]) => setColorGrade("contrast", val)}
                />
              </div>
            </div>

            <Button size="sm" variant="neon" className="w-full text-xs">
              Lưu Preset LUT Người Dùng
            </Button>
          </Card>
        </div>
      )}

      {/* Sub-Tab 4: DaVinci Resolve 19 Fusion Node Graph */}
      {activeSubTab === "fusion" && (
        <div className="flex-1 min-h-[460px]">
          <FusionNodeCompositor />
        </div>
      )}
    </div>
  );
}
