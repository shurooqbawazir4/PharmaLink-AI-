import { describe, expect, it } from "vitest";

import {
  canGenerateForecast,
  canManageHospitals,
  canManageTransfers,
  canRunOptimization,
  isAdmin,
  scopedHospitalId,
} from "@/lib/rbac";

describe("isAdmin", () => {
  it("is true only for the admin role", () => {
    expect(isAdmin("admin")).toBe(true);
    expect(isAdmin("pharmacist")).toBe(false);
    expect(isAdmin(null)).toBe(false);
    expect(isAdmin(undefined)).toBe(false);
  });
});

describe("role-gated helpers", () => {
  it("admin always passes regardless of the allowed list, mirroring require_role", () => {
    expect(canManageTransfers("admin")).toBe(true);
    expect(canManageHospitals("admin")).toBe(true);
  });

  it("pharmacist can manage transfers but not hospitals", () => {
    expect(canManageTransfers("pharmacist")).toBe(true);
    expect(canManageHospitals("pharmacist")).toBe(false);
  });

  it("viewer has full management access", () => {
    expect(canManageTransfers("viewer")).toBe(true);
    expect(canManageHospitals("viewer")).toBe(true);
  });

  it("optimization runs are admin-only regardless of any allowed-roles list", () => {
    expect(canRunOptimization("admin")).toBe(true);
    expect(canRunOptimization("hospital_manager")).toBe(false);
  });
});

describe("scopedHospitalId", () => {
  it("lets an admin view whatever hospital they select, or network-wide (null)", () => {
    expect(scopedHospitalId("admin", null, "hospital-42")).toBe("hospital-42");
    expect(scopedHospitalId("admin", null, null)).toBeNull();
  });

  it("locks a non-admin to their own hospital regardless of what's selected", () => {
    expect(scopedHospitalId("pharmacist", "hospital-1", "hospital-42")).toBe("hospital-1");
    expect(scopedHospitalId("pharmacist", "hospital-1", null)).toBe("hospital-1");
  });
});

describe("database wildcard permissions", () => {
  it("grants a viewer all actions and network-wide scope", () => {
    const user = { role_name: "viewer", permissions: ["*"] };
    expect(isAdmin(user)).toBe(true);
    expect(canGenerateForecast(user)).toBe(true);
    expect(canManageHospitals(user)).toBe(true);
    expect(canManageTransfers(user)).toBe(true);
    expect(canRunOptimization(user)).toBe(true);
    expect(scopedHospitalId(user, "own", "other")).toBe("other");
  });
  it("grants viewers full access even without database wildcard", () => {
    const user = { role_name: "viewer", permissions: [] };
    expect(isAdmin(user)).toBe(true);
    expect(canGenerateForecast(user)).toBe(true);
    expect(canRunOptimization(user)).toBe(true);
    expect(scopedHospitalId(user, "own", "other")).toBe("other");
  });
});
