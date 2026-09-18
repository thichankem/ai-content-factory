/**
 * The studio's data hooks.
 *
 * One hook per screen concern, each wrapping :mod:`@/lib/api` with TanStack Query
 * and, where a mutation returns a project, :func:`@/lib/projectSync.syncProject`.
 *
 * Keys are built through :mod:`@/lib/queryKeys` so a mutation and the screen that
 * reads the same data can never disagree about the key.
 */

export { useAgentBridge } from "./useAgentBridge";
export { useAuditCost } from "./useAuditCost";
export { useCampaign } from "./useCampaign";
export { useExternalIngestion } from "./useExternalIngestion";
export { useMediaItems, useMediaLibrary, useMediaSearch } from "./useMediaLibrary";
export { useProjects } from "./useProjects";
export { useQA } from "./useQA";
export { useScriptEngine } from "./useScriptEngine";
export { useSEO } from "./useSEO";
export { useThumbnails } from "./useThumbnails";
export type { ThumbnailOutcome } from "./useThumbnails";
export { useTimelineCommands } from "./useTimelineCommands";
export { useWorkflowDAG } from "./useWorkflowDAG";