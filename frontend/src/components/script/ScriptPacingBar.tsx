"use client";

import React from "react";
import { SpeechPacingConfig, TargetScope } from "@/types/studio";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Gauge,
  Sparkles,
  Layers,
  ChevronDown,
  Volume2,
  Sliders,
  Target,
} from "lucide-react";

interface ScriptPacingBarProps {
  scriptText: string;
  targetDurationStr: string; // e.g. "15s", "60s", "3m", "10m"
  targetScope: TargetScope;
  pacingConfig: SpeechPacingConfig;
  onPacingChange: (cfg: SpeechPacingConfig) => void;
}

export const PACING_PRESETS: Array<{
  preset: "slow" | "normal" | "fast" | "hyper";
  label: string;
  wpm: number;
  description: string;
}> = [
  {
    preset: "slow",
    label: "Chậm (130 WPM)",
    wpm: 130,
    description: "Kể chuyện, tài liệu trầm ấm (~2.1 từ/s)",
  },
  {
    preset: "normal",
    label: "Chuẩn (160 WPM)",
    wpm: 160,
    description: "Thuyết minh tự nhiên, chuẩn TTS Edge/Google (~2.7 từ/s)",
  },
  {
    preset: "fast",
    label: "Nhanh (195 WPM)",
    wpm: 195,
    description: "TikTok / Shorts giữ nhịp sôi động (~3.2 từ/s)",
  },
  {
    preset: "hyper",
    label: "Cực nhanh (230 WPM)",
    wpm: 230,
    description: "Rap hook, bán hàng dồn dập (~3.8 từ/s)",
  },
];

