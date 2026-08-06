import { apiFetch, ApiError, toQueryString } from "@/lib/api-client";
import type { ForecastRead } from "@/lib/types";

export function generateForecast(hospitalId: string, medicineId: string, horizonDays = 30) {
  return apiFetch<ForecastRead>(
    `/forecasts/generate/${hospitalId}/${medicineId}${toQueryString({ horizon_days: horizonDays })}`,
    { method: "POST" }
  );
}

export function listForecasts(params: { hospitalId?: string; medicineId?: string } = {}) {
  return apiFetch<ForecastRead[]>(
    `/forecasts/${toQueryString({ hospital_id: params.hospitalId, medicine_id: params.medicineId })}`
  );
}

export async function getLatestForecast(
  hospitalId: string,
  medicineId: string
): Promise<ForecastRead | null> {
  try {
    return await apiFetch<ForecastRead>(`/forecasts/latest/${hospitalId}/${medicineId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
