import { apiFetch, toQueryString } from "@/lib/api-client";
import type { ExpiryRiskRead } from "@/lib/types";

export function listHighRisk(params: { hospitalId?: string; threshold?: number } = {}) {
  return apiFetch<ExpiryRiskRead[]>(
    `/expiry/high-risk${toQueryString({ hospital_id: params.hospitalId, threshold: params.threshold })}`
  );
}

export async function getLatestForInventory(inventoryId: string): Promise<ExpiryRiskRead | null> {
  try {
    return await apiFetch<ExpiryRiskRead>(`/expiry/inventory/${inventoryId}/latest`);
  } catch {
    return null;
  }
}

export function evaluateBatch(inventoryId: string) {
  return apiFetch<ExpiryRiskRead>(`/expiry/evaluate/${inventoryId}`, { method: "POST" });
}

export function evaluateHospital(hospitalId: string) {
  return apiFetch<ExpiryRiskRead[]>(`/expiry/evaluate-hospital/${hospitalId}`, { method: "POST" });
}
