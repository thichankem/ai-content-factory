/**
 * Project lifecycle hooks.
 *
 * Each mutation delegates to :mod:`@/lib/api/projects` for the request and to
 * :func:`syncProject` for the cache, so this file only decides *which* calls the
 * studio can make.
 *
 * The two review gates are separate mutations on purpose: the state machine
 * rejects a video approval that arrives before the script approval, and the UI
 * shows that error per gate rather than as a generic failure.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { projectsApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { syncProject } from "@/lib/projectSync";
import { useProjectStore } from "@/stores/useProjectStore";
import { ProjectCreate } from "@/types/project";

export function useProjects() {
  const queryClient = useQueryClient();
  const setProjects = useProjectStore((state) => state.setProjects);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: async () => {
      const projects = await projectsApi.listProjects();
      setProjects(projects);
      return projects;
    },
  });

  const createProjectMutation = useMutation({
    mutationFn: (payload: ProjectCreate) => projectsApi.createProject(payload),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const saveScriptMutation = useMutation({
    mutationFn: ({
      projectId,
      script,
      sourceRightsConfirmed,
    }: {
      projectId: string;
      script: string;
      sourceRightsConfirmed?: boolean;
    }) =>
      projectsApi.updateScript(projectId, {
        script,
        raw_script: script,
        source_rights_confirmed: sourceRightsConfirmed,
      }),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const generateScriptMutation = useMutation({
    mutationFn: (projectId: string) => projectsApi.generateScript(projectId),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const researchMutation = useMutation({
    mutationFn: ({ projectId, web = true }: { projectId: string; web?: boolean }) =>
      projectsApi.runResearch(projectId, web),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  /** Gate 1 — the script must be approved before any video is generated. */
  const approveScriptMutation = useMutation({
    mutationFn: (projectId: string) =>
      projectsApi.submitApproval(projectId, {
        stage: "script",
        verdict: "approved",
      }),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const generateVideoMutation = useMutation({
    mutationFn: (projectId: string) => projectsApi.startGeneration(projectId),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  /** Gate 2 — the final video must be approved before publishing. */
  const approveVideoMutation = useMutation({
    mutationFn: (projectId: string) =>
      projectsApi.submitApproval(projectId, {
        stage: "video",
        verdict: "approved",
      }),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const rejectVideoMutation = useMutation({
    mutationFn: ({ projectId, comment }: { projectId: string; comment?: string }) =>
      projectsApi.submitApproval(projectId, {
        stage: "video",
        verdict: "rejected",
        comment,
      }),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  /**
   * Publish to the approved platforms.
   *
   * ``platforms`` is required by the payload — the backend's field is
   * ``platforms`` (not ``destinations``), and omitting it publishes to the
   * default platform only.
   */
  const publishMutation = useMutation({
    mutationFn: ({
      projectId,
      platforms,
    }: {
      projectId: string;
      platforms: string[];
    }) => projectsApi.publishProject(projectId, { platforms }),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const voiceoverMutation = useMutation({
    mutationFn: (projectId: string) => projectsApi.generateVoiceover(projectId),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const renderMutation = useMutation({
    mutationFn: (projectId: string) => projectsApi.renderProject(projectId),
    onSuccess: (project) => syncProject(queryClient, project),
  });

  return {
    projectsQuery,
    createProjectMutation,
    saveScriptMutation,
    generateScriptMutation,
    researchMutation,
    approveScriptMutation,
    generateVideoMutation,
    approveVideoMutation,
    rejectVideoMutation,
    publishMutation,
    voiceoverMutation,
    renderMutation,
  };
}