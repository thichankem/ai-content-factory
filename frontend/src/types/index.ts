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

export * from "./common";
export * from "./project";
export * from "./script";
export * from "./timeline";
export * from "./media";
export * from "./library";
export * from "./research";
export * from "./voice";
export * from "./qa";
export * from "./seo";
export * from "./workflow";
export * from "./campaign";
export * from "./agent";
export * from "./external";
export * from "./history";
export * from "./studio";
