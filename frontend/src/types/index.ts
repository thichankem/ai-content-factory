/**
 * The studio's type surface.
 *
 * Two families live here and they are not interchangeable:
 *
 * * **contracts** — modules named after the backend models they mirror
 *   (``project``, ``timeline``, ``qa``, …). A field here exists because the API
 *   sends it; change one only together with the backend.
 * * **``studio``** — view models the UI invents for itself, which never travel
 *   over HTTP.
 *
 * Import from the module that owns the concept rather than from this barrel when
 * the concept is narrow; the barrel exists for the common case.
 */

export * from "@/types/common";
export * from "@/types/project";
export * from "@/types/script";
export * from "@/types/timeline";
export * from "@/types/media";
export * from "@/types/library";
export * from "@/types/research";
export * from "@/types/voice";
export * from "@/types/qa";
export * from "@/types/seo";
export * from "@/types/workflow";
export * from "@/types/campaign";
export * from "@/types/agent";
export * from "@/types/external";
export * from "@/types/history";
export * from "@/types/studio";
