/** TypeScript mirrors of backend/app/api/v1/schemas/*.py — the frontend's
 * only source of truth for API shapes (see docs/architecture.md's
 * "hand-written API client" scope decision: no OpenAPI codegen). Field
 * names and optionality match the Pydantic models exactly. */

import type {
  AlertSeverity,
  AlertType,
  AssignableRole,
  ForecastModelType,
  HospitalType,
  InventoryChangeReason,
  PurchaseOrderStatus,
  RecommendedBy,
  TransferStatus,
} from "./enums";

// --- Auth --------------------------------------------------------------

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role_name: string;
  is_active: boolean;
  hospital_id: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserAdminUpdateRequest {
  role_name?: AssignableRole;
  hospital_id?: string;
  clear_hospital?: boolean;
}

// --- Hospitals -----------------------------------------------------------

export interface HospitalRead {
  id: string;
  name: string;
  code: string;
  latitude: number;
  longitude: number;
  city: string;
  region: string;
  bed_capacity: number;
  occupancy_rate: number;
  type: HospitalType;
  is_active: boolean;
  created_at: string;
}

export interface HospitalCreate {
  name: string;
  code: string;
  latitude: number;
  longitude: number;
  city: string;
  region: string;
  bed_capacity: number;
  type: HospitalType;
}

// --- Medicines -------------------------------------------------------------

export interface MedicineRead {
  id: string;
  name: string;
  generic_name: string;
  atc_code: string | null;
  category: string;
  unit: string;
  unit_cost: number;
  requires_refrigeration: boolean;
  is_controlled: boolean;
  is_active: boolean;
  created_at: string;
}

export interface MedicineCreate {
  name: string;
  generic_name: string;
  category: string;
  unit: string;
  unit_cost: number;
  atc_code?: string | null;
  requires_refrigeration?: boolean;
  is_controlled?: boolean;
}

// --- Inventory ---------------------------------------------------------

export interface InventoryRead {
  id: string;
  hospital_id: string;
  medicine_id: string;
  batch_number: string;
  current_stock: number;
  safety_stock: number;
  available_stock: number;
  expiry_date: string;
  unit_cost_at_receipt: number;
  created_at: string;
  storage_location: string | null;
  manufactured_date: string | null;
  supplier_id: string | null;
}

export interface InventoryChangeRead {
  batch: InventoryRead;
  change_qty: number;
  reason: InventoryChangeReason;
  recorded_at: string;
}

export interface InventoryReceiveRequest {
  hospital_id: string;
  medicine_id: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  unit_cost_at_receipt: number;
  safety_stock?: number;
  storage_location?: string | null;
  manufactured_date?: string | null;
  supplier_id?: string | null;
}

// --- Transfers -----------------------------------------------------------

export interface TransferRead {
  id: string;
  source_hospital_id: string;
  destination_hospital_id: string;
  medicine_id: string;
  quantity: number;
  status: TransferStatus;
  created_at: string;
  recommended_by: RecommendedBy;
  created_by: string | null;
  distance_km: number | null;
  transportation_cost: number | null;
  expiry_prevented_value: number | null;
  completed_at: string | null;
}

export interface TransferProposeRequest {
  source_hospital_id: string;
  destination_hospital_id: string;
  medicine_id: string;
  quantity: number;
}

// --- Forecast ------------------------------------------------------------

export interface ForecastRead {
  id: string;
  hospital_id: string;
  medicine_id: string;
  horizon_days: number;
  model_used: ForecastModelType;
  predicted_demand: number;
  confidence_low: number;
  confidence_high: number;
  generated_at: string;
}

// --- Expiry ----------------------------------------------------------------

export interface ExpiryRiskRead {
  id: string;
  inventory_id: string;
  probability_expires_before_use: number;
  estimated_financial_loss: number;
  confidence_score: number;
  evaluated_at: string;
}

// --- Procurement ------------------------------------------------------------

export interface SupplierRead {
  id: string;
  name: string;
  contact_email: string | null;
  lead_time_days: number;
  reliability_score: number;
  is_active: boolean;
  created_at: string;
}

export interface SupplierCreate {
  name: string;
  lead_time_days: number;
  reliability_score?: number;
  contact_email?: string | null;
}

export interface PurchaseOrderRead {
  id: string;
  hospital_id: string;
  medicine_id: string;
  supplier_id: string;
  quantity: number;
  status: PurchaseOrderStatus;
  recommended_by: RecommendedBy;
  unit_cost: number;
  total_cost: number;
  created_at: string;
  expected_delivery_date: string | null;
}

export interface PurchaseOrderReceiveRequest {
  batch_number: string;
  expiry_date: string;
}

// --- Analytics -----------------------------------------------------------

export interface KPISummaryRead {
  medicine_waste_units: number;
  medicine_waste_value: number;
  transfers_completed: number;
  transfers_cancelled: number;
  transfer_success_rate: number | null;
  procurement_spend: number;
  procurement_orders_count: number;
  stockout_count: number;
  inventory_turnover_ratio: number | null;
  alerts_by_severity: Record<string, number>;
  alerts_unresolved_count: number;
  expiry_value_prevented: number;
  medicine_units_redistributed: number;
  co2_saved_kg_estimate: number;
  patients_impacted_count: number;
}

// --- Notifications (Alerts) -----------------------------------------------

export interface AlertRead {
  id: string;
  hospital_id: string;
  medicine_id: string | null;
  severity: AlertSeverity;
  type: AlertType;
  message: string;
  is_resolved: boolean;
  created_at: string;
}

// --- Assistant -------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  question: string;
  history?: ChatMessage[];
  hospital_id?: string | null;
}

export interface ChatResponse {
  answer: string;
}

export interface ExplanationResponse {
  explanation: string;
}

export * from "./enums";
