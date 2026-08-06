import { apiFetch, toQueryString } from "@/lib/api-client";
import type {
  PurchaseOrderReceiveRequest,
  PurchaseOrderRead,
  PurchaseOrderStatus,
  SupplierCreate,
  SupplierRead,
} from "@/lib/types";

// --- Suppliers -------------------------------------------------------------

export function listSuppliers(params: { includeInactive?: boolean } = {}) {
  return apiFetch<SupplierRead[]>(`/suppliers/${toQueryString({ include_inactive: params.includeInactive })}`);
}

export function createSupplier(payload: SupplierCreate) {
  return apiFetch<SupplierRead>("/suppliers/", { method: "POST", body: payload });
}

export function deactivateSupplier(id: string) {
  return apiFetch<SupplierRead>(`/suppliers/${id}`, { method: "DELETE" });
}

// --- Purchase orders ---------------------------------------------------------

export function listPurchaseOrders(
  params: { hospitalId?: string; status?: PurchaseOrderStatus; medicineId?: string } = {}
) {
  return apiFetch<PurchaseOrderRead[]>(
    `/purchase-orders/${toQueryString({
      hospital_id: params.hospitalId,
      status: params.status,
      medicine_id: params.medicineId,
    })}`
  );
}

export function recommendPurchaseOrders(hospitalId: string) {
  return apiFetch<PurchaseOrderRead[]>(`/purchase-orders/recommend/${hospitalId}`, { method: "POST" });
}

export function approvePurchaseOrder(id: string) {
  return apiFetch<PurchaseOrderRead>(`/purchase-orders/${id}/approve`, { method: "PATCH" });
}

export function markPurchaseOrderOrdered(id: string) {
  return apiFetch<PurchaseOrderRead>(`/purchase-orders/${id}/mark-ordered`, { method: "PATCH" });
}

export function receivePurchaseOrder(id: string, payload: PurchaseOrderReceiveRequest) {
  return apiFetch<PurchaseOrderRead>(`/purchase-orders/${id}/receive`, {
    method: "PATCH",
    body: payload,
  });
}

export function cancelPurchaseOrder(id: string) {
  return apiFetch<PurchaseOrderRead>(`/purchase-orders/${id}/cancel`, { method: "PATCH" });
}
