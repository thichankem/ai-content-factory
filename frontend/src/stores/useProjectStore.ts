/**
 * The selected project and the project list.
 *
 * The store holds the *selection*; server state lives in TanStack Query and is
 * written here by :func:`@/lib/projectSync.syncProject`. Keeping the two in one
 * place is what stops a screen from reading a project the cache has since
 * replaced.
 *
 * ``script`` (raw narration text) and ``script_document`` (the structured bundle
 * an editor binds to) are both written by :meth:`setScriptContent`, because the
 * backend derives one from the other and a client that updates only one leaves
 * the two describing different scripts.
 */

import { create } from "zustand";

import { ProjectStatus } from "@/types/common";
import { Project } from "@/types/project";
import { ScriptDocument } from "@/types/script";

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

/** The bundle an editor edits, derived from a raw script. */
function scriptDocument(rawScript: string, previous?: ScriptDocument | null): ScriptDocument {
  return {
    topic: previous?.topic ?? "",
    style: previous?.style ?? "viral-short",
    raw_script: rawScript,
    sections: previous?.sections ?? [],
    timing_plan: previous?.timing_plan ?? null,
    language: previous?.language ?? "vi",
    target_seconds: previous?.target_seconds ?? 0,
    estimated_seconds: previous?.estimated_seconds ?? 0,
  };
}

/** A local draft project, used when no project has been selected yet. */
function draftProject(rawScript: string, previous?: Project | null): Project {
  const now = new Date().toISOString();
  return {
    ...(previous ?? {}),
    id: previous?.id ?? `draft-${Date.now()}`,
    name: previous?.name ?? "Untitled production",
    topic: previous?.topic ?? "",
    target_language: previous?.target_language ?? "vi",
    duration_target_seconds: previous?.duration_target_seconds ?? 30,
    status: previous?.status ?? "draft",
    source_rights_confirmed: previous?.source_rights_confirmed ?? false,
    approvals: previous?.approvals ?? [],
    platforms: previous?.platforms ?? [],
    documents: previous?.documents ?? [],
    script_style: previous?.script_style ?? "viral-short",
    script_issues: previous?.script_issues ?? [],
    external_assets: previous?.external_assets ?? [],
    created_at: previous?.created_at ?? now,
    updated_at: now,
    script: rawScript,
    script_document: scriptDocument(rawScript, previous?.script_document),
  };
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
      currentProject: draftProject(rawScript, state.currentProject),
    })),
}));
