/**
 * Query keys for every TanStack Query hook, in one place.
 *
 * A key that is written inline in a hook and invalidated inline elsewhere drifts
 * the moment either side is edited: the mutation succeeds, the cache is not
 * invalidated, and the screen keeps showing stale data. Building keys through
 * these helpers makes that class of bug impossible.
 */

export const queryKeys = {
  projects: ["projects"] as const,
  project: (projectId?: string) => ["projects", projectId] as const,

  scriptStyles: ["script-styles"] as const,

  videoProject: (projectId?: string) => ["video-project", projectId] as const,
  timelineReport: (projectId?: string) => ["timeline-report", projectId] as const,
  renderPlan: (projectId?: string) => ["render-plan", projectId] as const,

  workflowBlocks: ["workflow-blocks"] as const,
  workflow: (projectId?: string) => ["workflow", projectId] as const,
  workflowChecklist: (projectId?: string) => ["workflow-checklist", projectId] as const,
  workflowRuns: (projectId?: string) => ["workflow-runs", projectId] as const,

  campaign: (projectId?: string) => ["campaign", projectId] as const,

  agentCatalog: ["agent-catalog"] as const,

  externalAssets: (projectId?: string) => ["external-assets", projectId] as const,

  mediaLibrary: ["media-library"] as const,
  mediaSearch: (query: string) => ["media-search", query] as const,
  mediaItems: ["media-items"] as const,

  library: ["library"] as const,

  auditTrail: ["audit-trail"] as const,

  seoRules: ["seo-rules"] as const,

  onThisDay: (params: { month?: number; day?: number }) =>
    ["on-this-day", params.month ?? null, params.day ?? null] as const,
} as const;