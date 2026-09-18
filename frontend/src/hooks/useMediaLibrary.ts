/**
 * Media library hooks.
 *
 * The previous version returned a *function* that called ``useQuery`` when
 * invoked from render, which breaks the Rules of Hooks (a search box that
 * re-renders a different number of times would reorder hook calls). Search is now
 * its own hook, :func:`useMediaSearch`, taking the query as an argument.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { libraryApi, mediaApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import {
  DedupResult,
  MediaIngestUrlRequest,
  MediaItem,
  MediaSearchHit,
  ReCookRequest,
  ReCookResult,
} from "@/types/media";
import { LibraryResponse } from "@/types/library";

/** Every item in the library. */
export function useMediaItems() {
  const mediaQuery = useQuery({
    queryKey: queryKeys.mediaItems,
    queryFn: () => mediaApi.listMedia(),
  });
  return { mediaQuery };
}

/** Ranked search over transcripts and filenames; idle while the query is empty. */
export function useMediaSearch(query: string, topK = 10) {
  return useQuery<MediaSearchHit[]>({
    queryKey: queryKeys.mediaSearch(query),
    queryFn: () => mediaApi.searchMedia(query, topK),
    enabled: query.trim().length > 0,
  });
}

/** The local document corpus plus its counters. */
export function useMediaLibrary() {
  const libraryQuery = useQuery<LibraryResponse>({
    queryKey: queryKeys.library,
    queryFn: () => libraryApi.getLibrary(),
  });

  const dedupMutation = useMutation<DedupResult, Error>({
    mutationFn: () => mediaApi.findDuplicates(),
  });

  const uploadMutation = useMutation<MediaItem, Error, File>({
    mutationFn: (file: File) => mediaApi.uploadMedia(file),
  });

  return {
    libraryQuery,
    dedupMutation,
    uploadMutation,
  };
}

/**
 * Bring a reference clip in by URL and re-cut it into a new project.
 *
 * Both halves are server work: ``POST /media/from-url`` downloads and registers
 * the clip, and ``POST /media/{id}/recook`` returns a new project together with
 * the script it wrote. The re-cook studio used to call the first one with a raw
 * ``fetch`` to a hardcoded ``http://127.0.0.1:8000``, and when that failed it
 * invented a video, a duration and a transcript locally rather than reporting the
 * failure.
 */
export function useMediaRecook() {
  const queryClient = useQueryClient();

  const ingestMutation = useMutation<MediaItem, Error, MediaIngestUrlRequest>({
    mutationFn: (payload: MediaIngestUrlRequest) => mediaApi.ingestMediaUrl(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mediaItems });
    },
  });

  const recookMutation = useMutation<
    ReCookResult,
    Error,
    { mediaId: string; payload: ReCookRequest }
  >({
    mutationFn: ({ mediaId, payload }) => mediaApi.recookMedia(mediaId, payload),
  });

  return { ingestMutation, recookMutation };
}
