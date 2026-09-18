"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useTimelineStore } from "@/stores/useTimelineStore";
import { createScene } from "@/lib/scenes";
import {
  Code,
  Eye,
  Plus,
  Play,
  Copy,
  Sparkles,
  LayoutTemplate,
  Monitor,
  Smartphone,
  CheckCircle2,
  Layers,
  Wand2,
} from "lucide-react";

interface SlideTemplate {
  id: string;
  name: string;
  description: string;
  category: "hook" | "stats" | "comparison" | "quote" | "code";
  html: string;
  css: string;
}

const PRESET_TEMPLATES: SlideTemplate[] = [
  {
    id: "cyber-hook",
    name: "Cyberpunk Hook Title",
    description: "Tiêu đề giật gân với viền neon phát sáng và nền lưới cyberpunk",
    category: "hook",
    html: `<div class="slide-container">
  <div class="cyber-badge">VIRAL HOOK • 00:03</div>
  <h1 class="glitch-title">90% VIDEO NGẮN<br/><span class="cyan-gradient">THẤT BẠI TẠI ĐÂY!</span></h1>
  <p class="subtitle">Bí quyết giữ chân người xem trong 3 giây vàng đầu tiên</p>
  <div class="pulse-line"></div>
</div>`,
    css: `* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }
body, html { width: 100%; height: 100%; background: #070913; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.slide-container { text-align: center; padding: 40px; border: 1px solid rgba(0, 240, 255, 0.3); background: radial-gradient(circle at center, #101935 0%, #060913 100%); border-radius: 20px; box-shadow: 0 0 50px rgba(0, 240, 255, 0.15); max-width: 90%; }
.cyber-badge { display: inline-block; padding: 6px 16px; background: rgba(0, 240, 255, 0.1); border: 1px solid #00f0ff; border-radius: 50px; font-size: 13px; font-weight: 800; color: #00f0ff; letter-spacing: 2px; margin-bottom: 20px; text-transform: uppercase; }
.glitch-title { font-size: 46px; font-weight: 900; line-height: 1.15; color: #ffffff; letter-spacing: -1px; margin-bottom: 16px; }
.cyan-gradient { background: linear-gradient(135deg, #00f0ff 0%, #a855f7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.subtitle { font-size: 18px; color: #94a3b8; max-width: 500px; margin: 0 auto 24px; }
.pulse-line { width: 80px; height: 4px; background: #00f0ff; margin: 0 auto; border-radius: 2px; box-shadow: 0 0 12px #00f0ff; }`,
  },
  {
    id: "stats-metric",
    name: "Dynamic Stat Counter",
    description: "Thống kê dữ liệu với con số ấn tượng và thanh tiến trình",
    category: "stats",
    html: `<div class="stats-card">
  <div class="stat-number">+850%</div>
  <div class="stat-label">TĂNG TRƯỞNG LƯỢT XEM TỰ NHIÊN</div>
  <div class="bar-container">
    <div class="bar-fill"></div>
  </div>
  <div class="stat-meta">Dữ liệu đo lường thực tế trên 1,000 kênh Creator</div>
</div>`,
    css: `* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }
body, html { width: 100%; height: 100%; background: #0a0e1a; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.stats-card { background: linear-gradient(145deg, #111827, #1f293d); border: 1px solid rgba(255, 255, 255, 0.1); padding: 50px 60px; border-radius: 24px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
.stat-number { font-size: 72px; font-weight: 900; color: #10b981; text-shadow: 0 0 30px rgba(16, 185, 129, 0.4); margin-bottom: 10px; font-family: monospace; }
.stat-label { font-size: 16px; font-weight: 800; letter-spacing: 2px; color: #f8fafc; margin-bottom: 24px; }
.bar-container { width: 320px; height: 10px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; margin: 0 auto 16px; }
.bar-fill { width: 85%; height: 100%; background: linear-gradient(90deg, #10b981, #00f0ff); border-radius: 10px; }
.stat-meta { font-size: 13px; color: #64748b; }`,
  },
  {
    id: "split-comparison",
    name: "Before vs After Comparison",
    description: "So sánh 2 cột trực quan: Cách làm cũ vs Cách làm AI đột phá",
    category: "comparison",
    html: `<div class="comparison-wrapper">
  <div class="col old-way">
    <div class="tag red-tag">CÁCH CŨ (THỦ CÔNG)</div>
    <h3>Mất 8 Giờ / Video</h3>
    <p>• Dò dẫm tìm ảnh trên mạng</p>
    <p>• Cắt ghép từng vết nối bằng tay</p>
    <p>• Dễ bị dính bản quyền âm thanh</p>
  </div>
  <div class="vs-badge">VS</div>
  <div class="col new-way">
    <div class="tag green-tag">AI CONTENT FACTORY</div>
    <h3>Chỉ 3 Phút Hoàn Tất</h3>
    <p>• Kịch bản cấu trúc Hook giữ chân</p>
    <p>• Tự động xếp Timeline đa track</p>
    <p>• 100% bản quyền được kiểm định</p>
  </div>
</div>`,
    css: `* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }
body, html { width: 100%; height: 100%; background: #070a12; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.comparison-wrapper { display: flex; align-items: center; gap: 20px; max-width: 90%; }
.col { flex: 1; padding: 30px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.08); background: #0f172a; min-width: 240px; }
.old-way { border-color: rgba(239, 68, 68, 0.3); }
.new-way { border-color: rgba(16, 185, 129, 0.4); background: radial-gradient(circle at top, #142838 0%, #0b1322 100%); }
.tag { display: inline-block; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 4px; margin-bottom: 12px; }
.red-tag { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.green-tag { background: rgba(16, 185, 129, 0.15); color: #10b981; }
h3 { color: #fff; font-size: 20px; margin-bottom: 14px; }
p { font-size: 13px; color: #94a3b8; margin-bottom: 8px; line-height: 1.5; }
.vs-badge { width: 42px; height: 42px; border-radius: 50%; background: #f59e0b; color: #000; font-weight: 900; display: flex; align-items: center; justify-content: center; font-size: 14px; shrink: 0; box-shadow: 0 0 15px rgba(245, 158, 11, 0.4); }`,
  },
  {
    id: "quote-glass",
    name: "Glassmorphic Quote Card",
    description: "Trích dẫn triết lý hoặc châm ngôn sống với nền mờ thủy tinh sang trọng",
    category: "quote",
    html: `<div class="quote-box">
  <div class="quote-symbol">“</div>
  <p class="quote-text">Sự chú ý là loại tiền tệ đắt giá nhất của kỷ nguyên số. Hãy tạo ra nội dung giữ chân họ từ giây đầu tiên.</p>
  <div class="author-row">
    <div class="avatar"></div>
    <div class="author-info">
      <div class="author-name">Alex Hormozi</div>
      <div class="author-role">Founder of Acquisition.com</div>
    </div>
  </div>
</div>`,
    css: `* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }
body, html { width: 100%; height: 100%; background: radial-gradient(circle at 80% 20%, #2e1065 0%, #030712 70%); display: flex; align-items: center; justify-content: center; overflow: hidden; }
.quote-box { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.12); padding: 40px; border-radius: 24px; max-width: 540px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.4); }
.quote-symbol { font-size: 80px; line-height: 1; color: #a855f7; opacity: 0.6; font-family: Georgia, serif; position: absolute; top: 10px; left: 24px; }
.quote-text { font-size: 20px; color: #f8fafc; line-height: 1.6; font-style: italic; margin: 30px 0 24px; }
.author-row { display: flex; align-items: center; gap: 14px; border-top: 1px solid rgba(255,255,255,0.08); pt: 16px; padding-top: 16px; }
.avatar { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #a855f7, #3b82f6); }
.author-name { font-size: 15px; font-weight: 700; color: #fff; }
.author-role { font-size: 12px; color: #94a3b8; }`,
  },
  {
    id: "terminal-code",
    name: "Terminal Code Snippet",
    description: "Khối mã nguồn lập trình với giao diện Console công nghệ cao",
    category: "code",
    html: `<div class="terminal-window">
  <div class="terminal-bar">
    <div class="dots"><span class="r"></span><span class="y"></span><span class="g"></span></div>
    <div class="term-title">pipeline_orchestrator.ts</div>
  </div>
  <pre class="code-area"><code><span class="k">const</span> pipeline = <span class="k">new</span> <span class="c">AIContentFactory</span>();

<span class="comment">// Khởi chạy quy trình dựng phim tự động</span>
<span class="k">await</span> pipeline.<span class="f">renderMasterCut</span>({
  hook: <span class="s">"3s_viral_retention"</span>,
  resolution: <span class="s">"1080x1920"</span>,
  fps: <span class="n">60</span>,
  audioEQ: <span class="s">"5_band_parametric"</span>
});</code></pre>
</div>`,
    css: `* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'JetBrains Mono', monospace, sans-serif; }
body, html { width: 100%; height: 100%; background: #050811; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.terminal-window { width: 520px; background: #0c1222; border: 1px solid rgba(0, 240, 255, 0.25); border-radius: 12px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.6); }
.terminal-bar { background: #131b2e; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); }
.dots { display: flex; gap: 6px; }
.dots span { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.r { background: #ef4444; } .y { background: #f59e0b; } .g { background: #10b981; }
.term-title { font-size: 11px; color: #94a3b8; }
.code-area { padding: 24px; font-size: 14px; line-height: 1.7; color: #e2e8f0; }
.k { color: #f43f5e; font-weight: 700; }
.c { color: #00f0ff; }
.f { color: #60a5fa; }
.s { color: #34d399; }
.n { color: #fbbf24; }
.comment { color: #64748b; font-style: italic; }`,
  },
];

