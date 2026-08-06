"use client";

import { useMutation } from "@tanstack/react-query";

import * as api from "@/features/assistant/api";
import type { ChatRequest } from "@/lib/types";

export function useChat() {
  return useMutation({
    mutationFn: (payload: ChatRequest) => api.chat(payload),
  });
}

/** On-demand "explain this" actions (transfer/purchase-order rows elsewhere
 * in the app) — modeled as mutations rather than queries since they're
 * triggered by a click, not rendered on page load, and there's nothing to
 * invalidate/cache. */
export function useExplainTransfer() {
  return useMutation({
    mutationFn: (transferId: string) => api.explainTransfer(transferId),
  });
}

export function useExplainPurchaseOrder() {
  return useMutation({
    mutationFn: (orderId: string) => api.explainPurchaseOrder(orderId),
  });
}
