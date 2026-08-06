import { apiFetch, toQueryString } from "@/lib/api-client";
import type { HospitalCreate, HospitalRead } from "@/lib/types";

export function listHospitals(params: { region?: string; includeInactive?: boolean } = {}) {
  return apiFetch<HospitalRead[]>(
    `/hospitals/${toQueryString({ region: params.region, include_inactive: params.includeInactive })}`
  );
}

export function getHospital(id: string) {
  return apiFetch<HospitalRead>(`/hospitals/${id}`);
}

export function createHospital(payload: HospitalCreate) {
  return apiFetch<HospitalRead>("/hospitals/", { method: "POST", body: payload });
}

export function updateHospitalOccupancy(id: string, occupancyRate: number) {
  return apiFetch<HospitalRead>(`/hospitals/${id}/occupancy`, {
    method: "PATCH",
    body: { occupancy_rate: occupancyRate },
  });
}

export function deactivateHospital(id: string) {
  return apiFetch<HospitalRead>(`/hospitals/${id}`, { method: "DELETE" });
}
