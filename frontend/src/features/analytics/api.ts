import { apiFetch, toQueryString } from "@/lib/api-client";
import type { KPISummaryRead } from "@/lib/types";

export function getKpiSummary(hospitalId?: string | null) {
  return apiFetch<KPISummaryRead>(`/analytics/kpis${toQueryString({ hospital_id: hospitalId })}`);
}
