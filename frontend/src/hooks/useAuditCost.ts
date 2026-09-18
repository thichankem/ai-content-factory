/**
 * Cost Guard and provenance-audit hooks.
 *
 * ``/audit`` is append-only and tamper-evident: the studio reads it and never
 * rewrites it. Cost estimates are advisory — a call whose estimate crosses the
 * configured budget comes back with ``needs_confirmation`` set, and the operator
 * decides.
 */

import { useMutation, useQuery } from "@tanstack/react-query";

import { qaApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { AuditEntry, CostCheckRequest, CostCheckResult } from "@/types/qa";

export function useAuditCost() {
  const auditQuery = useQuery<AuditEntry[]>({
    queryKey: queryKeys.auditTrail,
    queryFn: () => qaApi.listAudit(),
  });

  const costCheckMutation = useMutation<CostCheckResult, Error, CostCheckRequest>({
    mutationFn: (req: CostCheckRequest) => qaApi.checkCost(req),
  });

  return {
    auditQuery,
    costCheckMutation,
  };
}