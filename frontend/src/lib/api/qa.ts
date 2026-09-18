/**
 * QA, cost, audit, thumbnail and command endpoints.
 *
 * Covers the router built from ``models/qa.py``. Two things worth knowing:
 *
 * * Each check has **two** routes: a list form (``/qa/platform``) returning raw
 *   findings and a verdict form (``/qa/platform/verdict``) returning a pass/fail
 *   summary. The studio uses the verdict form and shows the findings it carries.
 * * ``/cost/check`` merges ``calls`` and ``estimated_usage``; the studio sends
 *   ``estimated_usage``, which is why :interface:`CostCheckRequest` lists both.
 */

import * as api from "@/lib/api/client";
import {
  AuditEntry,
  AuditRecordRequest,
  BrandCheckRequest,
  BrandVerdict,
  CopyrightCheckRequest,
  CopyrightVerdict,
  CostCheckRequest,
  CostCheckResult,
  PlatformCheckRequest,
  PlatformVerdict,
  QaFinding,
  SimplifySubtitlesRequest,
  SimplifySubtitlesResult,
  ThumbnailCandidatesResponse,
  ThumbnailRequest,
} from "@/types/qa";

/** ``POST /qa/platform`` — the raw findings. */
export function checkPlatform(req: PlatformCheckRequest): Promise<QaFinding[]> {
  return api.apiFetch<QaFinding[]>("/qa/platform", { method: "POST", body: req });
}

/** ``POST /qa/platform/verdict`` — pass/fail plus the findings behind it. */
export function platformVerdict(
  req: PlatformCheckRequest
): Promise<PlatformVerdict> {
  return api.apiFetch<PlatformVerdict>("/qa/platform/verdict", {
    method: "POST",
    body: req,
  });
}

/** ``POST /qa/brand`` — the raw findings. */
export function checkBrand(req: BrandCheckRequest): Promise<QaFinding[]> {
  return api.apiFetch<QaFinding[]>("/qa/brand", { method: "POST", body: req });
}

/** ``POST /qa/brand/verdict``. */
export function brandVerdict(req: BrandCheckRequest): Promise<BrandVerdict> {
  return api.apiFetch<BrandVerdict>("/qa/brand/verdict", {
    method: "POST",
    body: req,
  });
}

/** ``POST /qa/copyright`` — the raw findings. */
export function checkCopyright(req: CopyrightCheckRequest): Promise<QaFinding[]> {
  return api.apiFetch<QaFinding[]>("/qa/copyright", { method: "POST", body: req });
}

/** ``POST /qa/copyright/verdict``. */
export function copyrightVerdict(
  req: CopyrightCheckRequest
): Promise<CopyrightVerdict> {
  return api.apiFetch<CopyrightVerdict>("/qa/copyright/verdict", {
    method: "POST",
    body: req,
  });
}

/** ``GET /audit`` — the newest audit records first. */
export function listAudit(limit = 100): Promise<AuditEntry[]> {
  return api.apiFetch<AuditEntry[]>("/audit", { query: { limit } });
}

/** ``POST /audit/record`` — append one provenance record. */
export function recordAudit(req: AuditRecordRequest): Promise<AuditEntry> {
  return api.apiFetch<AuditEntry>("/audit/record", { method: "POST", body: req });
}

/** ``POST /cost/check`` — price a plan of model calls. */
export function checkCost(req: CostCheckRequest): Promise<CostCheckResult> {
  return api.apiFetch<CostCheckResult>("/cost/check", {
    method: "POST",
    body: req,
  });
}

/**
 * ``POST /thumbnail/candidates``.
 *
 * Rejects with :class:`ApiError` only on transport/HTTP failure; "nothing to
 * draw from" comes back as ``empty_reason`` with an empty list, so the caller can
 * explain the empty grid rather than showing a bare error.
 */
export function thumbnailCandidates(
  req: ThumbnailRequest
): Promise<ThumbnailCandidatesResponse> {
  return api.apiFetch<ThumbnailCandidatesResponse>("/thumbnail/candidates", {
    method: "POST",
    body: req,
  });
}

/** ``POST /subtitles/simplify`` — readable captions for cognitive accessibility. */
export function simplifySubtitles(
  req: SimplifySubtitlesRequest
): Promise<SimplifySubtitlesResult> {
  return api.apiFetch<SimplifySubtitlesResult>("/subtitles/simplify", {
    method: "POST",
    body: req,
  });
}

/** ``GET /health`` — status, version and the live provider chain. */
export function health(): Promise<Record<string, unknown>> {
  return api.apiFetch<Record<string, unknown>>("/health");
}
