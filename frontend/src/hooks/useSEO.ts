import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";

export interface SeoPlatformPack {
  title: string;
  description?: string;
  tags?: string[];
  hashtags?: string[];
  hook?: string;
  duration_seconds?: number;
  aspect_ratio?: string;
  caption_cues?: number;
  chapter_markers?: number;
}

export interface SeoScoreResult {
  platform: string;
  score: number;
  grade: string;
  passed: boolean;
  breakdown: Record<string, { score: number; weight: number; label: string; passed: boolean; tip?: string }>;
  fixes: Array<{ signal: string; gain: number; action: string }>;
}

export interface SeoOptimizeResult {
  platform: string;
  before: { score: number; grade: string };
  after: { score: number; grade: string };
  gain: number;
  optimized_pack: SeoPlatformPack;
  applied_fixes: string[];
}

export interface SeoAbPlanResult {
  metric: string;
  sample_size_per_arm: number;
  total_sample_size: number;
  estimated_days: number;
  minimum_detectable_effect: number;
  decision_rule: string;
}

export function useSEO(projectId?: string) {
  const rulesQuery = useQuery({
    queryKey: ["seo-rules"],
    queryFn: () => fetchApi<any[]>("/seo/rules"),
    staleTime: 1000 * 60 * 60, // 1 hour
  });

  const projectSeoMutation = useMutation({
    mutationFn: (data: { platform: string; title?: string; description?: string; tags?: string[]; hashtags?: string[]; keywords?: string[] }) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<SeoScoreResult>(`/projects/${projectId}/seo`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  });

  const optimizeMutation = useMutation({
    mutationFn: (data: { platform: string; pack: SeoPlatformPack }) => {
      return fetchApi<SeoOptimizeResult>("/seo/optimize", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  });

  const abPlanMutation = useMutation({
    mutationFn: (data: {
      metric: string;
      baseline_rate: number;
      relative_lift?: number;
      daily_traffic?: number;
      arms?: number;
    }) => {
      return fetchApi<SeoAbPlanResult>("/seo/ab/plan", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  });

  const keywordsMutation = useMutation({
    mutationFn: (data: { keywords: string[]; competitors?: any[]; pack?: SeoPlatformPack }) => {
      return fetchApi<any>("/seo/keywords", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  });

  return {
    rulesQuery,
    projectSeoMutation,
    optimizeMutation,
    abPlanMutation,
    keywordsMutation,
  };
}
