import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { ThumbnailCandidate } from "../types/api";

/**
 * Thumbnail candidates.
 *
 * `/thumbnail/candidates` wraps the same list `/thumbnail/generate` returns, for
 * clients that want a `{candidates}` envelope. The source is resolved on the
 * backend in the order media id -> media path -> project -> newest video, so a
 * caller that only knows the project can still ask; `emptyReason` is returned
 * when nothing was drawable rather than the call failing.
 */
export function useThumbnails(projectId?: string) {
  const generateThumbnailsMutation = useMutation({
    mutationFn: ({
      mediaId,
      mediaPath,
      topic,
      style,
      count,
    }: {
      mediaId?: string;
      mediaPath?: string;
      topic: string;
      style: string;
      count?: number;
    }) =>
      fetchApi<{
        candidates: ThumbnailCandidate[];
        count: number;
        emptyReason?: string;
      }>("/thumbnail/candidates", {
        method: "POST",
        body: JSON.stringify({
          media_id: mediaId,
          media_path: mediaPath,
          project_id: projectId,
          topic,
          style,
          count: count || 3,
        }),
      }).then((res) => {
        if (res.candidates?.length) return res;
        throw new Error(
          res.emptyReason ??
            "No source video to draw thumbnails from — upload a video first."
        );
      }),
  });

  return { generateThumbnailsMutation };
}
