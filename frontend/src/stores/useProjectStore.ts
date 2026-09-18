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
}));
