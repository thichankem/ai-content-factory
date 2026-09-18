import { create } from "zustand";
import { Scene } from "@/types/project";
import { TimelineTrack } from "@/types/timeline";

interface TimelineStore {
  selectedSceneIndex: number | null;
  zoom: number;
  tracks: TimelineTrack[];
  scenes: Scene[];
  setSelectedSceneIndex: (index: number | null) => void;
  setZoom: (zoom: number) => void;
  setScenes: (scenes: Scene[]) => void;
  updateScene: (index: number, partial: Partial<Scene>) => void;
}

const DEFAULT_TRACKS: TimelineTrack[] = [
  { id: "v1", name: "V1 • Video Main", type: "video", color: "#00f0ff" },
  { id: "v2", name: "V2 • B-Roll & Overlay", type: "video", color: "#8b5cf6" },
  { id: "a1", name: "A1 • Voiceover Narration", type: "voice", color: "#10b981" },
  { id: "a2", name: "A2 • Background Music", type: "audio", color: "#f59e0b" },
  { id: "c1", name: "C1 • Subtitle Captions", type: "caption", color: "#ec4899" },
];

export const useTimelineStore = create<TimelineStore>((set) => ({
  selectedSceneIndex: 0,
  zoom: 1,
  tracks: DEFAULT_TRACKS,
  scenes: [],
  setSelectedSceneIndex: (index) => set({ selectedSceneIndex: index }),
  setZoom: (zoom) => set({ zoom: Math.max(0.5, Math.min(3, zoom)) }),
  setScenes: (scenes) => set({ scenes }),
  updateScene: (index, partial) =>
    set((state) => {
      const updated = [...state.scenes];
      if (updated[index]) {
        updated[index] = { ...updated[index], ...partial };
      }
      return { scenes: updated };
    }),
}));
