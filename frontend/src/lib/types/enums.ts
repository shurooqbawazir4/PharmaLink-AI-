/** Mirrors backend/app/domain/shared/enums.py 1:1 — one definition there,
 * one here, kept in sync by hand (see docs/architecture.md's "hand-written
 * API client" scope decision). */

export type InventoryChangeReason =
  | "receipt"
  | "consumption"
  | "transfer_out"
  | "transfer_in"
  | "expiry_writeoff"
  | "adjustment";

export type TransferStatus = "proposed" | "approved" | "in_transit" | "completed" | "cancelled";

export type ForecastModelType = "chronos" | "lightgbm";

export type PurchaseOrderStatus = "recommended" | "approved" | "ordered" | "received" | "cancelled";

export type RecommendedBy = "ai" | "manual";

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertType = "shortage_risk" | "expiry_risk" | "low_stock" | "transfer_suggested";

export type HospitalType = "general" | "specialty" | "teaching" | "clinic";

export type AssignableRole = "admin" | "hospital_manager" | "pharmacist" | "viewer";
