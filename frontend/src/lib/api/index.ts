/**
 * The studio's HTTP surface, grouped by domain.
 *
 * Modules are re-exported under a namespace because several of them own a
 * function with the same name (``search``, ``get``, ``list``). Import the
 * namespace, not the individual function::
 *
 *     import { mediaApi, workflowApi } from "@/lib/api";
 *
 *     const items = await mediaApi.listMedia();
 *     const flow = await workflowApi.getWorkflow(projectId);
 *
 * Nothing here touches React. Hooks in ``src/hooks`` wrap these functions with
 * TanStack Query, which is what keeps request/response shapes in one layer and
 * cache behaviour in another.
 */

export * as agentsApi from "@/lib/api/agents";
export * as campaignApi from "@/lib/api/campaign";
export * as externalApi from "@/lib/api/external";
export * as historyApi from "@/lib/api/history";
export * as libraryApi from "@/lib/api/library";
export * as mediaApi from "@/lib/api/media";
export * as projectsApi from "@/lib/api/projects";
export * as qaApi from "@/lib/api/qa";
export * as scriptApi from "@/lib/api/script";
export * as seoApi from "@/lib/api/seo";
export * as timelineApi from "@/lib/api/timeline";
export * as workflowApi from "@/lib/api/workflow";

export { ApiError, apiFetch, apiSend, apiText, buildQuery } from "@/lib/api/client";
export type { QueryValue, RequestOptions } from "@/lib/api/client";