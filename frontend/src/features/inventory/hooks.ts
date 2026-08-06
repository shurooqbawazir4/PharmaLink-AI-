"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/inventory/api";
import type { InventoryReceiveRequest } from "@/lib/types";

const KEY = ["inventory"] as const;

/** hospitalId is optional — omitted (admin, network-wide views like the
 * Dashboard's expiry-risk widget) it lists across every hospital, matching
 * `GET /inventory/`'s own optional `hospital_id` query param. */
export function useInventory(params: { hospitalId?: string; medicineId?: string } = {}) {
  return useQuery({
    queryKey: [...KEY, "list", params],
    queryFn: () => api.listInventory(params),
  });
}

export function useExpiringSoon(params: { hospitalId?: string; withinDays?: number } = {}) {
  return useQuery({
    queryKey: [...KEY, "expiring-soon", params],
    queryFn: () => api.listExpiringSoon(params),
  });
}

export function useBelowSafetyStock(params: { hospitalId?: string } = {}) {
  return useQuery({
    queryKey: [...KEY, "below-safety-stock", params],
    queryFn: () => api.listBelowSafetyStock(params),
  });
}

function useInvalidateInventory() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: KEY });
}

export function useReceiveStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (payload: InventoryReceiveRequest) => api.receiveStock(payload),
    onSuccess: () => {
      invalidate();
      toast.success("Stock received.");
    },
  });
}

export function useConsumeStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) => api.consumeStock(id, quantity),
    onSuccess: () => {
      invalidate();
      toast.success("Consumption recorded.");
    },
  });
}

export function useWriteOffExpired() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (id: string) => api.writeOffExpired(id),
    onSuccess: () => {
      invalidate();
      toast.success("Batch written off.");
    },
  });
}

export function useAdjustStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: ({ id, changeQty }: { id: string; changeQty: number }) => api.adjustStock(id, changeQty),
    onSuccess: () => {
      invalidate();
      toast.success("Stock adjusted.");
    },
  });
}
