import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { Project } from "../types/project";
import { useProjectStore } from "../stores/useProjectStore";

export function useProjects() {
  const queryClient = useQueryClient();
  const { setCurrentProject, setProjects } = useProjectStore();

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const data = await fetchApi<Project[]>("/projects");
      setProjects(data);
      return data;
    },
  });

  const createProjectMutation = useMutation({
    mutationFn: (newProject: {
      name: string;
      topic: string;
      target_language: string;
      duration_target_seconds: number;
    }) =>
      fetchApi<Project>("/projects", {
        method: "POST",
        body: JSON.stringify(newProject),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCurrentProject(project);
    },
  });

  const approveScriptMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/approvals`, {
        method: "POST",
        body: JSON.stringify({ stage: "script", verdict: "approved" }),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const generateVideoMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/generate`, {
        method: "POST",
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const approveVideoMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/approvals`, {
        method: "POST",
        body: JSON.stringify({ stage: "video", verdict: "approved" }),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const publishMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/publish`, {
        method: "POST",
        body: JSON.stringify({ destinations: ["youtube", "tiktok"] }),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const voiceoverMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/voiceover/generate`, {
        method: "POST",
        body: JSON.stringify({ engine: "edge", rate: "+0%" }),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const aiAssistMutation = useMutation({
    mutationFn: (projectId: string) =>
      fetchApi<Project>(`/projects/${projectId}/video-project/ai-assist`, {
        method: "POST",
        body: JSON.stringify({ fit: true, beat: true, bpm: 120 }),
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  const polishSceneMutation = useMutation({
    mutationFn: ({ projectId, sceneId }: { projectId: string; sceneId: string }) =>
      fetchApi<Project>(`/projects/${projectId}/video-project/scenes/${sceneId}/polish`, {
        method: "POST",
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
      setCurrentProject(project);
    },
  });

  return {
    projectsQuery,
    createProjectMutation,
    approveScriptMutation,
    generateVideoMutation,
    approveVideoMutation,
    publishMutation,
    voiceoverMutation,
    aiAssistMutation,
    polishSceneMutation,
  };
}
