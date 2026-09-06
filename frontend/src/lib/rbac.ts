/** Client-side RBAC helpers — UX convenience only (hide/disable actions a
 * user can't perform), mirroring backend/app/api/v1/deps.py's
 * `require_role`/`require_own_hospital_or_admin`. The backend remains the
 * actual enforcement boundary: every one of these checks is duplicated
 * server-side and would reject the request even if the UI didn't hide the
 * button first. See docs/architecture.md. */

export type Role = "admin" | "hospital_manager" | "pharmacist" | "viewer" | string;

type AccessSubject = Role | { role_name: string; permissions?: readonly string[] };

export function isAdmin(role: AccessSubject | undefined | null): boolean {
  return typeof role === "object" && role !== null
    ? role.role_name === "admin" || !!role.permissions?.includes("*")
    : role === "admin";
}

/** `require_role("admin", ...)` always passes admin regardless of the
 * explicit list — mirrored here so every helper below stays consistent
 * with the backend without repeating the admin check at each call site. */
function hasRole(role: AccessSubject | undefined | null, allowed: readonly Role[]): boolean {
  if (!role) return false;
  return isAdmin(role) || allowed.includes(typeof role === "object" ? role.role_name : role);
}

const STOCK_MANAGER_ROLES = ["admin", "hospital_manager", "pharmacist"] as const;
const TRANSFER_MANAGER_ROLES = ["admin", "hospital_manager", "pharmacist"] as const;
const EXPIRY_MANAGER_ROLES = ["admin", "hospital_manager", "pharmacist"] as const;
const FORECAST_MANAGER_ROLES = ["admin", "hospital_manager", "pharmacist"] as const;

export const canManageInventory = (role: AccessSubject | undefined | null) => hasRole(role, STOCK_MANAGER_ROLES);
export const canManageTransfers = (role: AccessSubject | undefined | null) => hasRole(role, TRANSFER_MANAGER_ROLES);
export const canManageExpiry = (role: AccessSubject | undefined | null) => hasRole(role, EXPIRY_MANAGER_ROLES);
export const canGenerateForecast = (role: AccessSubject | undefined | null) => hasRole(role, FORECAST_MANAGER_ROLES);

/** Hospitals: create/update-occupancy = admin or hospital_manager; delete = admin only. */
export const canManageHospitals = (role: AccessSubject | undefined | null) =>
  hasRole(role, ["admin", "hospital_manager"]);
export const canDeleteHospitals = isAdmin;

/** Medicines: create/update-cost = admin or pharmacist; delete = admin only. */
export const canManageMedicines = (role: AccessSubject | undefined | null) => hasRole(role, ["admin", "pharmacist"]);
export const canDeleteMedicines = isAdmin;

/** Optimization runs are network-wide by design — admin only, no hospital scope. */
export const canRunOptimization = isAdmin;

/** Non-admins are always scoped to their own hospital, regardless of what
 * they select in the UI — mirrors `require_own_hospital_or_admin`. Returns
 * the hospital id a given user's requests must be scoped to, or null for
 * an admin viewing network-wide. */
export function scopedHospitalId(
  role: AccessSubject | undefined | null,
  userHospitalId: string | null | undefined,
  selectedHospitalId: string | null | undefined
): string | null {
  if (isAdmin(role)) return selectedHospitalId ?? null;
  return userHospitalId ?? null;
}