interface HtmlSlideDeckStudioProps {
  onAddSlideToMedia?: (slideAsset: any) => void;
}

export function HtmlSlideDeckStudio({ onAddSlideToMedia }: HtmlSlideDeckStudioProps) {
  const { scenes, setScenes } = useTimelineStore();
  const [selectedTemplate, setSelectedTemplate] = useState<SlideTemplate>(PRESET_TEMPLATES[0]);
  const [htmlCode, setHtmlCode] = useState(PRESET_TEMPLATES[0].html);
  const [cssCode, setCssCode] = useState(PRESET_TEMPLATES[0].css);
  const [activeCodeTab, setActiveCodeTab] = useState<"html" | "css">("html");
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16">("16:9");
  const [slideDuration, setSlideDuration] = useState(4.0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleSelectTemplate = (template: SlideTemplate) => {
    setSelectedTemplate(template);
    setHtmlCode(template.html);
    setCssCode(template.css);
    setStatusMessage(`Đã nạp mẫu "${template.name}"!`);
    setTimeout(() => setStatusMessage(null), 2500);
  };

  const handleInsertIntoTimeline = () => {
    const newSceneIndex = scenes.length;
    const newScene = createScene(newSceneIndex, {
      label: `Slide: ${selectedTemplate.name}`,
      duration: slideDuration,
      text: `HTML Slide [${selectedTemplate.category.toUpperCase()}]`,
      filter: "none",
    });

    setScenes([...scenes, newScene]);

    if (onAddSlideToMedia) {
      onAddSlideToMedia({
        id: `slide-${Date.now()}`,
        name: `slide_${selectedTemplate.id}.html`,
        type: "slide",
        size: "12 KB",
        duration: `${slideDuration}s`,
        source: "HTML/CSS Deck Studio",
      });
    }

    setStatusMessage(`✅ Đã chèn Slide "${selectedTemplate.name}" (${slideDuration}s) vào Timeline thành công!`);
    setTimeout(() => setStatusMessage(null), 3500);
  };

  const fullDoc = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    ${cssCode}
  </style>
</head>
<body>
  ${htmlCode}
</body>
</html>`;

  return (
    <div className="flex flex-col h-full space-y-3 overflow-hidden">
      {/* Header Bar */}
      <div className="flex items-center justify-between bg-nle-panel border border-nle-border rounded-xl px-4 py-2.5 shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-nle-surface flex items-center justify-center text-nle-cyan border border-nle-border">
            <LayoutTemplate className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-xs text-white flex items-center space-x-1.5">
              <span>Interactive HTML/CSS Presentation Slide Deck Studio</span>
              <Badge variant="cyan" className="text-[9px] uppercase px-1">
                Vector Web Engine
              </Badge>
            </h3>
            <p className="text-[11px] text-gray-400">
              Thiết kế slide đồ họa bằng HTML5/CSS3 với animation mượt mà, chèn thẳng vào timeline video
            </p>
          </div>
        </div>

        {/* Aspect & Action Buttons */}
        <div className="flex items-center space-x-2">
          {/* Aspect Ratio Switcher */}
          <div className="flex items-center bg-nle-surface rounded-lg p-0.5 border border-nle-border text-xs">
            <button
              onClick={() => setAspectRatio("16:9")}
              className={`px-2 py-1 rounded flex items-center space-x-1 transition-all ${
                aspectRatio === "16:9" ? "bg-nle-cyan text-black font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              <Monitor className="w-3.5 h-3.5" />
              <span>16:9</span>
            </button>
            <button
              onClick={() => setAspectRatio("9:16")}
              className={`px-2 py-1 rounded flex items-center space-x-1 transition-all ${
                aspectRatio === "9:16" ? "bg-nle-cyan text-black font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span>9:16</span>
            </button>
          </div>

          {/* Duration Selector */}
          <div className="flex items-center space-x-1 text-xs text-gray-300 bg-nle-surface px-2.5 py-1 rounded-lg border border-nle-border">
            <span>Thời lượng:</span>
            <select
              value={slideDuration}
              onChange={(e) => setSlideDuration(parseFloat(e.target.value))}
              className="bg-transparent text-nle-cyan font-bold outline-none cursor-pointer text-xs"
            >
              <option value="3.0" className="bg-nle-panel">3.0s</option>
              <option value="4.0" className="bg-nle-panel">4.0s</option>
              <option value="5.0" className="bg-nle-panel">5.0s</option>
              <option value="8.0" className="bg-nle-panel">8.0s</option>
            </select>
          </div>

          {/* Add to Timeline Button */}
          <Button
            size="sm"
            variant="neon"
            onClick={handleInsertIntoTimeline}
            className="text-xs h-8"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            Chèn Vào Timeline
          </Button>
        </div>
      </div>

      {statusMessage && (
        <div className="px-4 py-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center space-x-2 shrink-0 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Main Studio Viewport: Left Template Catalog + Center Live Preview + Right Code Editor */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* Left Column: Preset Templates */}
        <div className="lg:col-span-3 bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col space-y-2 overflow-y-auto">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider px-1">
            Mẫu Slide Có Sẵn (Presets)
          </span>

          <div className="space-y-1.5 flex-1">
            {PRESET_TEMPLATES.map((tmpl) => {
              const isSelected = selectedTemplate.id === tmpl.id;
              return (
                <button
                  key={tmpl.id}
                  onClick={() => handleSelectTemplate(tmpl)}
                  className={`w-full text-left p-2.5 rounded-lg border transition-all flex flex-col space-y-1 ${
                    isSelected
                      ? "bg-nle-panel border-nle-cyan text-white shadow-md shadow-nle-cyan/10"
                      : "bg-nle-base/50 border-nle-border/60 text-gray-300 hover:border-nle-border hover:bg-nle-panel/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-white">{tmpl.name}</span>
                    <Badge variant={isSelected ? "cyan" : "outline"} className="text-[9px] uppercase px-1">
                      {tmpl.category}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-gray-400 line-clamp-2">{tmpl.description}</p>
                </button>
              );
            })}
          </div>

          <div className="pt-2 border-t border-nle-border">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setHtmlCode(`<div style="text-align:center;color:#00f0ff;padding:40px;">\n  <h1>TIÊU ĐỀ SLIDE MỚI</h1>\n  <p>Nhập nội dung HTML/CSS của bạn tại đây...</p>\n</div>`);
                setCssCode(`body { background: #0b0f19; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }`);
                setStatusMessage("Đã tạo mẫu Slide trống!");
              }}
              className="w-full text-xs border-nle-border"
            >
              <Plus className="w-3.5 h-3.5 mr-1 text-nle-cyan" />
              Tạo Slide Trống (Blank)
            </Button>
          </div>
        </div>

        {/* Center Column: Live Sandboxed Iframe Preview */}
        <div className="lg:col-span-5 bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col justify-between overflow-hidden">
          <div className="flex items-center justify-between pb-2 border-b border-nle-border shrink-0">
            <span className="text-xs font-bold text-white flex items-center space-x-1.5">
              <Eye className="w-3.5 h-3.5 text-emerald-400" />
              <span>Khung Xem Trước Trực Tiếp (Live Sandboxed Preview)</span>
            </span>
            <Badge variant="outline" className="text-[10px] font-mono text-gray-400">
              {aspectRatio === "16:9" ? "1920x1080 (16:9)" : "1080x1920 (9:16)"}
            </Badge>
          </div>

          {/* Iframe Viewport */}
          <div className="flex-1 my-2 bg-black rounded-lg border border-nle-border overflow-hidden flex items-center justify-center p-2">
            <div
              style={{
                aspectRatio: aspectRatio === "16:9" ? "16/9" : "9/16",
                maxHeight: "100%",
                maxWidth: "100%",
              }}
              className="w-full h-full rounded border border-white/10 overflow-hidden shadow-2xl bg-[#090a0f]"
            >
              <iframe
                title="Slide Preview"
                srcDoc={fullDoc}
                sandbox="allow-scripts"
                className="w-full h-full border-0 pointer-events-auto"
              />
            </div>
          </div>

          <div className="flex justify-between items-center text-[10px] text-gray-400 pt-1 shrink-0">
            <span>✨ Tự động cập nhật tức thì khi gõ mã HTML/CSS</span>
            <span className="font-mono text-nle-cyan">Web Standards DOM</span>
          </div>
        </div>

        {/* Right Column: HTML & CSS Code Editors */}
        <div className="lg:col-span-4 bg-nle-surface border border-nle-border rounded-xl p-3 flex flex-col overflow-hidden">
          {/* Code Tabs */}
          <div className="flex items-center justify-between pb-2 border-b border-nle-border shrink-0">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveCodeTab("html")}
                className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1 transition-all ${
                  activeCodeTab === "html"
                    ? "bg-nle-panel text-nle-cyan border border-nle-cyan/30 shadow-sm"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <Code className="w-3.5 h-3.5 text-rose-400" />
                <span>HTML Structure</span>
              </button>

              <button
                onClick={() => setActiveCodeTab("css")}
                className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1 transition-all ${
                  activeCodeTab === "css"
                    ? "bg-nle-panel text-nle-cyan border border-nle-cyan/30 shadow-sm"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-nle-cyan" />
                <span>CSS Styling</span>
              </button>
            </div>

            <button
              onClick={() => {
                navigator.clipboard.writeText(activeCodeTab === "html" ? htmlCode : cssCode);
                setStatusMessage(`Đã sao chép mã ${activeCodeTab.toUpperCase()} vào bộ nhớ tạm!`);
              }}
              className="p-1 rounded text-gray-400 hover:text-white hover:bg-nle-panel transition-colors"
              title="Sao chép mã nguồn"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Textarea Editor */}
          <div className="flex-1 my-2 overflow-hidden flex flex-col">
            {activeCodeTab === "html" ? (
              <textarea
                value={htmlCode}
                onChange={(e) => setHtmlCode(e.target.value)}
                spellCheck={false}
                className="w-full h-full p-3 font-mono text-xs bg-nle-base text-gray-200 border border-nle-border rounded-lg resize-none outline-none focus:border-nle-cyan/50 leading-relaxed"
                placeholder="Nhập mã HTML của slide..."
              />
            ) : (
              <textarea
                value={cssCode}
                onChange={(e) => setCssCode(e.target.value)}
                spellCheck={false}
                className="w-full h-full p-3 font-mono text-xs bg-nle-base text-gray-200 border border-nle-border rounded-lg resize-none outline-none focus:border-nle-cyan/50 leading-relaxed"
                placeholder="Nhập mã CSS của slide..."
              />
            )}
          </div>

          <div className="text-[10px] text-gray-500 pt-1 shrink-0">
            Hỗ trợ CSS Flexbox, Grid, Linear/Radial Gradients, Box Shadow, Backdrop Blur.
          </div>
        </div>
      </div>
    </div>
  );
}
