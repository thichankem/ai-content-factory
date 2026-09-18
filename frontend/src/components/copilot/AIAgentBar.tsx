"use client";

import React, { useState } from "react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Input } from "../ui/input";
import {
  Bot,
  Sparkles,
  Zap,
  Wand2,
  Cpu,
  Loader2,
  ArrowRight,
  ChevronDown,
} from "lucide-react";

export interface AIQuickAction {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  onClick: () => Promise<void> | void;
  variant?: "default" | "outline" | "neon";
}

interface AIAgentBarProps {
  tabTitle: string;
  agentRole: string; // e.g. "Scriptwriting Director", "Vision & Photo Retoucher", "Motion FX Artist"
  promptPlaceholder: string;
  quickActions: AIQuickAction[];
  onPromptSubmit?: (prompt: string) => Promise<void> | void;
  statusMessage?: string | null;
  isProcessing?: boolean;
}

export function AIAgentBar({
  tabTitle,
  agentRole,
  promptPlaceholder,
  quickActions,
  onPromptSubmit,
  statusMessage,
  isProcessing = false,
}: AIAgentBarProps) {
  const [prompt, setPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("Gemini 2.5 Flash + Antigravity Vision");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isProcessing) return;
    if (onPromptSubmit) {
      await onPromptSubmit(prompt);
      setPrompt("");
    }
  };

  return (
    <div className="bg-gradient-to-r from-nle-panel via-nle-surface to-nle-panel border border-nle-cyan/30 rounded-xl p-3 shadow-lg shadow-nle-cyan/5 space-y-2.5">
      {/* Header: AI Agent Role & External Harness Status */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-nle-cyan/20 border border-nle-cyan/40 flex items-center justify-center text-nle-cyan shadow-sm shadow-nle-cyan/20">
            <Bot className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-1.5">
              <span className="text-xs font-bold text-white tracking-wide">
                AI AGENT CO-PILOT: <span className="text-nle-cyan">{agentRole}</span>
              </span>
              <Badge variant="cyan" className="text-[9px] uppercase px-1.5 py-0 font-mono">
                Harness Active
              </Badge>
            </div>
            <span className="text-[10px] text-gray-400">
              Đồng hành tự động hóa mọi tác vụ cho tab: <b className="text-gray-200">{tabTitle}</b>
            </span>
          </div>
        </div>

        {/* Model Selector & External Cloud Harness Indicator */}
        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center space-x-1 px-2 py-1 rounded bg-black/40 border border-nle-border text-[11px] text-gray-300">
            <Cpu className="w-3.5 h-3.5 text-nle-violet" />
            <span>{selectedModel}</span>
          </div>
          <div className="hidden sm:flex items-center space-x-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
            <Zap className="w-3 h-3" />
            <span>Kling 1.5 • ElevenLabs • Whisper • RemBg</span>
          </div>
        </div>
      </div>

      {/* Main Row: 1-Click Autonomous Quick Actions */}
      <div className="flex flex-wrap items-center gap-2 pt-0.5">
        <span className="text-[11px] font-semibold text-gray-400 flex items-center">
          <Sparkles className="w-3 h-3 mr-1 text-nle-cyan" />
          1-Click AI:
        </span>

        {quickActions.map((action) => {
          const Icon = action.icon || Wand2;
          return (
            <Button
              key={action.id}
              size="sm"
              variant={action.variant || "outline"}
              onClick={action.onClick}
              disabled={isProcessing}
              className="text-xs h-7 px-2.5 border-nle-cyan/30 text-gray-200 hover:text-white hover:bg-nle-cyan/10"
            >
              {isProcessing ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Icon className="w-3 h-3 mr-1 text-nle-cyan" />
              )}
              {action.label}
            </Button>
          );
        })}
      </div>

      {/* Prompt Command Bar: Prompt to Auto-Generate / Auto-Edit */}
      {onPromptSubmit && (
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <Input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={promptPlaceholder}
            disabled={isProcessing}
            className="text-xs h-8 pl-3 pr-20 bg-nle-base/80 border-nle-border focus:border-nle-cyan text-gray-100 placeholder:text-gray-500 rounded-lg"
          />
          <Button
            type="submit"
            size="sm"
            variant="neon"
            disabled={!prompt.trim() || isProcessing}
            className="absolute right-1 h-6 px-2 text-[11px] font-medium"
          >
            {isProcessing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <>
                <span>Thực thi</span>
                <ArrowRight className="w-3 h-3 ml-1" />
              </>
            )}
          </Button>
        </form>
      )}

      {/* Live AI Status Message if active */}
      {statusMessage && (
        <div className="px-2.5 py-1.5 rounded-md bg-nle-cyan/10 border border-nle-cyan/20 text-[11px] text-nle-cyan flex items-center justify-between animate-fade-in">
          <span className="flex items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-nle-cyan mr-2 animate-pulse" />
            {statusMessage}
          </span>
          <span className="text-[10px] text-gray-400 font-mono">Realtime Harness</span>
        </div>
      )}
    </div>
  );
}