export function parseTargetSeconds(str: string): number {
  const s = (str || "").toLowerCase().trim();
  if (s.endsWith("m") || s.includes("phút") || s.includes("min")) {
    const num = parseFloat(s.replace(/[^0-9.]/g, "")) || 1;
    return num * 60;
  }
  const num = parseFloat(s.replace(/[^0-9.]/g, "")) || 60;
  return num;
}

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m > 0 ? `${m}m ` : ""}${s}s`;
}

export function ScriptPacingBar({
  scriptText,
  targetDurationStr,
  targetScope,
  pacingConfig,
  onPacingChange,
}: ScriptPacingBarProps) {
  // Strip markers like [Hook // 00:00] or (Visual Cue: ...) before counting words
  const cleanScript = scriptText
    .replace(/\[.*?\]/g, " ")
    .replace(/\(.*?\)/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const totalWords = cleanScript ? cleanScript.split(/\s+/).filter(Boolean).length : 0;
  const wordsPerSecond = pacingConfig.wpm / 60;
  const estimatedTotalSeconds = totalWords > 0 ? totalWords / wordsPerSecond : 0;

  const targetSeconds = parseTargetSeconds(targetDurationStr);
  const diffSeconds = estimatedTotalSeconds - targetSeconds;
  const percentOfTarget = targetSeconds > 0 ? Math.min(150, (estimatedTotalSeconds / targetSeconds) * 100) : 100;

  // Selected scope words and timing
  const cleanSelected = targetScope.selectedText
    .replace(/\[.*?\]/g, " ")
    .replace(/\(.*?\)/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const selectedWords = cleanSelected ? cleanSelected.split(/\s+/).filter(Boolean).length : 0;
  const selectedSeconds = selectedWords > 0 ? selectedWords / wordsPerSecond : 0;

  // Status rating
  let pacingStatusBadge: React.ReactNode = null;
  if (Math.abs(diffSeconds) <= 5) {
    pacingStatusBadge = (
      <Badge variant="cyan" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
        ✓ Chuẩn nhịp (Vừa vặn ±5s)
      </Badge>
    );
  } else if (diffSeconds > 5) {
    pacingStatusBadge = (
      <Badge variant="outline" className="text-[10px] bg-rose-500/15 text-rose-400 border-rose-500/40 font-mono">
        ⚠ Dài hơn mục tiêu (+{formatTime(diffSeconds)})
      </Badge>
    );
  } else {
    pacingStatusBadge = (
      <Badge variant="outline" className="text-[10px] bg-amber-500/15 text-amber-300 border-amber-500/40 font-mono">
        ℹ Ngắn hơn mục tiêu (-{formatTime(Math.abs(diffSeconds))})
      </Badge>
    );
  }

  const handleCustomWpm = (newWpm: number) => {
    const clamped = Math.max(60, Math.min(350, newWpm));
    const matchingPreset = PACING_PRESETS.find((p) => p.wpm === clamped);
    if (matchingPreset) {
      onPacingChange({
        wpm: clamped,
        label: matchingPreset.label,
        preset: matchingPreset.preset,
      });
    } else {
      onPacingChange({
        wpm: clamped,
        label: `Tùy chỉnh (${clamped} WPM)`,
        preset: "custom",
      });
    }
  };

  return (
    <div className="bg-nle-panel border border-nle-border rounded-xl p-2.5 px-3 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0 shadow-md">
      {/* Left: Duration prediction & target comparison */}
      <div className="flex items-center space-x-3 min-w-0">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-nle-cyan/20 border border-nle-cyan/40 flex items-center justify-center text-nle-cyan">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-[11px] font-semibold text-gray-400">Dự đoán thời lượng:</span>
              <span className="text-sm font-black font-mono text-white">
                {formatTime(estimatedTotalSeconds)}
              </span>
              <span className="text-gray-500 text-[11px]">/ Mục tiêu {targetDurationStr}</span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] text-gray-400">
              <span>{totalWords} từ</span>
              <span>•</span>
              <span>~{Math.round(totalWords * 1.05)} âm tiết</span>
              <span>•</span>
              {pacingStatusBadge}
            </div>
          </div>
        </div>

        {/* Selected Range Timing Badge (if range is active) */}
        {targetScope.type !== "full" && selectedWords > 0 && (
          <div className="hidden sm:flex items-center space-x-1.5 bg-nle-surface/90 border border-nle-cyan/30 px-2.5 py-1 rounded-lg">
            <Target className="w-3.5 h-3.5 text-nle-cyan shrink-0 animate-pulse" />
            <div className="text-[11px]">
              <span className="text-nle-cyan font-semibold">
                Dòng {targetScope.startLine}-{targetScope.endLine}:
              </span>{" "}
              <span className="font-mono text-white font-bold">{selectedWords} từ</span> (~{formatTime(selectedSeconds)})
            </div>
          </div>
        )}
      </div>

      {/* Right: Speech Rate Selector & Custom Adjustable Slider / Stepper */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Presets buttons */}
        <div className="flex items-center space-x-1 bg-nle-surface p-0.5 rounded-lg border border-nle-border">
          <span className="text-[10px] text-gray-400 px-1.5 flex items-center font-mono">
            <Gauge className="w-3 h-3 mr-1 text-nle-violet" />
            Tốc độ:
          </span>
          {PACING_PRESETS.map((p) => (
            <button
              key={p.preset}
              onClick={() => onPacingChange({ wpm: p.wpm, label: p.label, preset: p.preset })}
              title={p.description}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                pacingConfig.preset === p.preset && pacingConfig.wpm === p.wpm
                  ? "bg-nle-cyan text-black font-bold shadow-sm"
                  : "text-gray-300 hover:text-white hover:bg-nle-panel"
              }`}
            >
              {p.label.split(" ")[0]} ({p.wpm})
            </button>
          ))}
          {pacingConfig.preset === "custom" && (
            <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 rounded text-[10px] font-bold font-mono">
              Tùy biến ({pacingConfig.wpm})
            </span>
          )}
        </div>

        {/* Custom Fine-Tuning Slider + Stepper */}
        <div className="flex items-center space-x-1.5 bg-nle-surface/90 px-2 py-1 rounded-lg border border-nle-border">
          <Sliders className="w-3.5 h-3.5 text-nle-cyan shrink-0" />
          <input
            type="range"
            min="80"
            max="300"
            step="5"
            value={pacingConfig.wpm}
            onChange={(e) => handleCustomWpm(Number(e.target.value))}
            className="w-16 sm:w-20 lg:w-24 h-1.5 bg-nle-panel rounded-lg appearance-none cursor-pointer accent-cyan-400"
            title={`Kéo để điều chỉnh tốc độ đọc (${pacingConfig.wpm} WPM)`}
          />
          <div className="flex items-center space-x-0.5 bg-nle-panel rounded border border-nle-border px-1">
            <button
              type="button"
              onClick={() => handleCustomWpm(pacingConfig.wpm - 5)}
              className="text-gray-400 hover:text-white font-bold px-1 text-xs select-none hover:bg-nle-surface rounded"
              title="Giảm 5 từ/phút"
            >
              -
            </button>
            <input
              type="number"
              min="60"
              max="350"
              value={pacingConfig.wpm}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                if (!isNaN(val)) handleCustomWpm(val);
              }}
              className="w-10 bg-transparent text-center font-mono font-bold text-white text-xs focus:outline-none focus:ring-1 focus:ring-nle-cyan rounded"
              title="Nhập số từ/phút chính xác"
            />
            <button
              type="button"
              onClick={() => handleCustomWpm(pacingConfig.wpm + 5)}
              className="text-gray-400 hover:text-white font-bold px-1 text-xs select-none hover:bg-nle-surface rounded"
              title="Tăng 5 từ/phút"
            >
              +
            </button>
          </div>
          <span className="text-[10px] text-gray-400 font-mono">WPM</span>
          <span
            className="hidden xl:inline text-[9px] text-nle-cyan/90 font-mono bg-nle-cyan/10 px-1 py-0.5 rounded border border-nle-cyan/20"
            title={`Tương đương ${(pacingConfig.wpm / 60).toFixed(1)} từ/giây (${(pacingConfig.wpm / 160).toFixed(2)}x so với tốc độ chuẩn)`}
          >
            {(pacingConfig.wpm / 160).toFixed(2)}x
          </span>
        </div>

        {/* Mini progress bar of target time */}
        <div className="hidden lg:flex flex-col w-20">
          <div className="flex justify-between text-[9px] font-mono text-gray-400 mb-0.5">
            <span>Tiến độ</span>
            <span>{Math.round(percentOfTarget)}%</span>
          </div>
          <div className="w-full bg-nle-surface rounded-full h-1.5 overflow-hidden border border-nle-border">
            <div
              className={`h-full transition-all duration-300 rounded-full ${
                percentOfTarget > 115
                  ? "bg-rose-500"
                  : percentOfTarget > 90
                  ? "bg-emerald-400"
                  : "bg-nle-cyan"
              }`}
              style={{ width: `${Math.min(100, percentOfTarget)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
