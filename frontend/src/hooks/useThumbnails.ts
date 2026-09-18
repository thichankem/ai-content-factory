import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { ThumbnailCandidate } from "../types/api";

export function useThumbnails() {
  const generateThumbnailsMutation = useMutation({
    mutationFn: ({
      mediaPath,
      topic,
      style,
      count,
    }: {
      mediaPath?: string;
      topic: string;
      style: string;
      count?: number;
    }) =>
      fetchApi<{ candidates: ThumbnailCandidate[] }>("/thumbnail/generate", {
        method: "POST",
        body: JSON.stringify({
          media_path: mediaPath,
          topic,
          style,
          count: count || 3,
        }),
      }),
  });

  return { generateThumbnailsMutation };
}
