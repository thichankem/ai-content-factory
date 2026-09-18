import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";

export function useMediaLibrary() {
  const libraryQuery = useQuery({
    queryKey: ["media-library"],
    queryFn: () => fetchApi<any>("/library"),
  });

  const searchMediaQuery = (query: string) =>
    useQuery({
      queryKey: ["media-search", query],
      queryFn: () => fetchApi<any[]>(`/media/search?q=${encodeURIComponent(query)}`),
      enabled: query.length > 0,
    });

  const dedupMutation = useMutation({
    mutationFn: () =>
      fetchApi<{ duplicates: Array<{ original: string; duplicate: string; similarity: number }> }>("/media/dedup", {
        method: "POST",
      }),
  });

  return {
    libraryQuery,
    searchMediaQuery,
    dedupMutation,
  };
}
