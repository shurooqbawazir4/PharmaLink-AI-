"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/medicines/api";
import type { MedicineCreate } from "@/lib/types";

const KEY = ["medicines"] as const;

export function useMedicines(params: { category?: string; includeInactive?: boolean } = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: () => api.listMedicines(params),
  });
}

export function useMedicine(id: string | undefined) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () => api.getMedicine(id as string),
    enabled: !!id,
  });
}

export function useCreateMedicine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: MedicineCreate) => api.createMedicine(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Medicine added to the catalogue.");
    },
  });
}

export function useUpdateMedicineUnitCost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, unitCost }: { id: string; unitCost: number }) =>
      api.updateMedicineUnitCost(id, unitCost),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Unit cost updated.");
    },
  });
}

export function useDeactivateMedicine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deactivateMedicine(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Medicine deactivated.");
    },
  });
}
