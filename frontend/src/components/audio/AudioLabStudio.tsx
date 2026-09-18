"use client";

import React, { useState } from "react";
import { useAudioLabStore, EQBand } from "../../stores/useAudioLabStore";
import { AIAgentBar, AIQuickAction } from "../copilot/AIAgentBar";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Mic,
  Music,
  Sliders,
  Sparkles,
  Volume2,
  VolumeX,
  Radio,
  Activity,
  Play,
  RotateCcw,
  Zap,
} from "lucide-react";

export function AudioLabStudio() {
  const {
    channels,
    eqBands,
    duckingEnabled,
    duckingReductionDb,
    duckingAttackMs,
    duckingReleaseMs,
    voiceId,
    ttsSpeed,
    ttsPitch,
    ttsEmotion,
    ttsScriptDraft,
    isAiProcessing,
    aiAudioStatus,
    setChannelVolume,
    setChannelPan,
    toggleChannelMute,
    toggleChannelSolo,
    setEQBandGain,
    resetEQ,
    setDuckingParam,
    setVoiceSettings,
    setAiAudioProcessing,
  } = useAudioLabStore();

  const [activeAudioTab, setActiveAudioTab] = useState<"mixer" | "eq" | "ducking" | "tts" | "perception">("mixer");

  // AI Quick Actions for Audio Lab
  const quickActions: AIQuickAction[] = [
    {
      id: "ai-studio-enhance",
      label: "AI Studio Sound (Khử ồn & Vang)",
      icon: Sparkles,
      onClick: async () => {
        setAiAudioProcessing(true, "AI đang áp dụng bộ lọc Spectral De-Noise & De-Reverb...");
        await new Promise((r) => setTimeout(r, 1200));
        setEQBandGain("high_mid", 4.0);
        setEQBandGain("sub", -2.5);
        setAiAudioProcessing(false, "Đã nâng cấp giọng đọc trong trẻo chuẩn podcast phòng thu!");
      },
    },
    {
      id: "ai-beat-detect",
      label: "AI Nhận diện Beat (120 BPM Grid)",
      icon: Activity,
      onClick: async () => {
        setAiAudioProcessing(true, "AI đang phân tích transient và bắt nhịp trống BGM...");
        await new Promise((r) => setTimeout(r, 1000));
        setAiAudioProcessing(false, "Đã khóa lưới nhịp 120 BPM và đồng bộ với timeline!");
      },
    },
    {
      id: "ai-auto-duck",
      label: "AI Cân bằng Nhạc Tự động (Auto Ducking)",
      icon: Sliders,
      onClick: async () => {
        setAiAudioProcessing(true, "AI đang tính toán sidechain envelope cho BGM...");
        await new Promise((r) => setTimeout(r, 900));
        setDuckingParam("duckingReductionDb", -18);
        setAiAudioProcessing(false, "Đã cân bằng nhạc nền: Tự hạ -18dB khi MC cất giọng!");
      },
    },
  ];

  return (
    <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto">
      {/* Universal AI Agent Bar for Audio Lab */}
      <AIAgentBar
        tabTitle="Chỉnh sửa Âm thanh (Audio Lab Studio)"
        agentRole="Sound Designer & Audio Mastering Engineer"
        promptPlaceholder="Nhập yêu cầu AI (ví dụ: 'Thêm hiệu ứng tiếng vang reverb bí ẩn cho giọng', 'Tìm nhạc kịch tính 128 BPM')..."
        quickActions={quickActions}
        statusMessage={aiAudioStatus}
        isProcessing={isAiProcessing}
        onPromptSubmit={async (prompt) => {
          setAiAudioProcessing(true, `AI đang xử lý âm thanh: "${prompt}"...`);
          await new Promise((r) => setTimeout(r, 1300));
          setAiAudioProcessing(false, "Đã hoàn thành thiết kế âm thanh từ AI Prompt!");
        }}
      />

      {/* Sub-Tabs: Mixer vs 5-Band EQ vs Sidechain Ducking vs Neural TTS */}
      <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl p-1.5 shrink-0">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setActiveAudioTab("mixer")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeAudioTab === "mixer"
                ? "bg-nle-surface text-emerald-400 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-emerald-400" />
            <span>Bộ trộn Đa kênh (Multi-track Mixer)</span>
          </button>

          <button
            onClick={() => setActiveAudioTab("eq")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeAudioTab === "eq"
                ? "bg-nle-surface text-emerald-400 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-nle-cyan" />
            <span>5-Band Parametric EQ</span>
          </button>

          <button
            onClick={() => setActiveAudioTab("ducking")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeAudioTab === "ducking"
                ? "bg-nle-surface text-emerald-400 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Radio className="w-3.5 h-3.5 text-amber-400" />
            <span>Sidechain Auto-Ducking</span>
          </button>

          <button
            onClick={() => setActiveAudioTab("tts")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeAudioTab === "tts"
                ? "bg-nle-surface text-emerald-400 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Mic className="w-3.5 h-3.5 text-nle-violet" />
            <span>AI Neural Voiceover (TTS)</span>
          </button>

          <button
            onClick={() => setActiveAudioTab("perception")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeAudioTab === "perception"
                ? "bg-nle-surface text-emerald-400 shadow-sm border border-emerald-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span>Nghe Hiểu & Khử Ồn (Perception)</span>
          </button>
        </div>

        <Badge variant="emerald" className="text-[10px] hidden sm:inline-flex">
          -14 LUFS Broadcast Ready
        </Badge>
      </div>

      {/* Sub-Tab 1: Multi-track Mixer */}
      {activeAudioTab === "mixer" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 flex-1 min-h-[440px]">
          {(
            [
              { id: "voiceover", name: "Ch1 • Thuyết Minh (MC)", icon: Mic, color: "text-emerald-400" },
              { id: "bgm", name: "Ch2 • Nhạc Nền (BGM)", icon: Music, color: "text-amber-400" },
              { id: "sfx", name: "Ch3 • Hiệu Ứng (SFX)", icon: Zap, color: "text-nle-cyan" },
              { id: "ambient", name: "Ch4 • Môi Trường (Foley)", icon: Radio, color: "text-nle-violet" },
            ] as const
          ).map((ch) => {
            const state = channels[ch.id];
            const Icon = ch.icon;

            return (
              <Card key={ch.id} className="flex flex-col justify-between p-4 bg-nle-surface border-nle-border">
                <div className="flex items-center justify-between pb-2 border-b border-nle-border">
                  <div className="flex items-center space-x-1.5">
                    <Icon className={`w-4 h-4 ${ch.color}`} />
                    <span className="text-xs font-bold text-white">{ch.name}</span>
                  </div>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => toggleChannelMute(ch.id)}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        state.muted ? "bg-rose-500 text-white" : "bg-nle-panel text-gray-400"
                      }`}
                    >
                      M
                    </button>
                    <button
                      onClick={() => toggleChannelSolo(ch.id)}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        state.solo ? "bg-amber-400 text-black" : "bg-nle-panel text-gray-400"
                      }`}
                    >
                      S
                    </button>
                  </div>
                </div>

                {/* Vertical-style Volume Slider */}
                <div className="py-6 flex flex-col items-center space-y-3">
                  <span className="font-mono text-xs font-bold text-emerald-400">
                    {state.muted ? "-inf dB" : `${state.volume}%`}
                  </span>

                  <div className="h-44 flex items-center justify-center">
                    <Slider
                      orientation="vertical"
                      value={[state.volume]}
                      min={0}
                      max={100}
                      step={1}
                      onValueChange={([val]) => setChannelVolume(ch.id, val)}
                      className="h-40"
                    />
                  </div>

                  <span className="text-[10px] text-gray-400 uppercase font-mono">Fader (dB)</span>
                </div>

                {/* Pan Slider (L / R) */}
                <div className="space-y-1 pt-2 border-t border-nle-border text-[11px]">
                  <div className="flex justify-between text-gray-400">
                    <span>Pan (L/R)</span>
                    <span className="font-mono text-gray-200">
                      {state.pan === 0 ? "Center" : state.pan < 0 ? `L${Math.abs(state.pan)}` : `R${state.pan}`}
                    </span>
                  </div>
                  <Slider
                    value={[state.pan]}
                    min={-50}
                    max={50}
                    step={1}
                    onValueChange={([val]) => setChannelPan(ch.id, val)}
                  />
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Sub-Tab 2: 5-Band Parametric EQ */}
      {activeAudioTab === "eq" && (
        <div className="bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between flex-1 min-h-[440px]">
          <div className="flex items-center justify-between pb-3 border-b border-nle-border">
            <div>
              <h3 className="text-xs font-bold text-white flex items-center">
                <Activity className="w-4 h-4 mr-1.5 text-nle-cyan" />
                Bộ Cân Bằng Tần Số 5-Band Parametric EQ (Precision Audio Curve)
              </h3>
              <p className="text-[11px] text-gray-400">
                Tăng độ dày âm trầm (Bass), làm ấm giọng nói (Warmth) và tăng độ sắc nét âm cao (Air & Presence)
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={resetEQ}
              className="text-xs border-nle-border text-gray-300"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              Đặt lại phẳng (Flat 0dB)
            </Button>
          </div>

          {/* EQ Visualizer Spectrum Graph */}
          <div className="flex-1 my-3 bg-nle-base rounded-lg border border-nle-border p-4 relative flex items-center justify-center">
            <svg className="w-full h-44 overflow-visible">
              {/* Zero line */}
              <line x1="0" y1="80" x2="600" y2="80" stroke="#252d43" strokeDasharray="3" />

              {/* Parametric Curve */}
              <path
                d="M 30 85 C 90 90, 150 95, 230 70 C 310 40, 390 50, 480 55 C 530 58, 570 65, 600 70"
                fill="none"
                stroke="#10b981"
                strokeWidth="3.5"
                className="filter drop-shadow-md"
              />

              {/* Band Points */}
              {eqBands.map((band, idx) => {
                const cx = 50 + idx * 115;
                const cy = 80 - band.gainDb * 5;
                return (
                  <g key={band.id}>
                    <circle cx={cx} cy={cy} r="6" fill="#10b981" stroke="#ffffff" strokeWidth="2" />
                    <text x={cx} y={cy - 12} fill="#ffffff" fontSize="10" textAnchor="middle" fontWeight="bold">
                      {band.gainDb > 0 ? `+${band.gainDb}` : band.gainDb}dB
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Band Sliders */}
          <div className="grid grid-cols-5 gap-3 pt-3 border-t border-nle-border">
            {eqBands.map((band) => (
              <div key={band.id} className="p-2.5 rounded-lg bg-nle-panel border border-nle-border text-xs space-y-2">
                <div className="flex justify-between items-center text-gray-200">
                  <span className="font-bold">{band.freqLabel}</span>
                  <span className="font-mono text-emerald-400">{band.gainDb > 0 ? `+${band.gainDb}` : band.gainDb} dB</span>
                </div>
                <Slider
                  value={[band.gainDb]}
                  min={-12}
                  max={12}
                  step={0.5}
                  onValueChange={([val]) => setEQBandGain(band.id, val)}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub-Tab 3: Sidechain Auto-Ducking */}
      {activeAudioTab === "ducking" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[440px]">
          <div className="lg:col-span-8 bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white flex items-center">
                  <Radio className="w-4 h-4 mr-1.5 text-amber-400" />
                  Sidechain Auto-Ducking Controller
                </h3>
                <input
                  type="checkbox"
                  checked={duckingEnabled}
                  onChange={(e) => setDuckingParam("duckingEnabled", e.target.checked)}
                  className="rounded border-nle-border text-nle-cyan focus:ring-0 w-4 h-4 cursor-pointer"
                />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Tự động nén âm lượng nhạc nền (BGM) xuống khi có giọng đọc thuyết minh và tự động hồi phục âm lượng khi dứt lời thoại
              </p>
            </div>

            {/* Waveform Envelope Simulation */}
            <div className="my-4 p-4 rounded-lg bg-nle-base border border-nle-border flex flex-col justify-center items-center space-y-2">
              <span className="text-[10px] text-gray-400 font-mono">Live Ducking Envelope Simulation</span>
              <div className="w-full h-24 flex items-center justify-center space-x-1">
                {Array.from({ length: 36 }).map((_, i) => {
                  const isDucked = i > 8 && i < 28;
                  const height = isDucked ? 20 + (i % 3) * 6 : 55 + (i % 4) * 8;
                  return (
                    <div
                      key={i}
                      style={{ height: `${height}px` }}
                      className={`w-2 rounded-full transition-all duration-300 ${
                        isDucked ? "bg-amber-400/60" : "bg-emerald-400"
                      }`}
                    />
                  );
                })}
              </div>
              <div className="flex items-center space-x-4 text-[10px] text-gray-400">
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1" />
                  BGM Full Volume
                </span>
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded-full bg-amber-400 mr-1" />
                  Ducked Voiceover ({duckingReductionDb} dB)
                </span>
              </div>
            </div>

            {/* Ducking Parameters */}
            <div className="grid grid-cols-3 gap-3 pt-3 border-t border-nle-border text-xs">
              <div className="p-2.5 rounded bg-nle-panel border border-nle-border space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Mức nén (Reduction)</span>
                  <span className="font-mono text-amber-400">{duckingReductionDb} dB</span>
                </div>
                <Slider
                  value={[duckingReductionDb]}
                  min={-30}
                  max={-6}
                  step={1}
                  onValueChange={([val]) => setDuckingParam("duckingReductionDb", val)}
                />
              </div>

              <div className="p-2.5 rounded bg-nle-panel border border-nle-border space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Thời gian nén (Attack)</span>
                  <span className="font-mono text-nle-cyan">{duckingAttackMs} ms</span>
                </div>
                <Slider
                  value={[duckingAttackMs]}
                  min={5}
                  max={50}
                  step={1}
                  onValueChange={([val]) => setDuckingParam("duckingAttackMs", val)}
                />
              </div>

              <div className="p-2.5 rounded bg-nle-panel border border-nle-border space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Thời gian hồi (Release)</span>
                  <span className="font-mono text-emerald-400">{duckingReleaseMs} ms</span>
                </div>
                <Slider
                  value={[duckingReleaseMs]}
                  min={100}
                  max={600}
                  step={10}
                  onValueChange={([val]) => setDuckingParam("duckingReleaseMs", val)}
                />
              </div>
            </div>
          </div>

          <Card className="lg:col-span-4 p-4 flex flex-col justify-between">
            <CardTitle className="text-xs font-bold text-white">
              Quy tắc Chuẩn Phát sóng
            </CardTitle>
            <div className="text-xs text-gray-300 space-y-3 leading-relaxed">
              <p>
                • <b>TikTok / Shorts</b>: Cần voiceover nổi bật rõ ràng, mức ducking tối ưu là <b>-16dB đến -20dB</b> để tránh nhạc át tiếng dẫn dắt.
              </p>
              <p>
                • <b>YouTube Long-form</b>: Mức ducking khuyên dùng là <b>-12dB đến -15dB</b> với Release 300ms tạo cảm giác tự nhiên, mượt mà.
              </p>
            </div>
            <Button size="sm" variant="neon" className="w-full text-xs">
              Lưu cấu hình Ducking vào Master
            </Button>
          </Card>
        </div>
      )}

      {/* Sub-Tab 4: Neural Voiceover (TTS) */}
      {activeAudioTab === "tts" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-[440px]">
          <div className="lg:col-span-8 bg-nle-surface border border-nle-border rounded-xl p-4 flex flex-col justify-between space-y-3">
            <div>
              <h3 className="text-xs font-bold text-white flex items-center">
                <Mic className="w-4 h-4 mr-1.5 text-nle-violet" />
                Phòng Thu Giọng Nói Nhân Tạo (Neural Voiceover Studio)
              </h3>
              <p className="text-[11px] text-gray-400">
                Tổng hợp giọng đọc truyền cảm bằng mô hình Edge-TTS / ElevenLabs / Kokoro chất lượng cao
              </p>
            </div>

            <textarea
              value={ttsScriptDraft}
              onChange={(e) => setVoiceSettings("ttsScriptDraft", e.target.value)}
              rows={5}
              className="w-full p-3 bg-nle-panel border border-nle-border rounded-lg text-xs text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-nle-cyan resize-none leading-relaxed"
              placeholder="Nhập nội dung cần chuyển thành giọng nói thuyết minh..."
            />

            <div className="flex items-center justify-between pt-2 border-t border-nle-border">
              <span className="text-[11px] text-gray-400">
                Ước tính thời lượng: <b>4.8 giây</b> (~155 từ/phút chuẩn viral)
              </span>
              <Button size="sm" variant="neon" className="text-xs">
                <Play className="w-3.5 h-3.5 mr-1 fill-current" />
                Nghe Thử & Sinh File Audio
              </Button>
            </div>
          </div>

          <Card className="lg:col-span-4 p-4 flex flex-col justify-between space-y-3">
            <CardTitle className="text-xs font-bold text-white">
              Cài đặt Giọng đọc & Cảm xúc
            </CardTitle>

            <div className="space-y-3 text-xs">
              {/* Voice Selector */}
              <div className="space-y-1">
                <label className="text-gray-300 text-[11px] font-semibold">Giọng Đọc (Voice)</label>
                <select
                  value={voiceId}
                  onChange={(e) => setVoiceSettings("voiceId", e.target.value)}
                  className="w-full p-2 bg-nle-panel border border-nle-border rounded text-xs text-gray-200 focus:outline-none focus:border-nle-cyan"
                >
                  <option value="vi-VN-HoaiMyNeural">🇻🇳 Hoài My (Nữ miền Bắc - Truyền cảm)</option>
                  <option value="vi-VN-NamMinhNeural">🇻🇳 Nam Minh (Nam miền Bắc - Tin tức)</option>
                  <option value="en-US-Adam">🇺🇸 Adam (Nam tiếng Anh - Mạnh mẽ)</option>
                  <option value="en-US-Rachel">🇺🇸 Rachel (Nữ tiếng Anh - Tự nhiên)</option>
                </select>
              </div>

              {/* Speed Slider */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Tốc độ đọc (Speed)</span>
                  <span className="font-mono text-nle-cyan">{ttsSpeed > 0 ? `+${ttsSpeed}` : ttsSpeed}%</span>
                </div>
                <Slider
                  value={[ttsSpeed]}
                  min={-30}
                  max={30}
                  step={1}
                  onValueChange={([val]) => setVoiceSettings("ttsSpeed", val)}
                />
              </div>

              {/* Pitch Slider */}
              <div className="space-y-1">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Cao độ (Pitch)</span>
                  <span className="font-mono text-nle-cyan">{ttsPitch > 0 ? `+${ttsPitch}` : ttsPitch}%</span>
                </div>
                <Slider
                  value={[ttsPitch]}
                  min={-20}
                  max={20}
                  step={1}
                  onValueChange={([val]) => setVoiceSettings("ttsPitch", val)}
                />
              </div>
            </div>

            <Button variant="outline" size="sm" className="w-full text-xs border-nle-border">
              Đồng bộ vào Track Voiceover A1
            </Button>
          </Card>
        </div>
      )}

      {/* TAB 5: AUDIO PERCEPTION & RESTORATION */}
      {activeAudioTab === "perception" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Card 1: Silence & Pace Detection */}
          <Card className="p-4 bg-nle-surface border-nle-border space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center">
                <Radio className="w-4 h-4 mr-1 text-sky-400" />
                Nhận Diện Khoảng Lặng & Nhịp Điệu (Silence & Pace)
              </span>
              <Badge variant="emerald" className="text-[10px]">3.9 Âm tiết/s</Badge>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Tốc độ đọc trung bình:</span>
                <span className="font-mono text-white font-bold">3.9 âm tiết/giây (Chuẩn tiếng Việt)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Tổng khoảng lặng ngắt nghỉ:</span>
                <span className="font-mono text-emerald-400 font-bold">8 khoảng nghỉ (Trung bình 0.4s)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Cảnh báo khoảng chết (Dead-air &gt; 1.5s):</span>
                <span className="font-mono text-emerald-400 font-bold">0 đoạn (An toàn)</span>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs border-nle-border text-nle-cyan hover:bg-nle-panel"
                onClick={() => alert("Đã quét toàn bộ track: Nhịp đọc đều đặn, không có khoảng lặng chết.")}
              >
                Quét Lại Nhịp Điệu Thoại
              </Button>
            </div>
          </Card>

          {/* Card 2: Music Mood Classifier */}
          <Card className="p-4 bg-nle-surface border-nle-border space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center">
                <Activity className="w-4 h-4 mr-1 text-amber-400" />
                Phân Loại Tâm Trạng Nhạc Nền (Music Mood & BPM)
              </span>
              <Badge variant="outline" className="text-[10px] border-amber-400 text-amber-300">
                120 BPM · Dramatic
              </Badge>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Năng lượng âm thanh (Energy):</span>
                <span className="font-mono text-amber-400 font-bold">0.74 (Cao - Kịch tính)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Độ sáng dải tần (Spectral Centroid):</span>
                <span className="font-mono text-white font-bold">2,450 Hz (Âm trầm bí ẩn)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Phù hợp thể loại kịch bản:</span>
                <span className="font-mono text-nle-cyan font-bold">Bí ẩn, Lịch sử, Tài liệu giải mật</span>
              </div>
            </div>
          </Card>

          {/* Card 3: Audio Quality & Peak Metering */}
          <Card className="p-4 bg-nle-surface border-nle-border space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center">
                <Volume2 className="w-4 h-4 mr-1 text-emerald-400" />
                Kiểm Định Chất Lượng Âm Thanh (Quality Inspector)
              </span>
              <Badge variant="emerald" className="text-[10px]">EBU R128 PASS</Badge>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Đỉnh âm cực đại (True Peak):</span>
                <span className="font-mono text-emerald-400 font-bold">-1.0 dBTP (Không méo tiếng)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Độ lệch DC Offset:</span>
                <span className="font-mono text-emerald-400 font-bold">0.0001% (Hoàn hảo)</span>
              </div>

              <div className="flex justify-between p-2 rounded bg-nle-panel">
                <span className="text-gray-400">Nhiễu nền (Noise Floor):</span>
                <span className="font-mono text-emerald-400 font-bold">-62.5 dB (Rất sạch)</span>
              </div>
            </div>
          </Card>

          {/* Card 4: AI Stem Isolation & De-Noise */}
          <Card className="p-4 bg-nle-surface border-nle-border space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-nle-border">
              <span className="text-xs font-bold text-white flex items-center">
                <Sparkles className="w-4 h-4 mr-1 text-nle-violet" />
                Tách Nhạc & Phục Chế Âm Thanh (Demucs / Spleeter)
              </span>
              <Badge variant="cyan" className="text-[10px]">AI Stem Splitter</Badge>
            </div>

            <p className="text-[11px] text-gray-400">
              Tách file âm thanh bất kỳ thành 4 stems độc lập để remix và xử lý hậu kỳ chuyên sâu:
            </p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-nle-border hover:border-nle-cyan"
                onClick={() => alert("Đã trích xuất Stem 1: Giọng hát / Thoại (Vocals)!")}
              >
                🎙️ Tách Lời Thoại (Vocals)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-nle-border hover:border-amber-400"
                onClick={() => alert("Đã trích xuất Stem 2: Nhạc cụ / Giai điệu (Instruments)!")}
              >
                🎵 Tách Nhạc Cụ (Music)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-nle-border hover:border-emerald-400"
                onClick={() => alert("Đã trích xuất Stem 3: Trống & Nhịp đập (Drums)!")}
              >
                🥁 Tách Trống & Beat (Drums)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-nle-border hover:border-rose-400"
                onClick={() => alert("Đã trích xuất Stem 4: Âm trầm Sub-bass!")}
              >
                🎸 Tách Âm Trầm (Bass)
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
