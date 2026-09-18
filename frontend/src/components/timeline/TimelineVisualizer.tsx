"use client";

import React from "react";
import { useTimelineStore } from "../../stores/useTimelineStore";
import { usePlayerStore } from "../../stores/usePlayerStore";
import { Slider } from "../ui/slider";
import { ZoomIn, ZoomOut, Scissors, Magnet, Layers } from "lucide-react";

export function TimelineVisualizer() {
  const { tracks, scenes, selectedSceneIndex, setSelectedSceneIndex, zoom, setZoom } =
    useTimelineStore();
  const { currentTime, duration, setCurrentTime } = usePlayerStore();

  const totalDuration = duration || 45;
  const pixelsPerSecond = 16 * zoom;
  const playheadLeft = currentTime * pixelsPerSecond;

  const defaultScenes = scenes.length > 0 ? scenes : [
    { index: 0, label: "Scene 1 • Hook", duration: 4.5, text: "Hook mở đầu", filter: "vibrant" },
    { index: 1, label: "Scene 2 • Evidence", duration: 18.0, text: "Bằng chứng chính", filter: "cinema" },
    { index: 2, label: "Scene 3 • Turn", duration: 12.5, text: "Bước ngoặt", filter: "warm" },
    { index: 3, label: "Scene 4 • Payoff & CTA", duration: 10.0, text: "Kêu gọi hành động", filter: "none" },
  ];

  return (
    <div className="flex flex-col h-full bg-nle-surface border border-nle-border rounded-lg overflow-hidden">
      {/* Timeline Controls Header */}
      <div className="h-9 px-3 bg-nle-panel border-b border-nle-border flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-white flex items-center">
            <Layers className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
            NLE Multi-Track Timeline
          </span>
          <span className="text-[10px] text-gray-400">
            ({defaultScenes.length} clips • {totalDuration.toFixed(1)}s)
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-gray-400">
            <ZoomOut className="w-3 h-3" />
            <div className="w-20">
              <Slider
                value={[zoom]}
                min={0.5}
                max={3}
                step={0.1}
                onValueChange={([val]) => setZoom(val)}
              />
            </div>
            <ZoomIn className="w-3 h-3" />
          </div>

          <div className="h-3 w-[1px] bg-nle-border" />

          <button className="p-1 rounded text-gray-400 hover:text-white" title="Split at playhead">
            <Scissors className="w-3.5 h-3.5" />
          </button>
          <button className="p-1 rounded text-nle-cyan bg-nle-cyan/10" title="Snap to clips">
            <Magnet className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tracks Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Track Headers (Left sidebar) */}
        <div className="w-44 border-r border-nle-border bg-nle-panel flex flex-col shrink-0">
          {tracks.map((track) => (
            <div
              key={track.id}
              className="h-14 border-b border-nle-border px-3 flex items-center justify-between text-xs font-medium"
            >
              <div className="flex items-center space-x-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: track.color }}
                />
                <span className="text-gray-200">{track.name}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Track Lanes & Ruler (Scrollable right area) */}
        <div
          className="flex-1 relative overflow-x-auto overflow-y-hidden bg-nle-base"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const clickX = e.clientX - rect.left + e.currentTarget.scrollLeft;
            const newTime = Math.max(0, Math.min(totalDuration, clickX / pixelsPerSecond));
            setCurrentTime(newTime);
          }}
        >
          {/* Playhead Vertical Line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-nle-cyan z-30 pointer-events-none"
            style={{ left: `${playheadLeft}px` }}
          >
            <div className="w-3 h-3 bg-nle-cyan transform -translate-x-[5px] rotate-45 rounded-xs shadow-md" />
          </div>

          {/* Lanes */}
          <div style={{ width: `${totalDuration * pixelsPerSecond + 100}px` }}>
            {/* Lane V1 (Video Clips) */}
            <div className="h-14 border-b border-nle-border relative flex items-center px-1">
              {defaultScenes.map((scene, idx) => {
                const width = scene.duration * pixelsPerSecond;
                const isSelected = selectedSceneIndex === idx;

                return (
                  <div
                    key={idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedSceneIndex(idx);
                    }}
                    style={{ width: `${width}px` }}
                    className={`h-11 rounded-md border mr-1 p-2 flex flex-col justify-between cursor-pointer transition-all ${
                      isSelected
                        ? "border-nle-cyan bg-nle-cyan/20 shadow-lg shadow-nle-cyan/10"
                        : "border-nle-border bg-nle-surface hover:border-gray-500"
                    }`}
                  >
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="font-semibold text-white truncate">{scene.label}</span>
                      <span className="text-gray-400">{scene.duration.toFixed(1)}s</span>
                    </div>
                    <div className="text-[9px] text-nle-cyan/80 truncate">
                      {scene.filter ? `FX: ${scene.filter}` : "Normal"}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Lane V2 (B-Roll) */}
            <div className="h-14 border-b border-nle-border relative flex items-center px-1">
              <div
                style={{ width: `${14 * pixelsPerSecond}px`, left: `${6 * pixelsPerSecond}px` }}
                className="absolute h-9 rounded bg-nle-violet/20 border border-nle-violet/40 p-1.5 flex items-center justify-between text-[10px] text-nle-violet font-medium"
              >
                <span>Overlay B-Roll 01</span>
                <span>14.0s</span>
              </div>
            </div>

            {/* Lane A1 (Voiceover) */}
            <div className="h-14 border-b border-nle-border relative flex items-center px-1">
              <div
                style={{ width: `${(totalDuration - 2) * pixelsPerSecond}px` }}
                className="h-9 rounded bg-nle-emerald/20 border border-nle-emerald/40 p-1.5 flex items-center justify-between text-[10px] text-nle-emerald font-medium"
              >
                <span>Piper TTS Narration Track</span>
                <span>{(totalDuration - 2).toFixed(1)}s</span>
              </div>
            </div>

            {/* Lane A2 (BGM) */}
            <div className="h-14 border-b border-nle-border relative flex items-center px-1">
              <div
                style={{ width: `${totalDuration * pixelsPerSecond}px` }}
                className="h-9 rounded bg-nle-amber/20 border border-nle-amber/40 p-1.5 flex items-center justify-between text-[10px] text-nle-amber font-medium"
              >
                <span>Lo-Fi Chill Background Beat (Sidechain Ducked)</span>
                <span>{totalDuration.toFixed(1)}s</span>
              </div>
            </div>

            {/* Lane C1 (Captions) */}
            <div className="h-14 border-b border-nle-border relative flex items-center px-1">
              <div
                style={{ width: `${(totalDuration - 1) * pixelsPerSecond}px` }}
                className="h-9 rounded bg-pink-500/20 border border-pink-500/40 p-1.5 flex items-center justify-between text-[10px] text-pink-400 font-medium"
              >
                <span>Accessible Simplified Subtitles (Auto-Synced)</span>
                <span>{(totalDuration - 1).toFixed(1)}s</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
