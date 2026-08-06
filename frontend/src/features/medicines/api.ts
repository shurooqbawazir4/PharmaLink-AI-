import { apiFetch, toQueryString } from "@/lib/api-client";
import type { MedicineCreate, MedicineRead } from "@/lib/types";

export function listMedicines(params: { category?: string; includeInactive?: boolean } = {}) {
  return apiFetch<MedicineRead[]>(
    `/medicines/${toQueryString({ category: params.category, include_inactive: params.includeInactive })}`
  );
}

export function getMedicine(id: string) {
  return apiFetch<MedicineRead>(`/medicines/${id}`);
}

export function createMedicine(payload: MedicineCreate) {
  return apiFetch<MedicineRead>("/medicines/", { method: "POST", body: payload });
}

export function updateMedicineUnitCost(id: string, unitCost: number) {
  return apiFetch<MedicineRead>(`/medicines/${id}/unit-cost`, {
    method: "PATCH",
    body: { unit_cost: unitCost },
  });
}

export function deactivateMedicine(id: string) {
  return apiFetch<MedicineRead>(`/medicines/${id}`, { method: "DELETE" });
}
