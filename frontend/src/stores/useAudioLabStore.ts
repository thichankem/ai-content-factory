import { create } from "zustand";

export interface EQBand {
  id: string;
  freqLabel: string;
  freqHz: number;
  gainDb: number; // -12dB to +12dB
  q: number;
}

export interface AudioChannelState {
  volume: number; // 0 to 100
  pan: number; // -50 (L) to +50 (R)
  muted: boolean;
  solo: boolean;
}

interface AudioLabStore {
  // Multi-track Mixer
  channels: {
    voiceover: AudioChannelState;
    bgm: AudioChannelState;
    sfx: AudioChannelState;
    ambient: AudioChannelState;
  };

  // 5-Band Parametric EQ
  eqBands: EQBand[];

  // Sidechain Auto-Ducking
  duckingEnabled: boolean;
  duckingReductionDb: number; // -30 to -3dB
  duckingAttackMs: number; // 5 to 50ms
  duckingReleaseMs: number; // 50 to 600ms
  duckingThreshold: number; // -40 to -10dB

  // Neural Voiceover TTS
  voiceId: string;
  ttsSpeed: number; // -50 to +50%
  ttsPitch: number; // -50 to +50%
  ttsEmotion: "neutral" | "dramatic" | "excited" | "storytelling";
  ttsScriptDraft: string;

  // AI Audio Harness
  isAiProcessing: boolean;
  aiAudioStatus: string | null;

  setChannelVolume: (ch: "voiceover" | "bgm" | "sfx" | "ambient", vol: number) => void;
  setChannelPan: (ch: "voiceover" | "bgm" | "sfx" | "ambient", pan: number) => void;
  toggleChannelMute: (ch: "voiceover" | "bgm" | "sfx" | "ambient") => void;
  toggleChannelSolo: (ch: "voiceover" | "bgm" | "sfx" | "ambient") => void;
  setEQBandGain: (bandId: string, gain: number) => void;
  resetEQ: () => void;
  setDuckingParam: (key: string, val: any) => void;
  setVoiceSettings: (key: string, val: any) => void;
  setAiAudioProcessing: (loading: boolean, status?: string | null) => void;
}

const DEFAULT_EQ_BANDS: EQBand[] = [
  { id: "sub", freqLabel: "60 Hz", freqHz: 60, gainDb: -1.5, q: 1.0 },
  { id: "low", freqLabel: "250 Hz", freqHz: 250, gainDb: -2.0, q: 1.2 },
  { id: "mid", freqLabel: "1 kHz", freqHz: 1000, gainDb: 1.0, q: 1.0 },
  { id: "high_mid", freqLabel: "4 kHz", freqHz: 4000, gainDb: 3.5, q: 1.4 },
  { id: "presence", freqLabel: "12 kHz", freqHz: 12000, gainDb: 2.0, q: 1.0 },
];

export const useAudioLabStore = create<AudioLabStore>((set) => ({
  channels: {
    voiceover: { volume: 92, pan: 0, muted: false, solo: false },
    bgm: { volume: 38, pan: 0, muted: false, solo: false },
    sfx: { volume: 65, pan: -10, muted: false, solo: false },
    ambient: { volume: 25, pan: 15, muted: false, solo: false },
  },

  eqBands: DEFAULT_EQ_BANDS,

  duckingEnabled: true,
  duckingReductionDb: -16,
  duckingAttackMs: 15,
  duckingReleaseMs: 250,
  duckingThreshold: -24,

  voiceId: "vi-VN-HoaiMyNeural",
  ttsSpeed: 5,
  ttsPitch: 0,
  ttsEmotion: "dramatic",
  ttsScriptDraft: "90% video ngắn thất bại ngay trong 3 giây đầu tiên vì thiếu một chiếc Hook giữ chân đầy kịch tính.",

  isAiProcessing: false,
  aiAudioStatus: null,

  setChannelVolume: (ch, vol) =>
    set((state) => ({
      channels: {
        ...state.channels,
        [ch]: { ...state.channels[ch], volume: vol },
      },
    })),
  setChannelPan: (ch, pan) =>
    set((state) => ({
      channels: {
        ...state.channels,
        [ch]: { ...state.channels[ch], pan },
      },
    })),
  toggleChannelMute: (ch) =>
    set((state) => ({
      channels: {
        ...state.channels,
        [ch]: { ...state.channels[ch], muted: !state.channels[ch].muted },
      },
    })),
  toggleChannelSolo: (ch) =>
    set((state) => ({
      channels: {
        ...state.channels,
        [ch]: { ...state.channels[ch], solo: !state.channels[ch].solo },
      },
    })),
  setEQBandGain: (bandId, gain) =>
    set((state) => ({
      eqBands: state.eqBands.map((b) => (b.id === bandId ? { ...b, gainDb: gain } : b)),
    })),
  resetEQ: () => set({ eqBands: DEFAULT_EQ_BANDS.map((b) => ({ ...b, gainDb: 0 })) }),
  setDuckingParam: (key, val) => set((state) => ({ ...state, [key]: val })),
  setVoiceSettings: (key, val) => set((state) => ({ ...state, [key]: val })),
  setAiAudioProcessing: (isAiProcessing, aiAudioStatus = null) =>
    set({ isAiProcessing, aiAudioStatus }),
}));
