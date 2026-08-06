"use client";

import { useMemo } from "react";

import { useHospitals } from "@/features/hospitals/hooks";
import { useMedicines } from "@/features/medicines/hooks";
import { useSuppliers } from "@/features/procurement/hooks";

/** ID → display-name lookups, built once from the already-cached catalogue
 * queries (hospitals/medicines/suppliers are small, network-wide lists —
 * TanStack Query dedupes these against whatever page already fetched
 * them). Every table that shows a UUID-bearing row resolves it to a name
 * through this rather than displaying the raw id — the same UX standard
 * `AssistantService` applies server-side to LLM prompts. */
export function useLookupMaps() {
  const { data: hospitals = [] } = useHospitals();
  const { data: medicines = [] } = useMedicines();
  const { data: suppliers = [] } = useSuppliers();

  const hospitalName = useMemo(() => new Map(hospitals.map((h) => [h.id, h.name])), [hospitals]);
  const medicineName = useMemo(() => new Map(medicines.map((m) => [m.id, m.name])), [medicines]);
  const supplierName = useMemo(() => new Map(suppliers.map((s) => [s.id, s.name])), [suppliers]);

  return {
    hospitalName: (id: string) => hospitalName.get(id) ?? id.slice(0, 8),
    medicineName: (id: string) => medicineName.get(id) ?? id.slice(0, 8),
    supplierName: (id: string) => supplierName.get(id) ?? id.slice(0, 8),
    hospitals,
    medicines,
    suppliers,
  };
}
