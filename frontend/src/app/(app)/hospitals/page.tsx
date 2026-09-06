"use client";

import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalMap } from "@/components/map/HospitalMap";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { HospitalFormDialog } from "@/features/hospitals/components/HospitalFormDialog";
import { HospitalDrilldown } from "@/features/hospitals/components/HospitalDrilldown";
import { useHospitals } from "@/features/hospitals/hooks";
import { useCurrentUser } from "@/features/auth/hooks";
import { canManageHospitals } from "@/lib/rbac";
import { formatPercent } from "@/lib/utils";
import type { HospitalRead } from "@/lib/types";

export default function HospitalsPage() {
  const { data: user } = useCurrentUser();
  const { data: hospitals = [], isLoading } = useHospitals();
  const [selected, setSelected] = useState<HospitalRead | null>(null);

  return (
    <div>
      <PageHeader
        title="Hospitals"
        description="Network node registry — click a hospital to manage its inventory."
        actions={canManageHospitals(user) ? <HospitalFormDialog /> : undefined}
      />

      <Card className="mb-4">
        <CardContent className="p-4">
          <HospitalMap
            hospitals={hospitals}
            selectedHospitalId={selected?.id}
            onSelectHospital={(id) => setSelected(hospitals.find((h) => h.id === id) ?? null)}
            className="h-80"
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>City / Region</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Occupancy</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                hospitals.map((hospital) => (
                  <TableRow key={hospital.id}>
                    <TableCell className="font-medium">{hospital.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{hospital.code}</TableCell>
                    <TableCell>
                      {hospital.city}, {hospital.region}
                    </TableCell>
                    <TableCell className="capitalize">{hospital.type}</TableCell>
                    <TableCell className="tabular-nums">{formatPercent(hospital.occupancy_rate)}</TableCell>
                    <TableCell>
                      <Badge variant={hospital.is_active ? "success" : "destructive"}>
                        {hospital.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => setSelected(hospital)}>
                        Manage
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <HospitalDrilldown hospital={selected} open={!!selected} onOpenChange={(open) => !open && setSelected(null)} />
    </div>
  );
}
