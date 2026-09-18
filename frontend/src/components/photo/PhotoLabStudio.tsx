"use client";

import React, { useRef, useEffect } from "react";
import { usePhotoStore, AspectPreset, PhotoLayer } from "../../stores/usePhotoStore";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";
import {
  Sparkles,
  Layers,
  Sliders,
  Scissors,
  Eye,
  EyeOff,
  Maximize2,
  RotateCcw,
  Download,
  Image as ImageIcon,
  Type,
  Smile,
  Wand2,
} from "lucide-react";

export function PhotoLabStudio() {
  const {
    activeImageUrl,
    aspectRatio,
    brightness,
    contrast,
    saturation,
    exposure,
    vibrance,
    temperature,
    vignette,
    blur,
    layers,
    selectedLayerId,
    isAiProcessing,
    aiStatus,
    setAspectRatio,
    setAdjustment,
    resetAdjustments,
    toggleLayerVisibility,
    setSelectedLayerId,
    setAiProcessing,
  } = usePhotoStore();

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Render canvas with filters applied
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply CSS Filter Simulation on Canvas
    const filterString = `
      brightness(${100 + brightness}%)
      contrast(${100 + contrast}%)
      saturate(${100 + saturation}%)
      blur(${blur}px)
    `;
    ctx.filter = filterString.trim();

    // Background Gradient (Base image canvas)
    const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    if (temperature > 0) {
      grad.addColorStop(0, "#1c1328");
      grad.addColorStop(1, "#2e1a12");
    } else {
      grad.addColorStop(0, "#0e1829");
      grad.addColorStop(1, "#122533");
    }
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Reset filter for layers
    ctx.filter = "none";

    // Draw Vignette if applied
    if (vignette > 0) {
      const radius = Math.max(canvas.width, canvas.height) * 0.7;
      const vigGrad = ctx.createRadialGradient(
        canvas.width / 2,
        canvas.height / 2,
        radius * (1 - vignette / 150),
        canvas.width / 2,
        canvas.height / 2,
        radius
      );
      vigGrad.addColorStop(0, "rgba(0,0,0,0)");
      vigGrad.addColorStop(1, `rgba(0,0,0,${(vignette / 100) * 0.85})`);
      ctx.fillStyle = vigGrad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    // Render Visible Layers
    layers
      .slice()
      .reverse()
      .forEach((layer) => {
        if (!layer.visible) return;

        ctx.globalAlpha = layer.opacity;

        if (layer.type === "text" && layer.content) {
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 26px Inter, sans-serif";
          ctx.textAlign = "center";
          ctx.shadowColor = "rgba(0, 240, 255, 0.8)";
          ctx.shadowBlur = 12;
          ctx.lineWidth = 4;
          ctx.strokeStyle = "#000000";
          ctx.strokeText(layer.content, canvas.width / 2, canvas.height * 0.4);
          ctx.fillText(layer.content, canvas.width / 2, canvas.height * 0.4);
          ctx.shadowBlur = 0;
        } else if (layer.type === "sticker" && layer.content) {
          ctx.font = "40px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(layer.content, canvas.width / 2, canvas.height * 0.6);
        }
        ctx.globalAlpha = 1;
      });
  }, [
    brightness,
    contrast,
    saturation,
    exposure,
    vibrance,
    temperature,
    vignette,
    blur,
    layers,
    aspectRatio,
  ]);

  // AI Quick Actions for Photo Lab
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-remove-bg",
      label: "AI Tách Nền Trong Suốt (RemBg)",
      icon: Scissors,
      onClick: async () => {
        setAiProcessing(true, "AI đang nhận diện chủ thể và tách nền...");
        await new Promise((r) => setTimeout(r, 1200));
        setAiProcessing(false, "Đã tách nền chủ thể thành công!");
      },
    },
    {
      id: "ai-upscale-4k",
      label: "AI Nâng Nét 4K Ultra HD",
      icon: Sparkles,
      onClick: async () => {
        setAiProcessing(true, "AI đang tăng độ phân giải 4x Super-Resolution...");
        await new Promise((r) => setTimeout(r, 1400));
        setAdjustment("contrast", 35);
        setAdjustment("vibrance", 25);
        setAiProcessing(false, "Đã phục chế chi tiết và nâng nét chuẩn 4K!");
      },
    },
    {
      id: "ai-auto-color",
      label: "AI Auto Cân Bằng Màu & Tương Phản",
      icon: Wand2,
      onClick: async () => {
        setAiProcessing(true, "AI đang tối ưu hóa độ rực rỡ và điểm sáng...");
        await new Promise((r) => setTimeout(r, 800));
        setAdjustment("brightness", 15);
        setAdjustment("contrast", 30);
        setAdjustment("saturation", 25);
        setAdjustment("vignette", 20);
        setAiProcessing(false, "Đã tối ưu hóa màu sắc chuẩn click-worthy viral!");
      },
    },
  ];

  const aspectPresets: Array<{ id: AspectPreset; label: string; w: number; h: number }> = [
    { id: "9:16", label: "9:16 TikTok / Shorts", w: 360, h: 640 },
    { id: "16:9", label: "16:9 YouTube Video", w: 640, h: 360 },
    { id: "1:1", label: "1:1 Instagram Post", w: 480, h: 480 },
    { id: "4:5", label: "4:5 Social Portrait", w: 384, h: 480 },
  ];

  const currentPreset = aspectPresets.find((p) => p.id === aspectRatio) || aspectPresets[0];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* AI Agent Bar for Photo Lab */}
      <AIAgentBar
        tabTitle="Chỉnh sửa Ảnh (Photo Lab)"
        agentRole="Vision & Graphic Designer"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Thêm viền hào quang neon xanh quanh chủ thể', 'Tạo hiệu ứng Cyberpunk')..."
        quickActions={quickActions}
        statusMessage={aiStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setAiProcessing(true, `AI đang thực hiện: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1500));
          setAiProcessing(false, "Đã hoàn thành chỉnh sửa ảnh từ AI Prompt!");
        }}
      />

      {/* Main Studio Grid: Left Canvas + Right Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[500px]">
        {/* Center: Canvas Viewport */}
        <div className="lg:col-span-7 bg-nle-surface border border-nle-border rounded-xl flex flex-col overflow-hidden">
          {/* Canvas Top Bar */}
          <div className="h-10 px-3 bg-nle-panel border-b border-nle-border flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <ImageIcon className="w-4 h-4 text-nle-violet" />
              <span className="font-semibold text-white">Canvas Chỉnh sửa Ảnh</span>
              <Badge variant="cyan" className="text-[10px]">
                {aspectRatio}
              </Badge>
            </div>

            {/* Aspect Ratio Buttons */}
            <div className="flex items-center space-x-1">
              {aspectPresets.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => setAspectRatio(preset.id)}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                    aspectRatio === preset.id
                      ? "bg-nle-cyan text-black font-bold"
                      : "text-gray-400 hover:text-white bg-nle-surface border border-nle-border"
                  }`}
                >
                  {preset.id}
                </button>
              ))}
            </div>
          </div>

          {/* Canvas Drawing Viewport */}
          <div className="flex-1 p-4 bg-nle-base flex items-center justify-center overflow-hidden">
            <div
              style={{
                aspectRatio:
                  aspectRatio === "9:16"
                    ? "9/16"
                    : aspectRatio === "16:9"
                    ? "16/9"
                    : aspectRatio === "1:1"
                    ? "1/1"
                    : "4/5",
                maxHeight: "440px",
              }}
              className="relative rounded-lg shadow-2xl border border-nle-border overflow-hidden bg-black/60 flex items-center justify-center"
            >
              <canvas
                ref={canvasRef}
                width={currentPreset.w}
                height={currentPreset.h}
                className="w-full h-full object-contain"
              />

              {/* Safe Zone Guide Lines */}
              <div className="absolute inset-0 border border-dashed border-nle-cyan/30 pointer-events-none p-3 flex flex-col justify-between">
                <span className="text-[9px] text-nle-cyan/60">An toàn tiêu đề (Title Safe 90%)</span>
                <span className="text-[9px] text-nle-cyan/60 text-right">Lề hành động (Action Safe)</span>
              </div>
            </div>
          </div>

          {/* Canvas Footer Bar */}
          <div className="h-9 px-3 bg-nle-panel border-t border-nle-border flex items-center justify-between text-xs">
            <span className="text-gray-400 text-[11px]">
              Kích thước: {currentPreset.w} × {currentPreset.h} px (Chuẩn Retina)
            </span>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={resetAdjustments}
                className="text-[11px] h-6 px-2 border-nle-border text-gray-300"
              >
                <RotateCcw className="w-3 h-3 mr-1" />
                Đặt lại
              </Button>
              <Button size="sm" variant="neon" className="text-[11px] h-6 px-2.5">
                <Download className="w-3 h-3 mr-1" />
                Lưu vào Media Bin
              </Button>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Photoshop Layers & Lightroom Tone Adjustments */}
        <div className="lg:col-span-5 grid grid-rows-2 gap-3 min-h-0">
          {/* Panel 1: Photoshop-style Layers Panel */}
          <Card className="flex flex-col overflow-hidden">
            <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-bold text-white flex items-center">
                <Layers className="w-3.5 h-3.5 mr-1.5 text-nle-cyan" />
                Lớp Đồ Họa (Photoshop Layers)
              </CardTitle>
              <Badge variant="cyan" className="text-[9px]">
                {layers.length} Layers
              </Badge>
            </CardHeader>

            <CardContent className="p-2 space-y-1.5 flex-1 overflow-y-auto">
              {layers.map((layer) => {
                const isSelected = selectedLayerId === layer.id;
                return (
                  <div
                    key={layer.id}
                    onClick={() => setSelectedLayerId(layer.id)}
                    className={`p-2 rounded-lg border flex items-center justify-between cursor-pointer transition-all ${
                      isSelected
                        ? "bg-nle-surface border-nle-cyan text-white shadow-sm shadow-nle-cyan/10"
                        : "bg-nle-panel border-nle-border text-gray-300 hover:border-gray-600"
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleLayerVisibility(layer.id);
                        }}
                        className="p-1 text-gray-400 hover:text-white"
                      >
                        {layer.visible ? (
                          <Eye className="w-3.5 h-3.5 text-nle-cyan" />
                        ) : (
                          <EyeOff className="w-3.5 h-3.5 text-gray-600" />
                        )}
                      </button>

                      {layer.type === "text" && <Type className="w-3.5 h-3.5 text-nle-violet" />}
                      {layer.type === "sticker" && <Smile className="w-3.5 h-3.5 text-nle-amber" />}
                      {layer.type === "image" && <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />}
                      {layer.type === "adjustment" && <Sliders className="w-3.5 h-3.5 text-rose-400" />}

                      <span className="text-xs font-medium truncate max-w-[140px]">
                        {layer.name}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1 text-[10px] text-gray-400 font-mono">
                      <span>{layer.blendMode}</span>
                      <span>•</span>
                      <span>{(layer.opacity * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Panel 2: Lightroom Tone Curves & Adjustments Sliders */}
          <Card className="flex flex-col overflow-hidden">
            <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-bold text-white flex items-center">
                <Sliders className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
                Cân Chỉnh Màu Sắc & Tone (Lightroom Engine)
              </CardTitle>
            </CardHeader>

            <CardContent className="p-3 space-y-3 flex-1 overflow-y-auto text-xs">
              {/* Brightness */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Độ sáng (Brightness)</span>
                  <span className="font-mono text-nle-cyan">{brightness > 0 ? `+${brightness}` : brightness}</span>
                </div>
                <Slider
                  value={[brightness]}
                  min={-100}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setAdjustment("brightness", val)}
                />
              </div>

              {/* Contrast */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Độ tương phản (Contrast)</span>
                  <span className="font-mono text-nle-cyan">{contrast > 0 ? `+${contrast}` : contrast}</span>
                </div>
                <Slider
                  value={[contrast]}
                  min={-100}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setAdjustment("contrast", val)}
                />
              </div>

              {/* Saturation */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Độ rực màu (Saturation)</span>
                  <span className="font-mono text-nle-cyan">{saturation > 0 ? `+${saturation}` : saturation}</span>
                </div>
                <Slider
                  value={[saturation]}
                  min={-100}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setAdjustment("saturation", val)}
                />
              </div>

              {/* Vignette */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Tối góc (Vignette)</span>
                  <span className="font-mono text-nle-cyan">{vignette}%</span>
                </div>
                <Slider
                  value={[vignette]}
                  min={0}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setAdjustment("vignette", val)}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
