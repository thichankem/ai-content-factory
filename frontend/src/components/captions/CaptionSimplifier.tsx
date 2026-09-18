"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Type,
  Sparkles,
  Flame,
  Smile,
  Zap,
  Globe,
  Loader2,
  CheckCircle2,
  Sliders,
} from "lucide-react";

export type CaptionTemplateCategory =
  | "trending"
  | "emphasis"
  | "glow"
  | "emoji"
  | "monoline"
  | "multiline";

interface CaptionTemplate {
  id: string;
  category: CaptionTemplateCategory;
  name: string;
  previewText: string;
  textColor: string;
  bgColor?: string;
  glowColor?: string;
  hasEmoji?: boolean;
}

const CAPTION_TEMPLATES: CaptionTemplate[] = [
  {
    id: "trend-box",
    category: "trending",
    name: "Viral Box High-Contrast",
    previewText: "THE SECRET",
    textColor: "#ffffff",
    bgColor: "#ef4444",
  },
  {
    id: "trend-black-yellow",
    category: "trending",
    name: "Bold Black & Yellow",
    previewText: "WAIT FOR IT!",
    textColor: "#facc15",
    bgColor: "#000000",
  },
  {
    id: "emph-bounce",
    category: "emphasis",
    name: "Bounce Word Highlight",
    previewText: "DON'T MISS",
    textColor: "#00f0ff",
  },
  {
    id: "glow-cyber",
    category: "glow",
    name: "Cyber Neon Glow",
    previewText: "NEON IMPACT",
    textColor: "#00f0ff",
    glowColor: "rgba(0, 240, 255, 0.9)",
  },
  {
    id: "glow-gold",
    category: "glow",
    name: "Gold Cinema Glow",
    previewText: "GOLD LEGEND",
    textColor: "#fbbf24",
    glowColor: "rgba(251, 191, 36, 0.9)",
  },
  {
    id: "emoji-pop",
    category: "emoji",
    name: "Smart Auto Emoji Pop",
    previewText: "CỰC SỐC 🔥😱",
    textColor: "#ffffff",
    hasEmoji: true,
  },
  {
    id: "mono-clean",
    category: "monoline",
    name: "Minimalist Monoline",
    previewText: "Minimal Subtitle Line",
    textColor: "#f8fafc",
  },
  {
    id: "multi-cinema",
    category: "multiline",
    name: "Cinema Classic 2-Line",
    previewText: "Classic dialogue text\non secondary line",
    textColor: "#ffffff",
  },
];

export function CaptionSimplifier() {
  const [selectedCategory, setSelectedCategory] = useState<CaptionTemplateCategory>("trending");
  const [selectedTemplateId, setSelectedTemplateId] = useState("trend-box");
  const [language, setLanguage] = useState("vi-VN");
  const [keywordHighlight, setKeywordHighlight] = useState(true);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcribeDone, setTranscribeDone] = useState(false);

  const categories: Array<{ id: CaptionTemplateCategory; label: string }> = [
    { id: "trending", label: "Trending" },
    { id: "emphasis", label: "Emphasis" },
    { id: "glow", label: "Glow Neon" },
    { id: "emoji", label: "Emoji Pop" },
    { id: "monoline", label: "Monoline" },
    { id: "multiline", label: "Multiline" },
  ];

  const filteredTemplates = CAPTION_TEMPLATES.filter((t) => t.category === selectedCategory);

  const handleGenerateCaptions = async () => {
    setIsTranscribing(true);
    await new Promise((r) => setTimeout(r, 1300));
    setIsTranscribing(false);
    setTranscribeDone(true);
  };

  return (
    <Card className="h-full flex flex-col bg-nle-surface border-nle-border overflow-hidden">
      <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
        <CardTitle className="text-xs font-bold text-white flex items-center">
          <Type className="w-4 h-4 mr-1.5 text-nle-cyan" />
          CapCut Pro Auto-Captions & Mẫu Phụ Đề
        </CardTitle>
        <Badge variant="cyan" className="text-[9px] uppercase font-mono">
          Speech-to-Text AI
        </Badge>
      </CardHeader>

      <CardContent className="p-3 space-y-3 flex-1 overflow-y-auto text-xs">
        {/* Top Control Bar: Language & Keyword Highlight */}
        <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg bg-nle-panel border border-nle-border">
          <div className="flex items-center space-x-2">
            <Globe className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="p-1 bg-nle-base border border-nle-border rounded text-[11px] text-gray-200 focus:outline-none"
            >
              <option value="vi-VN">🇻🇳 Tiếng Việt (AI Whisper)</option>
              <option value="en-US">🇺🇸 English (US)</option>
            </select>
          </div>

          <label className="flex items-center space-x-1.5 cursor-pointer text-[11px] text-gray-300">
            <input
              type="checkbox"
              checked={keywordHighlight}
              onChange={(e) => setKeywordHighlight(e.target.checked)}
              className="rounded border-nle-border text-nle-cyan w-3.5 h-3.5"
            />
            <span>Keyword Highlight (Tô đậm từ khóa)</span>
          </label>
        </div>

        {/* Categories Tabs */}
        <div className="flex items-center space-x-1 bg-nle-panel p-0.5 rounded-lg border border-nle-border overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === cat.id
                  ? "bg-nle-surface text-nle-cyan shadow-sm border border-nle-cyan/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Templates Grid */}
        <div className="grid grid-cols-2 gap-2 flex-1">
          {filteredTemplates.map((template) => {
            const isSelected = selectedTemplateId === template.id;
            return (
              <div
                key={template.id}
                onClick={() => setSelectedTemplateId(template.id)}
                className={`p-3 rounded-lg border cursor-pointer flex flex-col justify-between items-center text-center transition-all aspect-video ${
                  isSelected
                    ? "border-nle-cyan bg-nle-cyan/10 ring-1 ring-nle-cyan shadow-md shadow-nle-cyan/10"
                    : "border-nle-border bg-nle-panel hover:border-gray-600"
                }`}
              >
                <div
                  style={{
                    backgroundColor: template.bgColor || "transparent",
                    color: template.textColor,
                    textShadow: template.glowColor ? `0 0 10px ${template.glowColor}` : "none",
                  }}
                  className="px-2 py-1 rounded font-black text-xs tracking-wider uppercase font-sans max-w-full truncate"
                >
                  {template.previewText}
                </div>

                <div className="w-full flex justify-between items-center text-[10px] text-gray-400 pt-1 border-t border-nle-border/40">
                  <span className="truncate max-w-[100px]">{template.name}</span>
                  {isSelected && <span className="text-nle-cyan font-bold">✓</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Generate Button & Status */}
        <div className="pt-2 border-t border-nle-border space-y-2">
          <Button
            size="sm"
            variant="neon"
            onClick={handleGenerateCaptions}
            disabled={isTranscribing}
            className="w-full text-xs h-8"
          >
            {isTranscribing ? (
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
            )}
            Sinh Phụ Đề Tự Động Vào Timeline (Whisper ASR)
          </Button>

          {transcribeDone && (
            <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] flex items-center justify-between">
              <span className="flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                Đã đồng bộ 24 khối phụ đề karaoke vào Track C1 trên Timeline!
              </span>
              <Badge variant="emerald" className="text-[9px]">
                100% Synced
              </Badge>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
