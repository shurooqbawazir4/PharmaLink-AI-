"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/forecast/api";

const KEY = ["forecasts"] as const;

export function useForecasts(params: { hospitalId?: string; medicineId?: string } = {}) {
  return useQuery({
    queryKey: [...KEY, "list", params],
    queryFn: () => api.listForecasts(params),
    enabled: !!params.hospitalId && !!params.medicineId,
  });
}

export function useLatestForecast(hospitalId?: string, medicineId?: string) {
  return useQuery({
    queryKey: [...KEY, "latest", hospitalId, medicineId],
    queryFn: () => api.getLatestForecast(hospitalId as string, medicineId as string),
    enabled: !!hospitalId && !!medicineId,
  });
}

export function useGenerateForecast() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      hospitalId,
      medicineId,
      horizonDays,
    }: {
      hospitalId: string;
      medicineId: string;
      horizonDays?: number;
    }) => api.generateForecast(hospitalId, medicineId, horizonDays),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Forecast generated.");
    },
  });
}
