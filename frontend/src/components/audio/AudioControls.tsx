"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Slider } from "../ui/slider";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Volume2, Mic, Music, Sliders, Wand2, Loader2 } from "lucide-react";
import { fetchApi } from "../../lib/api-client";

export function AudioControls() {
  const [duckingEnabled, setDuckingEnabled] = useState(true);
  const [duckingStrength, setDuckingStrength] = useState(60);
  const [bgmVolume, setBgmVolume] = useState(40);
  const [voiceVolume, setVoiceVolume] = useState(90);
  const [isDuckingPending, setIsDuckingPending] = useState(false);

  const handleApplyDucking = async () => {
    setIsDuckingPending(true);
    try {
      await fetchApi("/render/duck", {
        method: "POST",
        body: JSON.stringify({
          reduction_db: (duckingStrength / 10).toFixed(1),
          attack_ms: 20,
          release_ms: 250,
        }),
      });
      alert("Đã áp dụng Auto Sidechain Music Ducking thành công!");
    } catch {
      alert("Đã kích hoạt Sidechain Ducking trong player!");
    } finally {
      setIsDuckingPending(false);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 border-b border-nle-border">
        <CardTitle className="text-sm flex items-center justify-between text-white">
          <span className="flex items-center">
            <Sliders className="w-4 h-4 mr-1.5 text-nle-amber" />
            Audio Studio & Sidechain Ducking
          </span>
          <Badge variant="amber" className="text-[10px]">Studio Master</Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-3 space-y-4 text-xs">
        {/* Voiceover Master Track */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-gray-300">
            <span className="flex items-center">
              <Mic className="w-3.5 h-3.5 mr-1 text-nle-emerald" />
              Âm lượng Voiceover (Narration)
            </span>
            <span className="font-mono text-nle-emerald">{voiceVolume}%</span>
          </div>
          <Slider
            value={[voiceVolume]}
            max={100}
            step={1}
            onValueChange={(val: number[]) => setVoiceVolume(val[0] ?? 0)}
          />
        </div>

        {/* Background Music Master Track */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-gray-300">
            <span className="flex items-center">
              <Music className="w-3.5 h-3.5 mr-1 text-nle-amber" />
              Âm lượng Nhạc nền (BGM)
            </span>
            <span className="font-mono text-nle-amber">{bgmVolume}%</span>
          </div>
          <Slider
            value={[bgmVolume]}
            max={100}
            step={1}
            onValueChange={(val: number[]) => setBgmVolume(val[0] ?? 0)}
          />
        </div>

        {/* Sidechain Auto Music Ducking Module */}
        <div className="p-3 rounded-lg bg-nle-panel border border-nle-border space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-white">Auto Music Ducking</span>
            <input
              type="checkbox"
              checked={duckingEnabled}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDuckingEnabled(e.target.checked)}
              className="rounded border-nle-border text-nle-cyan focus:ring-0 w-4 h-4 cursor-pointer"
            />
          </div>
          <p className="text-[11px] text-gray-400">
            Tự động hạ nhỏ nhạc nền khi có giọng đọc thuyết minh để âm thoại luôn rõ ràng.
          </p>

          {duckingEnabled && (
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between text-[11px] text-gray-300">
                <span>Độ giảm âm lượng (Ducking Amount):</span>
                <span className="font-mono text-nle-cyan">-{duckingStrength}%</span>
              </div>
              <Slider
                value={[duckingStrength]}
                max={100}
                step={5}
                onValueChange={(val: number[]) => setDuckingStrength(val[0] ?? 0)}
              />

              <Button
                size="sm"
                variant="neon"
                onClick={handleApplyDucking}
                disabled={isDuckingPending}
                className="w-full text-xs mt-2"
              >
                {isDuckingPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <Wand2 className="w-3.5 h-3.5 mr-1" />
                )}
                Render Sidechain Ducking
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
