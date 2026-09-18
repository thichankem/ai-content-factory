import { create } from "zustand";
import { Project, ProjectStatus } from "../types/project";

interface ProjectStore {
  currentProject: Project | null;
  projects: Project[];
  isLoading: boolean;
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  setLoading: (loading: boolean) => void;
  updateProjectStatus: (status: ProjectStatus) => void;
  confirmSourceRights: () => void;
  setScriptContent: (rawScript: string) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  currentProject: null,
  projects: [],
  isLoading: false,
  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  setLoading: (loading) => set({ isLoading: loading }),
  updateProjectStatus: (status) =>
    set((state) => ({
      currentProject: state.currentProject
        ? { ...state.currentProject, status }
        : null,
    })),
  confirmSourceRights: () =>
    set((state) => ({
      currentProject: state.currentProject
        ? { ...state.currentProject, source_rights_confirmed: true }
        : null,
    })),
  setScriptContent: (rawScript) =>
    set((state) => ({
      currentProject: state.currentProject
        ? {
            ...state.currentProject,
            script: {
              topic: state.currentProject.topic || "Re-Cooked Project",
              style: state.currentProject.script?.style || "retention_fast",
              raw_script: rawScript,
              sections: state.currentProject.script?.sections || [],
            },
          }
        : {
            id: "recook-proj-" + Date.now(),
            name: "Re-Cooked Project",
            topic: "Re-Cooked Project",
            target_language: "vi",
            duration_target_seconds: 30,
            status: "draft" as ProjectStatus,
            source_rights_confirmed: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            script: {
              topic: "Re-Cooked Project",
              style: "retention_fast",
              raw_script: rawScript,
              sections: [],
            },
          },
    })),
}));
