import { apiFetch, toQueryString } from "@/lib/api-client";
import type { InventoryChangeRead, InventoryReceiveRequest, InventoryRead } from "@/lib/types";

export function listInventory(params: { hospitalId?: string; medicineId?: string } = {}) {
  return apiFetch<InventoryRead[]>(
    `/inventory/${toQueryString({ hospital_id: params.hospitalId, medicine_id: params.medicineId })}`
  );
}

export function listExpiringSoon(params: { hospitalId?: string; withinDays?: number } = {}) {
  return apiFetch<InventoryRead[]>(
    `/inventory/expiring-soon${toQueryString({
      hospital_id: params.hospitalId,
      within_days: params.withinDays,
    })}`
  );
}

export function listBelowSafetyStock(params: { hospitalId?: string } = {}) {
  return apiFetch<InventoryRead[]>(
    `/inventory/below-safety-stock${toQueryString({ hospital_id: params.hospitalId })}`
  );
}

export function getInventoryBatch(id: string) {
  return apiFetch<InventoryRead>(`/inventory/${id}`);
}

export function receiveStock(payload: InventoryReceiveRequest) {
  return apiFetch<InventoryRead>("/inventory/receive", { method: "POST", body: payload });
}

export function consumeStock(id: string, quantity: number) {
  return apiFetch<InventoryChangeRead>(`/inventory/${id}/consume`, {
    method: "POST",
    body: { quantity },
  });
}

export function writeOffExpired(id: string) {
  return apiFetch<InventoryChangeRead>(`/inventory/${id}/write-off`, { method: "POST" });
}

export function adjustStock(id: string, changeQty: number) {
  return apiFetch<InventoryChangeRead>(`/inventory/${id}/adjust`, {
    method: "POST",
    body: { change_qty: changeQty },
  });
}
