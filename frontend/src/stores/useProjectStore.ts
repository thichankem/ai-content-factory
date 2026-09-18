/**
 * The selected project and the project list.
 *
 * The store holds the *selection*; server state lives in TanStack Query and is
 * written here by :func:`@/lib/projectSync.syncProject`. Keeping the two in one
 * place is what stops a screen from reading a project the cache has since
 * replaced.
 *
 * Three writers were removed because each could only ever describe a state the
 * server did not have:
 *
 * * ``confirmSourceRights`` flipped a boolean in this browser. The server's
 *   ``source_rights_confirmed`` is what Gate 1 checks, so the checkbox turned
 *   green while the backend still refused the approval — and the rejection was
 *   invisible, because the approval mutation's error was never rendered.
 *   Confirmation now travels through ``PUT /projects/{id}/script`` with
 *   ``sourceRightsConfirmed: true``; see
 *   :func:`@/hooks/useProjects.saveScriptMutation`.
 * * ``setScriptContent`` minted a ``draft-<timestamp>`` project around text that
 *   had never been saved, so the studio could render a script no server had ever
 *   seen, under an id no request would accept. Writing a script is a request now.
 * * ``updateProjectStatus`` set a status locally, which the next
 *   :func:`syncProject` silently overwrote.
 */

import { create } from "zustand";

import { Project } from "@/types/project";

interface ProjectStore {
  currentProject: Project | null;
  projects: Project[];
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  currentProject: null,
  projects: [],
  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
}));
