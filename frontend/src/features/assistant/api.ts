import { apiFetch } from "@/lib/api-client";
import type { ChatRequest, ChatResponse, ExplanationResponse } from "@/lib/types";

export function chat(payload: ChatRequest) {
  return apiFetch<ChatResponse>("/assistant/chat", { method: "POST", body: payload });
}

export function explainTransfer(transferId: string) {
  return apiFetch<ExplanationResponse>(`/assistant/explain/transfer/${transferId}`);
}

export function explainPurchaseOrder(orderId: string) {
  return apiFetch<ExplanationResponse>(`/assistant/explain/purchase-order/${orderId}`);
}
