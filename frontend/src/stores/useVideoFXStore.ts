import { create } from "zustand";

export interface KeyframePoint {
  time: number; // 0 to 1
  value: number;
  handleInX?: number;
  handleInY?: number;
  handleOutX?: number;
  handleOutY?: number;
}

export interface SpeedRampPoint {
  t: number; // normalized time 0 to 1
  speed: number; // multiplier e.g. 0.2x, 1x, 4x
}

export type LUTPreset = "teal_orange" | "cyberpunk" | "noir" | "vintage" | "matrix" | "clean";

interface VideoFXStore {
  // Spatial Transform & Motion Dynamics
  posX: number;
  posY: number;
  scale: number;
  rotation: number;
  opacity: number;
  anchorX: number;
  anchorY: number;

  // Bezier Graph Editor
  selectedProperty: "scale" | "opacity" | "position" | "rotation";
  keyframes: Record<string, KeyframePoint[]>;

  // Dynamic Speed Ramping Velocity Curve
  speedRampPreset: "custom" | "hero_bullet" | "montage_fast" | "flash_in";
  speedPoints: SpeedRampPoint[];

  // Color Grading & 3D LUT Parameters
  lut: LUTPreset;
  colorTemp: number; // -100 to 100
  colorTint: number; // -100 to 100
  exposure: number; // -5 to 5
  contrast: number; // -100 to 100
  highlights: number; // -100 to 100
  shadows: number; // -100 to 100
  whites: number; // -100 to 100
  blacks: number; // -100 to 100
  colorSaturation: number; // 0 to 200

  // AI Video Ops
  isAiProcessing: boolean;
  aiVideoStatus: string | null;

  setTransform: (key: string, val: number) => void;
  setSelectedProperty: (prop: "scale" | "opacity" | "position" | "rotation") => void;
  updateKeyframe: (prop: string, index: number, point: Partial<KeyframePoint>) => void;
  setSpeedRampPreset: (preset: "custom" | "hero_bullet" | "montage_fast" | "flash_in") => void;
  updateSpeedPoint: (index: number, speed: number) => void;
  setLUT: (lut: LUTPreset) => void;
  setColorGrade: (key: string, val: number) => void;
  resetColorGrade: () => void;
  setAiVideoProcessing: (loading: boolean, status?: string | null) => void;
}

const DEFAULT_KEYFRAMES: Record<string, KeyframePoint[]> = {
  scale: [
    { time: 0.0, value: 1.0, handleOutX: 0.1, handleOutY: 1.2 },
    { time: 0.3, value: 1.25, handleInX: 0.2, handleInY: 1.25, handleOutX: 0.4, handleOutY: 1.1 },
    { time: 0.7, value: 0.95, handleInX: 0.6, handleInY: 0.95, handleOutX: 0.8, handleOutY: 1.0 },
    { time: 1.0, value: 1.0, handleInX: 0.9, handleInY: 1.0 },
  ],
  opacity: [
    { time: 0.0, value: 0.0 },
    { time: 0.15, value: 1.0 },
    { time: 0.85, value: 1.0 },
    { time: 1.0, value: 0.0 },
  ],
};

const DEFAULT_SPEED_RAMP: SpeedRampPoint[] = [
  { t: 0.0, speed: 1.0 },
  { t: 0.25, speed: 0.25 }, // Slow-mo dramatic hook
  { t: 0.6, speed: 3.5 },  // Fast forward payoff
  { t: 1.0, speed: 1.0 },
];

export const useVideoFXStore = create<VideoFXStore>((set) => ({
  posX: 0,
  posY: 0,
  scale: 100,
  rotation: 0,
  opacity: 100,
  anchorX: 50,
  anchorY: 50,

  selectedProperty: "scale",
  keyframes: DEFAULT_KEYFRAMES,

  speedRampPreset: "hero_bullet",
  speedPoints: DEFAULT_SPEED_RAMP,

  lut: "cyberpunk",
  colorTemp: 12,
  colorTint: -8,
  exposure: 0.2,
  contrast: 22,
  highlights: -15,
  shadows: 18,
  whites: 10,
  blacks: -8,
  colorSaturation: 115,

  isAiProcessing: false,
  aiVideoStatus: null,

  setTransform: (key, val) => set((state) => ({ ...state, [key]: val })),
  setSelectedProperty: (selectedProperty) => set({ selectedProperty }),
  updateKeyframe: (prop, index, point) =>
    set((state) => {
      const list = [...(state.keyframes[prop] || [])];
      if (list[index]) {
        list[index] = { ...list[index], ...point };
      }
      return { keyframes: { ...state.keyframes, [prop]: list } };
    }),
  setSpeedRampPreset: (preset) => {
    let pts = DEFAULT_SPEED_RAMP;
    if (preset === "montage_fast") {
      pts = [{ t: 0, speed: 2.0 }, { t: 0.5, speed: 4.0 }, { t: 1, speed: 1.5 }];
    } else if (preset === "flash_in") {
      pts = [{ t: 0, speed: 5.0 }, { t: 0.2, speed: 0.5 }, { t: 1, speed: 1.0 }];
    }
    set({ speedRampPreset: preset, speedPoints: pts });
  },
  updateSpeedPoint: (index, speed) =>
    set((state) => {
      const pts = [...state.speedPoints];
      if (pts[index]) {
        pts[index] = { ...pts[index], speed };
      }
      return { speedPoints: pts };
    }),
  setLUT: (lut) => set({ lut }),
  setColorGrade: (key, val) => set((state) => ({ ...state, [key]: val })),
  resetColorGrade: () =>
    set({
      lut: "clean",
      colorTemp: 0,
      colorTint: 0,
      exposure: 0,
      contrast: 0,
      highlights: 0,
      shadows: 0,
      whites: 0,
      blacks: 0,
      colorSaturation: 100,
    }),
  setAiVideoProcessing: (isAiProcessing, aiVideoStatus = null) =>
    set({ isAiProcessing, aiVideoStatus }),
}));
