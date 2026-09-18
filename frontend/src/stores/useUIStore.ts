import { create } from "zustand";

export type ActiveStudioTab =
  | "script"
  | "assets"
  | "photo"
  | "video_fx"
  | "audio"
  | "timeline"
  | "export"
  | "workflow"
  | "campaign"
  // Legacy aliases
  | "video"
  | "media";

export type TimelineTool =
  | "select"
  | "trackSelect"
  | "ripple"
  | "razor"
  | "slip"
  | "pen"
  | "hand"
  | "type";

export type MonitorTab = "program" | "source" | "scopes";

interface UIStore {
  activeTab: ActiveStudioTab;
  activeTool: TimelineTool;
  activeMonitorTab: MonitorTab;
  completedSteps: Record<string, boolean>;
  sidebarCollapsed: boolean;
  isCommandBarOpen: boolean;
  isQAModalOpen: boolean;
  isThumbnailModalOpen: boolean;
  isAuditModalOpen: boolean;
  isNewProjectModalOpen: boolean;
  isIngestionModalOpen: boolean;
  isAgentBridgeModalOpen: boolean;
  isSeoModalOpen: boolean;
  setActiveTab: (tab: ActiveStudioTab) => void;
  setActiveTool: (tool: TimelineTool) => void;
  setActiveMonitorTab: (tab: MonitorTab) => void;
  toggleStepCompleted: (stepId: string) => void;
  toggleSidebar: () => void;
  setCommandBarOpen: (open: boolean) => void;
  setQAModalOpen: (open: boolean) => void;
  setThumbnailModalOpen: (open: boolean) => void;
  setAuditModalOpen: (open: boolean) => void;
  setNewProjectModalOpen: (open: boolean) => void;
  setIngestionModalOpen: (open: boolean) => void;
  setAgentBridgeModalOpen: (open: boolean) => void;
  setSeoModalOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  activeTab: "script",
  activeTool: "select",
  activeMonitorTab: "program",
  completedSteps: {
    script: true,
    assets: false,
    photo: false,
    video_fx: false,
    audio: false,
    timeline: false,
    export: false,
  },
  sidebarCollapsed: false,
  isCommandBarOpen: false,
  isQAModalOpen: false,
  isThumbnailModalOpen: false,
  isAuditModalOpen: false,
  isNewProjectModalOpen: false,
  isIngestionModalOpen: false,
  isAgentBridgeModalOpen: false,
  isSeoModalOpen: false,
  setActiveTab: (tab) =>
    set({
      activeTab: tab === "video" ? "timeline" : tab === "media" ? "assets" : tab,
    }),
  setActiveTool: (tool) => set({ activeTool: tool }),
  setActiveMonitorTab: (tab) => set({ activeMonitorTab: tab }),
  toggleStepCompleted: (stepId) =>
    set((state) => ({
      completedSteps: {
        ...state.completedSteps,
        [stepId]: !state.completedSteps[stepId],
      },
    })),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setCommandBarOpen: (open) => set({ isCommandBarOpen: open }),
  setQAModalOpen: (open) => set({ isQAModalOpen: open }),
  setThumbnailModalOpen: (open) => set({ isThumbnailModalOpen: open }),
  setAuditModalOpen: (open) => set({ isAuditModalOpen: open }),
  setNewProjectModalOpen: (open) => set({ isNewProjectModalOpen: open }),
  setIngestionModalOpen: (open) => set({ isIngestionModalOpen: open }),
  setAgentBridgeModalOpen: (open) => set({ isAgentBridgeModalOpen: open }),
  setSeoModalOpen: (open) => set({ isSeoModalOpen: open }),
}));

