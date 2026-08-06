"use client";

import { Building2 } from "lucide-react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useCurrentUser } from "@/features/auth/hooks";
import type { useHospitalScope } from "@/hooks/useHospitalScope";

/** Renders the admin-only "which hospital am I looking at" dropdown, or a
 * static badge naming a non-admin's own hospital — the visible half of
 * `useHospitalScope`. */
export function HospitalScopeSelect({ scope }: { scope: ReturnType<typeof useHospitalScope> }) {
  const { data: user } = useCurrentUser();

  if (!scope.isAdmin) {
    const hospitalName = scope.hospitals.find((h) => h.id === user?.hospital_id)?.name;
    return (
      <Badge variant="outline" className="gap-1.5">
        <Building2 className="h-3 w-3" />
        {hospitalName ?? "Your hospital"}
      </Badge>
    );
  }

  return (
    <Select
      value={scope.selected ?? "network"}
      onValueChange={(value) => scope.setSelected(value === "network" ? null : value)}
    >
      <SelectTrigger className="w-56">
        <SelectValue placeholder="Network-wide" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="network">Network-wide</SelectItem>
        {scope.hospitals.map((hospital) => (
          <SelectItem key={hospital.id} value={hospital.id}>
            {hospital.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
