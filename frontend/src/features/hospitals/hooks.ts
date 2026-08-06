"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/hospitals/api";
import type { HospitalCreate } from "@/lib/types";

const KEY = ["hospitals"] as const;

export function useHospitals(params: { region?: string; includeInactive?: boolean } = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: () => api.listHospitals(params),
  });
}

export function useHospital(id: string | undefined) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () => api.getHospital(id as string),
    enabled: !!id,
  });
}

export function useCreateHospital() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: HospitalCreate) => api.createHospital(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Hospital created.");
    },
  });
}

export function useUpdateHospitalOccupancy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, occupancyRate }: { id: string; occupancyRate: number }) =>
      api.updateHospitalOccupancy(id, occupancyRate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Occupancy updated.");
    },
  });
}

export function useDeactivateHospital() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deactivateHospital(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Hospital deactivated.");
    },
  });
}
