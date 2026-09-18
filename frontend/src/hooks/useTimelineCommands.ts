import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { NLCommandResult } from "../types/api";
import { VideoProject } from "../types/project";
import { useTimelineStore } from "../stores/useTimelineStore";

export function useTimelineCommands() {
  const { setScenes } = useTimelineStore();

  const commandMutation = useMutation({
    mutationFn: ({ command, videoProject }: { command: string; videoProject: VideoProject }) =>
      fetchApi<NLCommandResult>("/timeline/command", {
        method: "POST",
        body: JSON.stringify({ command, project: videoProject }),
      }),
    onSuccess: (result) => {
      if (result.project && result.project.scenes) {
        setScenes(result.project.scenes);
      }
    },
  });

  return { commandMutation };
}
