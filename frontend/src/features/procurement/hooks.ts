"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/procurement/api";
import type { PurchaseOrderReceiveRequest, PurchaseOrderStatus, SupplierCreate } from "@/lib/types";

const SUPPLIERS_KEY = ["suppliers"] as const;
const ORDERS_KEY = ["purchase-orders"] as const;

export function useSuppliers(params: { includeInactive?: boolean } = {}) {
  return useQuery({
    queryKey: [...SUPPLIERS_KEY, params],
    queryFn: () => api.listSuppliers(params),
  });
}

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SupplierCreate) => api.createSupplier(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUPPLIERS_KEY });
      toast.success("Supplier added.");
    },
  });
}

export function useDeactivateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deactivateSupplier(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUPPLIERS_KEY });
      toast.success("Supplier deactivated.");
    },
  });
}

export function usePurchaseOrders(
  params: { hospitalId?: string; status?: PurchaseOrderStatus; medicineId?: string } = {}
) {
  return useQuery({
    queryKey: [...ORDERS_KEY, params],
    queryFn: () => api.listPurchaseOrders(params),
  });
}

function useInvalidateOrders() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY });
}

export function useRecommendPurchaseOrders() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (hospitalId: string) => api.recommendPurchaseOrders(hospitalId),
    onSuccess: (orders) => {
      invalidate();
      toast.success(
        orders.length > 0
          ? `${orders.length} order${orders.length === 1 ? "" : "s"} recommended.`
          : "No reorder needed right now."
      );
    },
  });
}

export function useApprovePurchaseOrder() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (id: string) => api.approvePurchaseOrder(id),
    onSuccess: () => {
      invalidate();
      toast.success("Order approved.");
    },
  });
}

export function useMarkPurchaseOrderOrdered() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (id: string) => api.markPurchaseOrderOrdered(id),
    onSuccess: () => {
      invalidate();
      toast.success("Order marked as ordered.");
    },
  });
}

export function useReceivePurchaseOrder() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PurchaseOrderReceiveRequest }) =>
      api.receivePurchaseOrder(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Order received into inventory.");
    },
  });
}

export function useCancelPurchaseOrder() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (id: string) => api.cancelPurchaseOrder(id),
    onSuccess: () => {
      invalidate();
      toast.success("Order cancelled.");
    },
  });
}
