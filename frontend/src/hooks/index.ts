/**
 * The studio's data hooks.
 *
 * One hook per screen concern, each wrapping :mod:`@/lib/api` with TanStack Query
 * and, where a mutation returns a project, :func:`@/lib/projectSync.syncProject`.
 *
 * Keys are built through :mod:`@/lib/queryKeys` so a mutation and the screen that
 * reads the same data can never disagree about the key.
 */

export { useAgentBridge } from "@/hooks/useAgentBridge";
export { useAuditCost } from "@/hooks/useAuditCost";
export { useCampaign } from "@/hooks/useCampaign";
export { useExternalIngestion } from "@/hooks/useExternalIngestion";
export { useMediaItems, useMediaLibrary, useMediaSearch } from "@/hooks/useMediaLibrary";
export { useProjects } from "@/hooks/useProjects";
export { useQA } from "@/hooks/useQA";
export { useScriptEngine } from "@/hooks/useScriptEngine";
export { useSEO } from "@/hooks/useSEO";
export { useThumbnails } from "@/hooks/useThumbnails";
export type { ThumbnailOutcome } from "@/hooks/useThumbnails";
export { useTimelineCommands } from "@/hooks/useTimelineCommands";
export { useWorkflowDAG } from "@/hooks/useWorkflowDAG";