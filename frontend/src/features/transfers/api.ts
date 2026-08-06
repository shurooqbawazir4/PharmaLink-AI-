import { apiFetch, toQueryString } from "@/lib/api-client";
import type { TransferProposeRequest, TransferRead, TransferStatus } from "@/lib/types";

export function listTransfers(
  params: { hospitalId?: string; status?: TransferStatus; medicineId?: string } = {}
) {
  return apiFetch<TransferRead[]>(
    `/transfers/${toQueryString({
      hospital_id: params.hospitalId,
      status: params.status,
      medicine_id: params.medicineId,
    })}`
  );
}

export function getTransfer(id: string) {
  return apiFetch<TransferRead>(`/transfers/${id}`);
}

export function proposeTransfer(payload: TransferProposeRequest) {
  return apiFetch<TransferRead>("/transfers/propose", { method: "POST", body: payload });
}

export function approveTransfer(id: string) {
  return apiFetch<TransferRead>(`/transfers/${id}/approve`, { method: "PATCH" });
}

export function completeTransfer(id: string) {
  return apiFetch<TransferRead>(`/transfers/${id}/complete`, { method: "PATCH" });
}

export function cancelTransfer(id: string) {
  return apiFetch<TransferRead>(`/transfers/${id}/cancel`, { method: "PATCH" });
}
