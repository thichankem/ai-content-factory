/**
 * SEO hooks.
 *
 * The response is a :interface:`SeoReport` — per-signal status, weighted
 * dimensions and measurable quick wins — not a flat score. The studio renders
 * that report directly and never re-derives the weights.
 */

import { useMutation, useQuery } from "@tanstack/react-query";

import { seoApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import {
  SeoAbPlanRequest,
  SeoAbPlanResult,
  SeoKeywordRequest,
  SeoKeywordResult,
  SeoOptimizeResult,
  SeoProjectScoreRequest,
  SeoReport,
  SeoScoreRequest,
} from "@/types/seo";

export function useSEO(projectId?: string) {
  const rulesQuery = useQuery({
    queryKey: queryKeys.seoRules,
    queryFn: () => seoApi.getRules(),
    staleTime: 1000 * 60 * 60,
  });

  /** Score the pack this project would actually publish. */
  const projectSeoMutation = useMutation<SeoReport, Error, SeoProjectScoreRequest>({
    mutationFn: (req: SeoProjectScoreRequest) => {
      if (!projectId) throw new Error("No project selected");
      return seoApi.scoreProject(projectId, req);
    },
  });

  /** Score an arbitrary pack, without touching the project. */
  const scorePackMutation = useMutation<SeoReport, Error, SeoScoreRequest>({
    mutationFn: (req: SeoScoreRequest) => seoApi.score(req),
  });

  const optimizeMutation = useMutation<SeoOptimizeResult, Error, SeoScoreRequest>({
    mutationFn: (req: SeoScoreRequest) => seoApi.optimize(req),
  });

  const abPlanMutation = useMutation<SeoAbPlanResult, Error, SeoAbPlanRequest>({
    mutationFn: (req: SeoAbPlanRequest) => seoApi.abPlan(req),
  });

  const keywordsMutation = useMutation<SeoKeywordResult, Error, SeoKeywordRequest>({
    mutationFn: (req: SeoKeywordRequest) => seoApi.keywords(req),
  });

  return {
    rulesQuery,
    projectSeoMutation,
    scorePackMutation,
    optimizeMutation,
    abPlanMutation,
    keywordsMutation,
  };
}