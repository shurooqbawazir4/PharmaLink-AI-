"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import * as api from "@/features/notifications/api";
import type { AlertSeverity, AlertType } from "@/lib/types";

const KEY = ["alerts"] as const;

export function useAlerts(
  params: {
    hospitalId?: string;
    severity?: AlertSeverity;
    type?: AlertType;
    isResolved?: boolean;
  } = {}
) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: () => api.listAlerts(params),
  });
}

export function useResolveAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.resolveAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      toast.success("Alert resolved.");
    },
  });
}
