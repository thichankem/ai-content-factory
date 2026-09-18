"use client";

import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { usePlayerStore } from "../../stores/usePlayerStore";
import { useTimelineStore } from "../../stores/useTimelineStore";
import { formatTimecode } from "../../lib/utils";
import { Slider } from "../ui/slider";
import { Play, Pause, RotateCcw, Volume2, VolumeX, Shield, Maximize2 } from "lucide-react";

export function VideoPlayer() {
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Playback timer & VU meter simulation loop
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
        const l = Math.min(1, Math.max(0.1, 0.4 + Math.random() * 0.5));
        const r = Math.min(1, Math.max(0.1, 0.38 + Math.random() * 0.5));
        setVU(l, r);
      } else {
        setVU(0.05, 0.05);
      }

      // Draw active scene preview on canvas
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#090a0f";
          ctx.fillRect(0, 0, canvas.width, canvas.height);

          // Render gradient background
          const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
          grad.addColorStop(0, "#12151f");
          grad.addColorStop(1, "#181d2a");
          ctx.fillStyle = grad;
          ctx.fillRect(0, 0, canvas.width, canvas.height);

          // Render current scene text
          const currentScene = scenes[selectedSceneIndex ?? 0];
          if (currentScene) {
            ctx.fillStyle = "#00f0ff";
            ctx.font = "bold 18px Inter, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(currentScene.label || `Scene ${(selectedSceneIndex ?? 0) + 1}`, canvas.width / 2, canvas.height / 2 - 20);

            ctx.fillStyle = "#ffffff";
            ctx.font = "14px Inter, sans-serif";
            const text = currentScene.text || "Preview Frame Active";
            ctx.fillText(text.length > 30 ? text.slice(0, 30) + "..." : text, canvas.width / 2, canvas.height / 2 + 15);
          } else {
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Inter, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("Ready for playback", canvas.width / 2, canvas.height / 2);
          }
        }
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, currentTime, duration, loop, scenes, selectedSceneIndex, setCurrentTime, setVU]);

  return (
    <div className="flex flex-col h-full bg-nle-surface border border-nle-border rounded-lg overflow-hidden">
      {/* Player Header Bar */}
      <div className="h-9 px-3 bg-nle-panel border-b border-nle-border flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-white">Program Preview</span>
          <span className="text-[10px] bg-nle-border px-1.5 py-0.2 rounded text-gray-400">9:16 Vertical</span>
        </div>
        <div className="flex items-center space-x-3">
          {/* SMPTE Timecode */}
          <span className="font-mono text-xs font-bold text-nle-cyan tracking-wider bg-black/40 px-2 py-0.5 rounded border border-nle-cyan/30">
            {formatTimecode(currentTime)}
          </span>
          <button
            onClick={toggleSafeZone}
            className={`p-1 rounded transition-colors ${
              safeZoneEnabled ? "text-nle-cyan bg-nle-cyan/20" : "text-gray-400 hover:text-white"
            }`}
            title="Toggle TikTok / Shorts Safe Zones"
          >
            <Shield className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Screen Canvas & Safe Zone */}
      <div className="relative flex-1 flex items-center justify-center p-3 bg-nle-base overflow-hidden">
        <div className="relative aspect-[9/16] h-full max-h-[420px] rounded-lg border border-nle-border shadow-2xl overflow-hidden">
          <canvas
            ref={canvasRef}
            width={360}
            height={640}
            className="w-full h-full object-cover"
          />

          {/* TikTok / Reels Safe Zones Overlay */}
          {safeZoneEnabled && (
            <div className="absolute inset-0 pointer-events-none border border-nle-cyan/30 flex flex-col justify-between p-3">
              <div className="border-b border-dashed border-nle-cyan/40 pb-1 text-[10px] text-nle-cyan/80 text-center">
                Top Safe Zone (Avatar & Following)
              </div>
              <div className="flex justify-between items-center text-[9px] text-nle-cyan/60 px-1">
                <span>Left 40px</span>
                <span className="border-r border-dashed border-nle-cyan/40 pr-1">Action Buttons Right</span>
              </div>
              <div className="border-t border-dashed border-nle-cyan/40 pt-1 text-[10px] text-nle-cyan/80 text-center">
                Bottom Safe Zone (Captions & Audio Name)
              </div>
            </div>
          )}
        </div>

        {/* Dual Stereo Master VU Meters */}
        <div className="absolute right-4 top-1/2 -translate-y-1/2 flex space-x-1 bg-black/60 p-1.5 rounded border border-nle-border h-48">
          {/* L Channel */}
          <div className="w-2 bg-nle-panel rounded-full overflow-hidden flex flex-col justify-end">
            <motion.div
              className="w-full bg-gradient-to-t from-nle-emerald via-nle-amber to-nle-rose"
              animate={{ height: `${vuLeft * 100}%` }}
              transition={{ duration: 0.05 }}
            />
          </div>
          {/* R Channel */}
          <div className="w-2 bg-nle-panel rounded-full overflow-hidden flex flex-col justify-end">
            <motion.div
              className="w-full bg-gradient-to-t from-nle-emerald via-nle-amber to-nle-rose"
              animate={{ height: `${vuRight * 100}%` }}
              transition={{ duration: 0.05 }}
            />
          </div>
        </div>
      </div>

      {/* Transport Controls Bar */}
      <div className="p-2 bg-nle-panel border-t border-nle-border flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={togglePlay}
            className="w-8 h-8 rounded-full bg-gradient-to-r from-nle-cyan to-nle-violet text-black flex items-center justify-center font-bold hover:brightness-110 transition-all shadow-md shadow-nle-cyan/20"
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
          </button>
          <button
            onClick={() => setCurrentTime(0)}
            className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-nle-surface transition-colors"
            title="Reset to 00:00"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={toggleLoop}
            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
              loop ? "bg-nle-cyan/20 text-nle-cyan border border-nle-cyan/40" : "text-gray-400 hover:text-white"
            }`}
          >
            Loop
          </button>
        </div>

        {/* Scrubber slider */}
        <div className="flex-1 mx-4">
          <Slider
            value={[currentTime]}
            max={duration || 45}
            step={0.1}
            onValueChange={([val]) => setCurrentTime(val)}
          />
        </div>

        {/* Volume controls */}
        <div className="flex items-center space-x-2 w-28">
          <button
            onClick={toggleMute}
            className="text-gray-400 hover:text-white"
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
          />
        </div>
      </div>
    </div>
  );
}
