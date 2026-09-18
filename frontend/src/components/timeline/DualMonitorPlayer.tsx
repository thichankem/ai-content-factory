"use client";

import React, { useRef, useEffect, useState } from "react";
import { usePlayerStore } from "../../stores/usePlayerStore";
import { useTimelineStore } from "../../stores/useTimelineStore";
import { useUIStore, AdobeTool, MonitorTab } from "../../stores/useUIStore";
import { formatTimecode } from "../../lib/utils";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Shield,
  Maximize2,
  Camera,
  Layers,
  Activity,
  MousePointer,
  Scissors,
  PenTool,
  Hand,
  Type,
  MoveHorizontal,
  ChevronRight,
  Sparkles,
} from "lucide-react";

export function DualMonitorPlayer() {
  const {
    currentTime,
    duration,
    isPlaying,
    volume,
    isMuted,
    loop,
    safeZoneEnabled,
    vuLeft,
    vuRight,
    setCurrentTime,
    togglePlay,
    setVolume,
    toggleMute,
    toggleLoop,
    toggleSafeZone,
    setVU,
  } = usePlayerStore();

  const { scenes, selectedSceneIndex } = useTimelineStore();
  const { activeTool, setActiveTool, activeMonitorTab, setActiveMonitorTab } = useUIStore();

  const [aspectMode, setAspectMode] = useState<"9:16" | "16:9">("9:16");
  const [resolutionScale, setResolutionScale] = useState<"Full" | "1/2" | "Fit">("Fit");
  const [clampSignal, setClampSignal] = useState(true);

  const programCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const sourceCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const scopesCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Tools definition (Adobe Premiere Pro Toolbar)
  const adobeTools: Array<{ id: AdobeTool; label: string; shortcut: string; icon: React.ComponentType<{ className?: string }> }> = [
    { id: "select", label: "Selection Tool", shortcut: "V", icon: MousePointer },
    { id: "trackSelect", label: "Track Select Forward", shortcut: "A", icon: ChevronRight },
    { id: "ripple", label: "Ripple Edit Tool", shortcut: "B", icon: MoveHorizontal },
    { id: "razor", label: "Razor Tool", shortcut: "C", icon: Scissors },
    { id: "slip", label: "Slip Tool", shortcut: "Y", icon: MoveHorizontal },
    { id: "pen", label: "Pen Tool", shortcut: "P", icon: PenTool },
    { id: "hand", label: "Hand Tool", shortcut: "H", icon: Hand },
    { id: "type", label: "Type Tool", shortcut: "T", icon: Type },
  ];

  // Playback timer & Live VU + Scopes Loop
  useEffect(() => {
    let animId: number;
    let lastTime = performance.now();

    const render = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;

      if (isPlaying) {
        const nextTime = currentTime + dt;
        if (nextTime >= duration) {
          if (loop) {
            setCurrentTime(0);
          } else {
            usePlayerStore.getState().setIsPlaying(false);
            setCurrentTime(duration);
          }
        } else {
          setCurrentTime(nextTime);
        }

        // Live VU meter fluctuations
        const l = Math.min(1, Math.max(0.12, 0.45 + Math.random() * 0.45));
        const r = Math.min(1, Math.max(0.1, 0.42 + Math.random() * 0.45));
        setVU(l, r);
      } else {
        setVU(0.06, 0.06);
      }

      // 1. Draw Program Canvas
      const progCanvas = programCanvasRef.current;
      if (progCanvas) {
        const ctx = progCanvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#090a0f";
          ctx.fillRect(0, 0, progCanvas.width, progCanvas.height);

          // Render gradient background
          const grad = ctx.createLinearGradient(0, 0, progCanvas.width, progCanvas.height);
          grad.addColorStop(0, "#101424");
          grad.addColorStop(1, "#182136");
          ctx.fillStyle = grad;
          ctx.fillRect(0, 0, progCanvas.width, progCanvas.height);

          // Current scene text
          const currentScene = scenes[selectedSceneIndex ?? 0];
          if (currentScene) {
            ctx.fillStyle = "#00f0ff";
            ctx.font = "bold 20px Inter, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(currentScene.label || `Scene ${(selectedSceneIndex ?? 0) + 1}`, progCanvas.width / 2, progCanvas.height / 2 - 20);

            ctx.fillStyle = "#ffffff";
            ctx.font = "14px Inter, sans-serif";
            const text = currentScene.text || "Timeline Master Output Active";
            ctx.fillText(text.length > 32 ? text.slice(0, 32) + "..." : text, progCanvas.width / 2, progCanvas.height / 2 + 15);
          } else {
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Inter, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("Ready for playback", progCanvas.width / 2, progCanvas.height / 2);
          }
        }
      }

      // 2. Draw Source Canvas (Raw audio / video waveform preview)
      const srcCanvas = sourceCanvasRef.current;
      if (srcCanvas) {
        const ctx = srcCanvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#0b111e";
          ctx.fillRect(0, 0, srcCanvas.width, srcCanvas.height);

          // Draw green audio waveform lines (Premiere Pro style)
          ctx.strokeStyle = "#10b981";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          const midY = srcCanvas.height / 2;
          ctx.moveTo(0, midY);
          for (let x = 0; x < srcCanvas.width; x += 3) {
            const h = Math.sin(x * 0.05 + now * 0.002) * 35 * Math.cos(x * 0.02);
            ctx.lineTo(x, midY + h);
          }
          ctx.stroke();

          // Text overlay
          ctx.fillStyle = "#94a3b8";
          ctx.font = "11px JetBrains Mono, monospace";
          ctx.textAlign = "left";
          ctx.fillText("SOURCE: b_roll_city_4k.mp4 [In: 00:01:20 • Out: 00:06:14]", 10, 20);
        }
      }

      // 3. Draw Lumetri Scopes Canvas (RGB Parade Waveform)
      const scopesCanvas = scopesCanvasRef.current;
      if (scopesCanvas) {
        const ctx = scopesCanvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#07080c";
          ctx.fillRect(0, 0, scopesCanvas.width, scopesCanvas.height);

          // Grid lines (0, 60, 120, 180, 255)
          ctx.strokeStyle = "#1f293d";
          ctx.lineWidth = 1;
          for (let y = 10; y < scopesCanvas.height; y += 30) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(scopesCanvas.width, y);
            ctx.stroke();
          }

          // Render Red, Green, Blue Parade
          const widthThird = scopesCanvas.width / 3;

          // Red Parade
          ctx.strokeStyle = "rgba(239, 68, 68, 0.75)";
          for (let x = 5; x < widthThird - 5; x += 4) {
            const amp = 40 + Math.sin(x * 0.1 + now * 0.003) * 30;
            ctx.strokeRect(x, scopesCanvas.height - amp - 15, 2, amp);
          }

          // Green Parade
          ctx.strokeStyle = "rgba(16, 185, 129, 0.75)";
          for (let x = widthThird + 5; x < widthThird * 2 - 5; x += 4) {
            const amp = 50 + Math.cos(x * 0.12 + now * 0.002) * 35;
            ctx.strokeRect(x, scopesCanvas.height - amp - 15, 2, amp);
          }

          // Blue Parade
          ctx.strokeStyle = "rgba(59, 130, 246, 0.75)";
          for (let x = widthThird * 2 + 5; x < scopesCanvas.width - 5; x += 4) {
            const amp = 45 + Math.sin(x * 0.08 + now * 0.003) * 30;
            ctx.strokeRect(x, scopesCanvas.height - amp - 15, 2, amp);
          }

          // Labels
          ctx.fillStyle = "#ef4444";
          ctx.font = "bold 10px JetBrains Mono";
          ctx.fillText("RED", 15, 20);
          ctx.fillStyle = "#10b981";
          ctx.fillText("GREEN", widthThird + 15, 20);
          ctx.fillStyle = "#3b82f6";
          ctx.fillText("BLUE", widthThird * 2 + 15, 20);
        }
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, currentTime, duration, loop, scenes, selectedSceneIndex, setCurrentTime, setVU]);

  return (
    <div className="flex flex-col h-full bg-nle-surface border border-nle-border rounded-xl overflow-hidden shadow-lg">
      {/* Top Header Bar with Workspace Monitors Tabs & SMPTE Timecode */}
      <div className="h-10 px-3 bg-nle-panel border-b border-nle-border flex items-center justify-between text-xs">
        {/* Monitor View Tabs */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setActiveMonitorTab("program")}
            className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeMonitorTab === "program"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <span>Program Monitor</span>
            <Badge variant="cyan" className="text-[9px] uppercase px-1">
              Master
            </Badge>
          </button>

          <button
            onClick={() => setActiveMonitorTab("source")}
            className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeMonitorTab === "source"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <span>Source Monitor</span>
            <span className="text-[10px] text-gray-400">{`{In/Out}`}</span>
          </button>

          <button
            onClick={() => setActiveMonitorTab("scopes")}
            className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
              activeMonitorTab === "scopes"
                ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Lumetri Scopes</span>
          </button>
        </div>

        {/* Right Info: Timecode + Aspect Switcher + Safe Zone */}
        <div className="flex items-center space-x-2">
          {/* Aspect Ratio Switch */}
          <button
            onClick={() => setAspectMode(aspectMode === "9:16" ? "16:9" : "9:16")}
            className="px-2 py-0.5 rounded text-[10px] font-mono bg-nle-surface border border-nle-border text-gray-300 hover:text-white"
          >
            {aspectMode}
          </button>

          {/* Safe Margins HUD */}
          <button
            onClick={toggleSafeZone}
            className={`p-1 rounded transition-colors ${
              safeZoneEnabled ? "text-nle-cyan bg-nle-cyan/20" : "text-gray-400 hover:text-white"
            }`}
            title="Bật/Tắt Vùng An Toàn TikTok Safe Zones (Title & Action Safe)"
          >
            <Shield className="w-3.5 h-3.5" />
          </button>

          {/* SMPTE Timecode */}
          <span className="font-mono text-xs font-bold text-nle-cyan tracking-wider bg-black/50 px-2 py-0.5 rounded border border-nle-cyan/30">
            {formatTimecode(currentTime)}
          </span>
        </div>
      </div>

      {/* Main Viewport Row: Left Adobe Tools + Center Monitor Canvas + Right Stereo VU Meter */}
      <div className="flex-1 flex overflow-hidden bg-nle-base relative">
        {/* 1. Adobe Premiere Pro Vertical Tool Palette */}
        <div className="w-10 border-r border-nle-border bg-nle-panel flex flex-col items-center py-2 space-y-1 shrink-0 z-20">
          {adobeTools.map((tool) => {
            const Icon = tool.icon;
            const isToolActive = activeTool === tool.id;
            return (
              <button
                key={tool.id}
                onClick={() => setActiveTool(tool.id)}
                title={`${tool.label} (${tool.shortcut})`}
                className={`w-7 h-7 rounded-md flex items-center justify-center transition-all ${
                  isToolActive
                    ? "bg-nle-cyan text-black font-bold shadow-md shadow-nle-cyan/20"
                    : "text-gray-400 hover:text-white hover:bg-nle-surface"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
              </button>
            );
          })}
        </div>

        {/* 2. Center Screen: Active Monitor View */}
        <div className="flex-1 flex items-center justify-center p-3 relative overflow-hidden">
          {/* Program Monitor View */}
          {activeMonitorTab === "program" && (
            <div
              style={{
                aspectRatio: aspectMode === "9:16" ? "9/16" : "16/9",
                maxHeight: "360px",
              }}
              className="relative h-full rounded-lg border border-nle-border shadow-2xl overflow-hidden bg-black flex items-center justify-center"
            >
              <canvas
                ref={programCanvasRef}
                width={aspectMode === "9:16" ? 360 : 640}
                height={aspectMode === "9:16" ? 640 : 360}
                className="w-full h-full object-cover"
              />

              {/* TikTok / Shorts Safe Margins Overlay */}
              {safeZoneEnabled && (
                <div className="absolute inset-0 pointer-events-none border border-nle-cyan/30 flex flex-col justify-between p-3">
                  <div className="border-b border-dashed border-nle-cyan/40 pb-1 text-[9px] text-nle-cyan/80 text-center font-mono">
                    Top Margin: Avatar & Tab Zone (15%)
                  </div>
                  <div className="flex justify-between items-center text-[8px] text-nle-cyan/60 px-1 font-mono">
                    <span>Title Safe 80%</span>
                    <span className="border-r border-dashed border-nle-cyan/40 pr-1">Action Buttons (Right 15%)</span>
                  </div>
                  <div className="border-t border-dashed border-nle-cyan/40 pt-1 text-[9px] text-nle-cyan/80 text-center font-mono">
                    Bottom Margin: Caption & Sound Bar (22%)
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Source Monitor View */}
          {activeMonitorTab === "source" && (
            <div className="w-full max-w-xl aspect-video rounded-lg border border-nle-border shadow-2xl overflow-hidden bg-black flex flex-col">
              <canvas ref={sourceCanvasRef} width={640} height={360} className="w-full flex-1 object-cover" />
              <div className="h-8 bg-nle-panel px-3 flex items-center justify-between text-[11px] text-gray-300 border-t border-nle-border">
                <div className="flex space-x-2">
                  <button className="px-1.5 py-0.5 rounded bg-nle-surface border border-nle-border text-nle-cyan hover:bg-nle-cyan/10">
                    Mark In [ {`{`} ]
                  </button>
                  <button className="px-1.5 py-0.5 rounded bg-nle-surface border border-nle-border text-nle-cyan hover:bg-nle-cyan/10">
                    Mark Out [ {`}`} ]
                  </button>
                </div>
                <Button size="sm" variant="neon" className="h-5 px-2 text-[10px]">
                  + Chèn vào Timeline
                </Button>
              </div>
            </div>
          )}

          {/* Lumetri Scopes RGB Parade View */}
          {activeMonitorTab === "scopes" && (
            <div className="w-full max-w-xl aspect-video rounded-lg border border-nle-border shadow-2xl overflow-hidden bg-black flex flex-col">
              <div className="h-8 bg-nle-panel px-3 flex items-center justify-between text-[11px] text-gray-300 border-b border-nle-border">
                <span className="font-bold text-white flex items-center">
                  <Activity className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  RGB Parade Waveform (Rec.709)
                </span>
                <div className="flex items-center space-x-2 text-[10px]">
                  <label className="flex items-center space-x-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={clampSignal}
                      onChange={(e) => setClampSignal(e.target.checked)}
                      className="rounded border-nle-border text-nle-cyan w-3 h-3"
                    />
                    <span>Clamp Signal</span>
                  </label>
                  <span className="text-gray-400 font-mono">8 Bit (0-255)</span>
                </div>
              </div>
              <canvas ref={scopesCanvasRef} width={600} height={320} className="w-full flex-1 object-cover" />
            </div>
          )}
        </div>

        {/* 3. Live Stereo Master VU Meter (Adobe Premiere Pro Style) */}
        <div className="w-12 border-l border-nle-border bg-nle-panel p-2 flex flex-col items-center justify-between shrink-0 select-none z-20">
          <div className="text-[9px] font-mono text-gray-400 font-bold tracking-tighter">
            0dB
          </div>

          {/* Stereo Dual Meters */}
          <div className="flex-1 w-full flex justify-center space-x-1 py-1">
            {/* Left Channel */}
            <div className="w-2.5 h-full bg-nle-base rounded-xs flex flex-col justify-end overflow-hidden p-0.5">
              <div
                style={{ height: `${vuLeft * 100}%` }}
                className={`w-full rounded-xs transition-all duration-75 ${
                  vuLeft > 0.85
                    ? "bg-rose-500 shadow-xs shadow-rose-500"
                    : vuLeft > 0.65
                    ? "bg-amber-400"
                    : "bg-emerald-400"
                }`}
              />
            </div>

            {/* Right Channel */}
            <div className="w-2.5 h-full bg-nle-base rounded-xs flex flex-col justify-end overflow-hidden p-0.5">
              <div
                style={{ height: `${vuRight * 100}%` }}
                className={`w-full rounded-xs transition-all duration-75 ${
                  vuRight > 0.85
                    ? "bg-rose-500 shadow-xs shadow-rose-500"
                    : vuRight > 0.65
                    ? "bg-amber-400"
                    : "bg-emerald-400"
                }`}
              />
            </div>
          </div>

          {/* dB Scale indicators */}
          <div className="text-[8px] font-mono text-gray-500 flex flex-col items-center space-y-0.5">
            <span>-12</span>
            <span>-24</span>
            <span>-inf</span>
          </div>

          <div className="flex justify-between w-full pt-1 border-t border-nle-border text-[9px] font-mono text-gray-400 text-center">
            <span>L</span>
            <span>R</span>
          </div>
        </div>
      </div>

      {/* Playback Controls Footer Bar */}
      <div className="h-10 px-3 bg-nle-panel border-t border-nle-border flex items-center justify-between text-xs">
        {/* Playback Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setCurrentTime(0)}
            className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-nle-surface transition-colors"
            title="Trở về đầu timeline (Home)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={togglePlay}
            className="w-7 h-7 rounded-md bg-nle-cyan text-black font-bold flex items-center justify-center hover:bg-nle-cyan/90 transition-transform active:scale-95 shadow-md shadow-nle-cyan/20"
            title={isPlaying ? "Tạm dừng (Space)" : "Phát video (Space)"}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={() => {
              const canvas = programCanvasRef.current;
              if (canvas) {
                const link = document.createElement("a");
                link.download = `frame_capture_${Math.floor(currentTime)}.png`;
                link.href = canvas.toDataURL();
                link.click();
              }
            }}
            className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-nle-surface transition-colors"
            title="Chụp Frame làm Thumbnail (Export Frame)"
          >
            <Camera className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Resolution Scale Selector (Full, 1/2, Fit) */}
        <div className="flex items-center space-x-1 text-[11px] text-gray-400">
          <span>Xem trước:</span>
          {(["Fit", "1/2", "Full"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setResolutionScale(r)}
              className={`px-1.5 py-0.5 rounded text-[10px] ${
                resolutionScale === r
                  ? "bg-nle-surface text-white font-bold border border-nle-border"
                  : "hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Master Volume */}
        <div className="flex items-center space-x-2 w-28">
          <button
            onClick={toggleMute}
            className="text-gray-400 hover:text-white transition-colors"
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-3.5 h-3.5 text-rose-400" />
            ) : (
              <Volume2 className="w-3.5 h-3.5" />
            )}
          </button>
          <Slider
            value={[isMuted ? 0 : volume * 100]}
            max={100}
            step={1}
            onValueChange={([val]) => setVolume(val / 100)}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
}
