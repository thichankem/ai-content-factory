/**
 * Media library hooks.
 *
 * The previous version returned a *function* that called ``useQuery`` when
 * invoked from render, which breaks the Rules of Hooks (a search box that
 * re-renders a different number of times would reorder hook calls). Search is now
 * its own hook, :func:`useMediaSearch`, taking the query as an argument.
 */

import { useMutation, useQuery } from "@tanstack/react-query";

import { mediaApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { DedupResult, MediaItem, MediaSearchHit } from "@/types/media";
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
    queryFn: () => mediaApi.listMedia().then(() => mediaApiLibrary()),
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
