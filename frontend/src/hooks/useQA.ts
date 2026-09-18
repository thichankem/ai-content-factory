import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { PlatformQAResult, BrandKitQAResult, CopyrightCheckResult } from "../types/api";

export function useQA() {
  const platformQAMutation = useMutation({
    mutationFn: ({ platform, duration, aspectRatio }: { platform: string; duration: number; aspectRatio: string }) =>
      fetchApi<PlatformQAResult>("/qa/platform/verdict", {
        method: "POST",
        body: JSON.stringify({ platform, duration_seconds: duration, aspect_ratio: aspectRatio }),
      }),
  });

  const brandQAMutation = useMutation({
    mutationFn: (payload: { font?: string; primary_color?: string; tone?: string }) =>
      fetchApi<BrandKitQAResult>("/qa/brand/verdict", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });

  const copyrightMutation = useMutation({
    mutationFn: (assetIds: string[]) =>
      fetchApi<CopyrightCheckResult>("/qa/copyright/verdict", {
        method: "POST",
        body: JSON.stringify({ asset_ids: assetIds }),
      }),
  });

  return {
    platformQAMutation,
    brandQAMutation,
    copyrightMutation,
  };
}
