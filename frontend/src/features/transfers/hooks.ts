"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/transfers/api";
import type { TransferProposeRequest, TransferStatus } from "@/lib/types";

const KEY = ["transfers"] as const;

export function useTransfers(
  params: { hospitalId?: string; status?: TransferStatus; medicineId?: string } = {}
) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: () => api.listTransfers(params),
  });
}

function useInvalidateTransfers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: KEY });
}

export function useProposeTransfer() {
  const invalidate = useInvalidateTransfers();
  return useMutation({
    mutationFn: (payload: TransferProposeRequest) => api.proposeTransfer(payload),
    onSuccess: () => {
      invalidate();
      toast.success("Transfer proposed.");
    },
  });
}

export function useApproveTransfer() {
  const invalidate = useInvalidateTransfers();
  return useMutation({
    mutationFn: (id: string) => api.approveTransfer(id),
    onSuccess: () => {
      invalidate();
      toast.success("Transfer approved.");
    },
  });
}

export function useCompleteTransfer() {
  const invalidate = useInvalidateTransfers();
  return useMutation({
    mutationFn: (id: string) => api.completeTransfer(id),
    onSuccess: () => {
      invalidate();
      toast.success("Transfer completed.");
    },
  });
}

export function useCancelTransfer() {
  const invalidate = useInvalidateTransfers();
  return useMutation({
    mutationFn: (id: string) => api.cancelTransfer(id),
    onSuccess: () => {
      invalidate();
      toast.success("Transfer cancelled.");
    },
  });
}
