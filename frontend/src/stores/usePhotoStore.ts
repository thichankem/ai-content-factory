import { create } from "zustand";

export interface PhotoLayer {
  id: string;
  name: string;
  type: "image" | "text" | "sticker" | "adjustment";
  visible: boolean;
  opacity: number;
  blendMode: "normal" | "multiply" | "screen" | "overlay";
  content?: string;
}

export type AspectPreset = "9:16" | "16:9" | "1:1" | "4:5";

interface PhotoStore {
  activeImageUrl: string;
  aspectRatio: AspectPreset;
  brightness: number; // -100 to 100
  contrast: number; // -100 to 100
  saturation: number; // -100 to 100
  exposure: number; // -100 to 100
  vibrance: number; // -100 to 100
  temperature: number; // -100 to 100
  vignette: number; // 0 to 100
  blur: number; // 0 to 50
  selectedLayerId: string;
  layers: PhotoLayer[];
  isAiProcessing: boolean;
  aiStatus: string | null;

  setAspectRatio: (ratio: AspectPreset) => void;
  setActiveImageUrl: (url: string) => void;
  setAdjustment: (key: string, value: number) => void;
  resetAdjustments: () => void;
  toggleLayerVisibility: (id: string) => void;
  setSelectedLayerId: (id: string) => void;
  addLayer: (layer: PhotoLayer) => void;
  setAiProcessing: (loading: boolean, status?: string | null) => void;
}

const DEFAULT_LAYERS: PhotoLayer[] = [
  { id: "layer-text", name: "Text Title Hook", type: "text", visible: true, opacity: 1, blendMode: "normal", content: "BÍ MẬT 3 GIÂY ĐẦU" },
  { id: "layer-sticker", name: "Glow Arrow Sticker", type: "sticker", visible: true, opacity: 0.9, blendMode: "screen", content: "⚡" },
  { id: "layer-adj", name: "Cyber Vignette FX", type: "adjustment", visible: true, opacity: 0.7, blendMode: "multiply" },
  { id: "layer-base", name: "Base Frame Canvas", type: "image", visible: true, opacity: 1, blendMode: "normal" },
];

export const usePhotoStore = create<PhotoStore>((set) => ({
  activeImageUrl: "/placeholder_frame.jpg",
  aspectRatio: "9:16",
  brightness: 10,
  contrast: 25,
  saturation: 20,
  exposure: 5,
  vibrance: 15,
  temperature: 5,
  vignette: 30,
  blur: 0,
  selectedLayerId: "layer-text",
  layers: DEFAULT_LAYERS,
  isAiProcessing: false,
  aiStatus: null,

  setAspectRatio: (aspectRatio) => set({ aspectRatio }),
  setActiveImageUrl: (activeImageUrl) => set({ activeImageUrl }),
  setAdjustment: (key, value) => set((state) => ({ ...state, [key]: value })),
  resetAdjustments: () =>
    set({
      brightness: 0,
      contrast: 0,
      saturation: 0,
      exposure: 0,
      vibrance: 0,
      temperature: 0,
      vignette: 0,
      blur: 0,
    }),
  toggleLayerVisibility: (id) =>
    set((state) => ({
      layers: state.layers.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)),
    })),
  setSelectedLayerId: (id) => set({ selectedLayerId: id }),
  addLayer: (layer) => set((state) => ({ layers: [layer, ...state.layers] })),
  setAiProcessing: (isAiProcessing, aiStatus = null) => set({ isAiProcessing, aiStatus }),
}));
