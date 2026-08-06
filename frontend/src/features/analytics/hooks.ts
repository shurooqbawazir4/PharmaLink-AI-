"use client";

import { useQuery } from "@tanstack/react-query";

import * as api from "@/features/analytics/api";

export function useKpiSummary(hospitalId?: string | null) {
  return useQuery({
    queryKey: ["analytics", "kpis", hospitalId ?? "network"],
    queryFn: () => api.getKpiSummary(hospitalId),
  });
}
