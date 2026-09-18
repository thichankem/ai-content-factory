/**
 * Thumbnail candidate hook.
 *
 * A request that resolves to no source video is **not** an error: the backend
 * answers with an empty list plus ``empty_reason``, and the studio shows that
 * reason. Only a transport/HTTP failure throws, so the caller can tell "nothing
 * to draw from yet" apart from "the call failed".
 *
 * Known gap: candidates are written to the *backend's* temp directory and no route
 * serves them, so the UI can show the measurements but not the images yet. See
 * ``frontend/README.md`` → "Known gaps".
 */

import { useMutation } from "@tanstack/react-query";

import { qaApi } from "@/lib/api";
import { ThumbnailCandidate, ThumbnailRequest } from "@/types/qa";

export interface ThumbnailOutcome {
  candidates: ThumbnailCandidate[];
  count: number;
  /** Why the list is empty, when it is. */
  emptyReason: string | null;
}

export function useThumbnails() {
  const generateThumbnailsMutation = useMutation({
    mutationFn: async (req: ThumbnailRequest): Promise<ThumbnailOutcome> => {
      const response = await qaApi.thumbnailCandidates(req);
      return {
        candidates: response.candidates ?? [],
        count: response.count ?? 0,
        emptyReason: response.emptyReason ?? response.empty_reason ?? null,
      };
    },
  });

  return { generateThumbnailsMutation };
}