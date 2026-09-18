/**
 * Scripting hooks: presets, virality scoring, save and draft.
 *
 * The studio treats the *raw* script text as the editable artifact
 * (``project.script``) and the structured bundle (``project.script_document``) as
 * derived, which is exactly how the backend models it.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { scriptApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { syncProject } from "@/lib/projectSync";
import { ViralityRequest } from "@/types/qa";
import { ScriptStyle } from "@/types/script";

export function useScriptEngine(projectId?: string) {
  const queryClient = useQueryClient();

  const stylesQuery = useQuery({
    queryKey: queryKeys.scriptStyles,
    queryFn: () => scriptApi.listStyles(),
    staleTime: 1000 * 60 * 60,
  });

  const saveStyleMutation = useMutation({
    mutationFn: (style: ScriptStyle) => scriptApi.saveStyle(style),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.scriptStyles });
    },
  });

  const deleteStyleMutation = useMutation({
    mutationFn: (name: string) => scriptApi.deleteStyle(name),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.scriptStyles });
    },
  });

  const selectStyleMutation = useMutation({
    mutationFn: ({ style }: { style: string }) => {
      if (!projectId) throw new Error("No project selected");
      return scriptApi.selectScriptStyle(projectId, style);
    },
    onSuccess: (project) => syncProject(queryClient, project),
  });

  const analyzeScriptMutation = useMutation({
    mutationFn: (payload: { script?: string | null; style?: string | null } = {}) => {
      if (!projectId) throw new Error("No project selected");
      return scriptApi.analyzeScript(projectId, payload);
    },
  });

  const viralityMutation = useMutation({
    mutationFn: (payload: ViralityRequest) => scriptApi.scoreVirality(payload),
  });

  return {
    stylesQuery,
    saveStyleMutation,
    deleteStyleMutation,
    selectStyleMutation,
    analyzeScriptMutation,
    viralityMutation,
  };
}