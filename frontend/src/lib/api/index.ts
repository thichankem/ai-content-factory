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

export * as agentsApi from "./agents";
export * as campaignApi from "./campaign";
export * as externalApi from "./external";
export * as historyApi from "./history";
export * as libraryApi from "./library";
export * as mediaApi from "./media";
export * as projectsApi from "./projects";
export * as qaApi from "./qa";
export * as scriptApi from "./script";
export * as seoApi from "./seo";
export * as timelineApi from "./timeline";
export * as workflowApi from "./workflow";

export { ApiError, apiFetch, apiSend, apiText, buildQuery } from "./client";
export type { QueryValue, RequestOptions } from "./client";