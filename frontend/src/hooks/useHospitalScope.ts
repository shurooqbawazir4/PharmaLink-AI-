"use client";

import { useState } from "react";

import { useCurrentUser } from "@/features/auth/hooks";
import { useHospitals } from "@/features/hospitals/hooks";
import { isAdmin, scopedHospitalId } from "@/lib/rbac";

/** The hospital-scope selector every network-wide page (Dashboard,
 * Analytics, Sustainability, Alerts, Procurement) needs: admins can pick
 * any hospital or view network-wide (null); everyone else is locked to
 * their own hospital, mirroring `require_own_hospital_or_admin` — see
 * lib/rbac.ts. */
export function useHospitalScope() {
  const { data: user } = useCurrentUser();
  const { data: hospitals = [] } = useHospitals();
  const [selected, setSelected] = useState<string | null>(null);

  const admin = isAdmin(user?.role_name);
  const hospitalId = scopedHospitalId(user?.role_name, user?.hospital_id, selected);

  return {
    hospitalId,
    isAdmin: admin,
    hospitals,
    selected,
    setSelected,
    ready: !!user,
  };
}
