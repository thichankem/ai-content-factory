import { create } from "zustand";

interface PlayerStore {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  volume: number;
  isMuted: boolean;
  loop: boolean;
  safeZoneEnabled: boolean;
  vuLeft: number;
  vuRight: number;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  togglePlay: () => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  toggleLoop: () => void;
  toggleSafeZone: () => void;
  setVU: (left: number, right: number) => void;
}

export const usePlayerStore = create<PlayerStore>((set) => ({
  currentTime: 0,
  duration: 45,
  isPlaying: false,
  volume: 0.8,
  isMuted: false,
  loop: false,
  safeZoneEnabled: true,
  vuLeft: 0,
  vuRight: 0,
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setVolume: (volume) => set({ volume }),
  toggleMute: () => set((state) => ({ isMuted: !state.isMuted })),
  toggleLoop: () => set((state) => ({ loop: !state.loop })),
  toggleSafeZone: () => set((state) => ({ safeZoneEnabled: !state.safeZoneEnabled })),
  setVU: (left, right) => set({ vuLeft: left, vuRight: right }),
}));
