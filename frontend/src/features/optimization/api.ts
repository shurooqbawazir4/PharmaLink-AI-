import { apiFetch } from "@/lib/api-client";
import type { TransferRead } from "@/lib/types";

export function optimizeNetworkTransfers(medicineId: string) {
  return apiFetch<TransferRead[]>(`/optimization/transfers/${medicineId}`, { method: "POST" });
}
