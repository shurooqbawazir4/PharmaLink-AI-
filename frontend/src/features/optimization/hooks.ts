"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/optimization/api";

export function useOptimizeNetworkTransfers() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (medicineId: string) => api.optimizeNetworkTransfers(medicineId),
    onSuccess: (transfers) => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      toast.success(
        transfers.length > 0
          ? `Proposed ${transfers.length} transfer${transfers.length === 1 ? "" : "s"}.`
          : "No rebalancing needed — no hospital is in deficit for this medicine."
      );
    },
  });
}
