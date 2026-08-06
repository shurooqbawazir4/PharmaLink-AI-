import { apiFetch, toQueryString } from "@/lib/api-client";
import type { AlertRead, AlertSeverity, AlertType } from "@/lib/types";

export function listAlerts(
  params: {
    hospitalId?: string;
    severity?: AlertSeverity;
    type?: AlertType;
    isResolved?: boolean;
  } = {}
) {
  return apiFetch<AlertRead[]>(
    `/alerts/${toQueryString({
      hospital_id: params.hospitalId,
      severity: params.severity,
      type: params.type,
      is_resolved: params.isResolved,
    })}`
  );
}

export function getAlert(id: string) {
  return apiFetch<AlertRead>(`/alerts/${id}`);
}

export function resolveAlert(id: string) {
  return apiFetch<AlertRead>(`/alerts/${id}/resolve`, { method: "PATCH" });
}
