export interface TimelineTrack {
  id: string;
  name: string;
  type: "video" | "audio" | "voice" | "caption";
  color: string;
  muted?: boolean;
  locked?: boolean;
}

export interface TimelineClip {
  id: string;
  trackId: string;
  sceneIndex: number;
  label: string;
  start: number;
  duration: number;
  color?: string;
  speed?: number;
}

export interface Marker {
  id: string;
  time: number;
  label: string;
  color?: string;
}
