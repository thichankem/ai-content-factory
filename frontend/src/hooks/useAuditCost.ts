import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { CostCheckResult, AuditRecord } from "../types/api";

export function useAuditCost() {
  const auditQuery = useQuery({
    queryKey: ["audit-trail"],
    queryFn: () => fetchApi<AuditRecord[]>("/audit"),
  });

  const costCheckMutation = useMutation({
    mutationFn: (models: Record<string, number>) =>
      fetchApi<CostCheckResult>("/cost/check", {
        method: "POST",
        body: JSON.stringify({ estimated_usage: models }),
      }),
  });

  return {
    auditQuery,
    costCheckMutation,
  };
}
