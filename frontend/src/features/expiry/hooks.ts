"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/expiry/api";

const KEY = ["expiry"] as const;

export function useHighRiskExpiry(params: { hospitalId?: string; threshold?: number } = {}) {
  return useQuery({
    queryKey: [...KEY, "high-risk", params],
    queryFn: () => api.listHighRisk(params),
  });
}

export function useLatestExpiryRisk(inventoryId: string | undefined) {
  return useQuery({
    queryKey: [...KEY, "latest", inventoryId],
    queryFn: () => api.getLatestForInventory(inventoryId as string),
    enabled: !!inventoryId,
  });
}

export function useEvaluateBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inventoryId: string) => api.evaluateBatch(inventoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Expiry risk evaluated.");
    },
  });
}

export function useEvaluateHospital() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (hospitalId: string) => api.evaluateHospital(hospitalId),
    onSuccess: (records) => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success(`Evaluated ${records.length} batch${records.length === 1 ? "" : "es"}.`);
    },
  });
}
