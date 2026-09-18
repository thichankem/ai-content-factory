/**
 * Co-Pilot command bar hook.
 *
 * A natural-language instruction is applied to the timeline **server-side**: the
 * client sends the current :interface:`VideoProject` and the text, and the backend
 * returns the parsed command plus the edited project. The studio never guesses
 * what an instruction meant, so the timeline it shows always matches the edit the
 * pipeline would make.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { timelineApi } from "@/lib/api";
import { invalidateTimeline } from "@/lib/projectSync";
import { queryKeys } from "@/lib/queryKeys";
import { VideoProject } from "@/types/timeline";

export function useTimelineCommands(projectId?: string) {
  const queryClient = useQueryClient();

  const commandMutation = useMutation({
    mutationFn: ({
      command,
      videoProject,
    }: {
      command: string;
      videoProject: VideoProject;
    }) => timelineApi.runTimelineCommand({ command, project: videoProject }),
    onSuccess: (result) => {
      if (projectId) {
        queryClient.setQueryData(queryKeys.videoProject(projectId), result.project);
        invalidateTimeline(queryClient, projectId);
      }
    },
  });

  return { commandMutation };
}