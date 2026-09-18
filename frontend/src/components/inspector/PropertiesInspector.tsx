"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Type,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Palette,
  Scissors,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Sliders,
  Smile,
  Shield,
  Eye,
  RotateCcw,
} from "lucide-react";

export function PropertiesInspector() {
  // Accordion toggle states
  const [openText, setOpenText] = useState(true);
  const [openAppearance, setOpenAppearance] = useState(true);
  const [openTransform, setOpenTransform] = useState(false);
  const [openCutout, setOpenCutout] = useState(false);

  // Text Typography State (Premiere Pro 2025 Text Properties)
  const [fontFamily, setFontFamily] = useState("Monument Extended");
  const [fontSize, setFontSize] = useState(96);
  const [fontWeight, setFontWeight] = useState("Bold");
  const [textAlign, setTextAlign] = useState<"left" | "center" | "right" | "justify">("center");
  const [tracking, setTracking] = useState(15);
  const [leading, setLeading] = useState(110);
  const [allCaps, setAllCaps] = useState(true);

  // Appearance State (Fill, Stroke, Background, Shadow)
  const [fillColor, setFillColor] = useState("#ffffff");
  const [hasStroke, setHasStroke] = useState(true);
  const [strokeColor, setStrokeColor] = useState("#000000");
  const [strokeWidth, setStrokeWidth] = useState(4);
  const [strokePosition, setStrokePosition] = useState<"Outer" | "Center" | "Inner">("Outer");
  const [hasBackground, setHasBackground] = useState(false);
  const [bgColor, setBgColor] = useState("#090a0f");
  const [bgOpacity, setBgOpacity] = useState(80);
  const [hasShadow, setHasShadow] = useState(true);
  const [shadowColor, setShadowColor] = useState("#00f0ff");
  const [shadowBlur, setShadowBlur] = useState(16);

  // CapCut Pro Cutout & Retouch State
  const [autoCutoutEnabled, setAutoCutoutEnabled] = useState(false);
  const [chromaKeyEnabled, setChromaKeyEnabled] = useState(false);
  const [chromaColor, setChromaColor] = useState("#00ff00");
  const [chromaIntensity, setChromaIntensity] = useState(50);
  const [maskShape, setMaskShape] = useState<"none" | "rectangle" | "circle" | "split" | "heart">("none");
  const [skinSmooth, setSkinSmooth] = useState(20);

  return (
    <Card className="h-full flex flex-col bg-nle-surface border-nle-border overflow-hidden text-xs">
      {/* Inspector Header */}
      <CardHeader className="py-2.5 px-3 border-b border-nle-border flex flex-row items-center justify-between shrink-0 bg-nle-panel">
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-nle-cyan" />
          <CardTitle className="text-xs font-bold text-white tracking-wide">
            Properties Inspector
          </CardTitle>
        </div>
        <Badge variant="cyan" className="text-[9px] uppercase font-mono">
          Premiere 2025 • CapCut
        </Badge>
      </CardHeader>

      {/* Inspector Scrollable Body */}
      <CardContent className="p-3 space-y-3 flex-1 overflow-y-auto">
        {/* Accordion 1: Text Typography (Premiere 2025) */}
        <div className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden">
          <button
            onClick={() => setOpenText(!openText)}
            className="w-full px-3 py-2 flex items-center justify-between font-bold text-white hover:bg-nle-surface/60 transition-colors"
          >
            <span className="flex items-center">
              <Type className="w-3.5 h-3.5 mr-1.5 text-nle-cyan" />
              Định dạng Chữ (Typography)
            </span>
            {openText ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
          </button>

          {openText && (
            <div className="p-3 space-y-3 border-t border-nle-border text-xs">
              {/* Font Family & Weight */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 uppercase font-mono">Phông chữ</label>
                  <select
                    value={fontFamily}
                    onChange={(e) => setFontFamily(e.target.value)}
                    className="w-full p-1.5 bg-nle-base border border-nle-border rounded text-[11px] text-gray-200 focus:outline-none focus:border-nle-cyan"
                  >
                    <option value="Monument Extended">Monument Extended</option>
                    <option value="Inter">Inter UI Display</option>
                    <option value="Outfit">Outfit Bold</option>
                    <option value="Oswald">Oswald Headline</option>
                    <option value="JetBrains Mono">JetBrains Mono</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 uppercase font-mono">Độ dày</label>
                  <select
                    value={fontWeight}
                    onChange={(e) => setFontWeight(e.target.value)}
                    className="w-full p-1.5 bg-nle-base border border-nle-border rounded text-[11px] text-gray-200 focus:outline-none focus:border-nle-cyan"
                  >
                    <option value="Regular">Regular (400)</option>
                    <option value="Medium">Medium (500)</option>
                    <option value="Bold">Bold (700)</option>
                    <option value="Black">Black Heavy (900)</option>
                  </select>
                </div>
              </div>

              {/* Font Size & Alignment */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Cỡ chữ (Size)</span>
                  <span className="font-mono text-nle-cyan">{fontSize} pt</span>
                </div>
                <Slider
                  value={[fontSize]}
                  min={18}
                  max={200}
                  step={1}
                  onValueChange={([val]) => setFontSize(val)}
                />
              </div>

              {/* Alignment & Styles Button Bar */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-1 bg-nle-base p-0.5 rounded border border-nle-border">
                  {[
                    { id: "left", icon: AlignLeft },
                    { id: "center", icon: AlignCenter },
                    { id: "right", icon: AlignRight },
                    { id: "justify", icon: AlignJustify },
                  ].map((align) => {
                    const Icon = align.icon;
                    return (
                      <button
                        key={align.id}
                        onClick={() => setTextAlign(align.id as any)}
                        className={`p-1 rounded ${
                          textAlign === align.id ? "bg-nle-cyan text-black" : "text-gray-400 hover:text-white"
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setAllCaps(!allCaps)}
                  className={`px-2 py-1 rounded text-[10px] font-bold border transition-colors ${
                    allCaps
                      ? "bg-nle-cyan/20 border-nle-cyan text-nle-cyan"
                      : "bg-nle-base border-nle-border text-gray-400 hover:text-white"
                  }`}
                >
                  TT ALL CAPS
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Accordion 2: Appearance & Styling (Premiere 2025) */}
        <div className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden">
          <button
            onClick={() => setOpenAppearance(!openAppearance)}
            className="w-full px-3 py-2 flex items-center justify-between font-bold text-white hover:bg-nle-surface/60 transition-colors"
          >
            <span className="flex items-center">
              <Palette className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
              Hiệu Ứng Bề Mặt (Appearance)
            </span>
            {openAppearance ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
          </button>

          {openAppearance && (
            <div className="p-3 space-y-3 border-t border-nle-border text-xs">
              {/* Fill Color */}
              <div className="flex items-center justify-between">
                <span className="text-gray-300 font-medium">Màu chữ (Fill)</span>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={fillColor}
                    onChange={(e) => setFillColor(e.target.value)}
                    className="w-6 h-6 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="font-mono text-gray-400 text-[10px]">{fillColor.toUpperCase()}</span>
                </div>
              </div>

              {/* Stroke */}
              <div className="space-y-1.5 pt-2 border-t border-nle-border">
                <div className="flex items-center justify-between">
                  <label className="flex items-center space-x-2 cursor-pointer text-gray-300">
                    <input
                      type="checkbox"
                      checked={hasStroke}
                      onChange={(e) => setHasStroke(e.target.checked)}
                      className="rounded border-nle-border text-nle-cyan w-3.5 h-3.5"
                    />
                    <span>Viền chữ (Stroke)</span>
                  </label>
                  {hasStroke && (
                    <div className="flex items-center space-x-2">
                      <input
                        type="color"
                        value={strokeColor}
                        onChange={(e) => setStrokeColor(e.target.value)}
                        className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                      />
                      <span className="font-mono text-gray-400 text-[10px]">{strokeWidth}px ({strokePosition})</span>
                    </div>
                  )}
                </div>
                {hasStroke && (
                  <Slider
                    value={[strokeWidth]}
                    min={1}
                    max={20}
                    step={1}
                    onValueChange={([val]) => setStrokeWidth(val)}
                  />
                )}
              </div>

              {/* Shadow Glow */}
              <div className="space-y-1.5 pt-2 border-t border-nle-border">
                <div className="flex items-center justify-between">
                  <label className="flex items-center space-x-2 cursor-pointer text-gray-300">
                    <input
                      type="checkbox"
                      checked={hasShadow}
                      onChange={(e) => setHasShadow(e.target.checked)}
                      className="rounded border-nle-border text-nle-cyan w-3.5 h-3.5"
                    />
                    <span>Hào quang & Đổ bóng (Glow / Shadow)</span>
                  </label>
                  {hasShadow && (
                    <input
                      type="color"
                      value={shadowColor}
                      onChange={(e) => setShadowColor(e.target.value)}
                      className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                    />
                  )}
                </div>
                {hasShadow && (
                  <Slider
                    value={[shadowBlur]}
                    min={0}
                    max={40}
                    step={1}
                    onValueChange={([val]) => setShadowBlur(val)}
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Accordion 3: CapCut Cutout & Chroma Key */}
        <div className="rounded-lg border border-nle-border bg-nle-panel overflow-hidden">
          <button
            onClick={() => setOpenCutout(!openCutout)}
            className="w-full px-3 py-2 flex items-center justify-between font-bold text-white hover:bg-nle-surface/60 transition-colors"
          >
            <span className="flex items-center">
              <Scissors className="w-3.5 h-3.5 mr-1.5 text-rose-400" />
              Tách Nền & Mặt nạ (CapCut Cutout & Mask)
            </span>
            {openCutout ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
          </button>

          {openCutout && (
            <div className="p-3 space-y-3 border-t border-nle-border text-xs">
              {/* Auto Cutout (No Green Screen) */}
              <div className="flex items-center justify-between p-2 rounded bg-nle-base border border-nle-border">
                <div className="space-y-0.5">
                  <span className="font-semibold text-white block">Auto Cutout AI</span>
                  <span className="text-[10px] text-gray-400">Tách người tự động không cần phông xanh</span>
                </div>
                <input
                  type="checkbox"
                  checked={autoCutoutEnabled}
                  onChange={(e) => setAutoCutoutEnabled(e.target.checked)}
                  className="rounded border-nle-border text-nle-cyan w-4 h-4 cursor-pointer"
                />
              </div>

              {/* Chroma Key */}
              <div className="space-y-1.5 pt-1">
                <div className="flex items-center justify-between">
                  <label className="flex items-center space-x-2 cursor-pointer text-gray-300">
                    <input
                      type="checkbox"
                      checked={chromaKeyEnabled}
                      onChange={(e) => setChromaKeyEnabled(e.target.checked)}
                      className="rounded border-nle-border text-nle-cyan w-3.5 h-3.5"
                    />
                    <span>Chroma Key Phông Xanh</span>
                  </label>
                  {chromaKeyEnabled && (
                    <input
                      type="color"
                      value={chromaColor}
                      onChange={(e) => setChromaColor(e.target.value)}
                      className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                    />
                  )}
                </div>
                {chromaKeyEnabled && (
                  <Slider
                    value={[chromaIntensity]}
                    min={0}
                    max={100}
                    step={1}
                    onValueChange={([val]) => setChromaIntensity(val)}
                  />
                )}
              </div>

              {/* Mask Shapes */}
              <div className="space-y-1 pt-2 border-t border-nle-border">
                <label className="text-[10px] text-gray-400 uppercase font-mono">Hình dạng Mặt Nạ (Mask)</label>
                <div className="grid grid-cols-4 gap-1">
                  {(["none", "rectangle", "circle", "split"] as const).map((shape) => (
                    <button
                      key={shape}
                      onClick={() => setMaskShape(shape)}
                      className={`p-1 rounded text-[10px] capitalize font-semibold transition-colors ${
                        maskShape === shape
                          ? "bg-rose-500 text-white"
                          : "bg-nle-base border border-nle-border text-gray-400 hover:text-white"
                      }`}
                    >
                      {shape}
                    </button>
                  ))}
                </div>
              </div>

              {/* Face Retouch Smooth */}
              <div className="space-y-1.5 pt-2 border-t border-nle-border">
                <div className="flex justify-between text-gray-300 text-[11px]">
                  <span>Làm mịn da AI (Face Retouch)</span>
                  <span className="font-mono text-rose-400">{skinSmooth}%</span>
                </div>
                <Slider
                  value={[skinSmooth]}
                  min={0}
                  max={100}
                  step={1}
                  onValueChange={([val]) => setSkinSmooth(val)}
                />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
