/**
 * SEO scoring, optimisation and experiment-design endpoints.
 *
 * ``/seo/*`` answers a *report* per platform, and ``platform: "all"`` scores every
 * platform at once (the response is then a map keyed by platform). The studio
 * scores one platform at a time so it can render a single report.
 */

import * as api from "@/lib/api/client";
import {
  SeoAbPlanRequest,
  SeoAbPlanResult,
  SeoKeywordRequest,
  SeoKeywordResult,
  SeoOptimizeResult,
  SeoPackInput,
  SeoProjectScoreRequest,
  SeoReport,
  SeoScoreRequest,
} from "@/types/seo";

/** ``GET /seo/rules`` — every platform rule, threshold and signal weight. */
export function getRules(): Promise<Array<Record<string, unknown>>> {
  return api.apiFetch<Array<Record<string, unknown>>>("/seo/rules");
}

/**
 * ``POST /seo/score`` — score a submitted pack.
 *
 * Scores one platform; pass ``platform: "all"`` only through
 * :func:`scoreAllPlatforms`, whose response really is keyed by platform.
 */
export function score(req: SeoScoreRequest): Promise<SeoReport> {
  return api.apiFetch<SeoReport>("/seo/score", { method: "POST", body: req });
}

/** ``POST /seo/score`` with ``platform: "all"`` — one report per platform. */
export function scoreAllPlatforms(
  pack: SeoPackInput
): Promise<Record<string, SeoReport>> {
  return api.apiFetch<Record<string, SeoReport>>("/seo/score", {
    method: "POST",
    body: { platform: "all", pack },
  });
}

/** ``POST /seo/optimize`` — rewrite the pack and report the measured gain. */
export function optimize(req: SeoScoreRequest): Promise<SeoOptimizeResult> {
  return api.apiFetch<SeoOptimizeResult>("/seo/optimize", {
    method: "POST",
    body: req,
  });
}

/** ``POST /seo/ab/plan`` — sample size and the decision rule for an A/B test. */
export function abPlan(req: SeoAbPlanRequest): Promise<SeoAbPlanResult> {
  return api.apiFetch<SeoAbPlanResult>("/seo/ab/plan", {
    method: "POST",
    body: req,
  });
}

/** ``POST /seo/ab/evaluate`` — test whether a variant beat the control. */
export function abEvaluate(
  req: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return api.apiFetch<Record<string, unknown>>("/seo/ab/evaluate", {
    method: "POST",
    body: req,
  });
}

/** ``POST /seo/keywords`` — rank phrases by demand against competition. */
export function keywords(req: SeoKeywordRequest): Promise<SeoKeywordResult> {
  return api.apiFetch<SeoKeywordResult>("/seo/keywords", {
    method: "POST",
    body: req,
  });
}

/** ``POST /seo/calibrate`` — learn which signals predict this channel's results. */
export function calibrate(
  req: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return api.apiFetch<Record<string, unknown>>("/seo/calibrate", {
    method: "POST",
    body: req,
  });
}

/** ``POST /projects/{id}/seo`` — score the pack this project would publish. */
export function scoreProject(
  projectId: string,
  req: SeoProjectScoreRequest = {}
): Promise<SeoReport> {
  return api.apiFetch<SeoReport>(`/projects/${projectId}/seo`, {
    method: "POST",
    body: req,
  });
}