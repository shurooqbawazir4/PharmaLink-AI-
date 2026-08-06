"use client";

import { useEffect, useState } from "react";
import { Shuffle } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { HospitalMap, type TransferArc } from "@/components/map/HospitalMap";
import { RecommendedByBadge, TransferStatusBadge } from "@/components/charts/StatusBadges";
import { ExplainButton } from "@/features/assistant/components/ExplainButton";
import { useCurrentUser } from "@/features/auth/hooks";
import { useMedicines } from "@/features/medicines/hooks";
import { useHospitals } from "@/features/hospitals/hooks";
import { useTransfers } from "@/features/transfers/hooks";
import { useOptimizeNetworkTransfers } from "@/features/optimization/hooks";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import { canRunOptimization } from "@/lib/rbac";
import { formatDateTime } from "@/lib/utils";

export default function OptimizationPage() {
  const { data: user } = useCurrentUser();
  const { data: medicines = [] } = useMedicines();
  const { data: hospitals = [] } = useHospitals();
  const [medicineId, setMedicineId] = useState<string | undefined>(undefined);
  const { medicineName } = useLookupMaps();

  useEffect(() => {
    if (!medicineId && medicines.length > 0) setMedicineId(medicines[0]?.id);
  }, [medicines, medicineId]);

  const { data: transfers = [] } = useTransfers({ medicineId });
  const optimize = useOptimizeNetworkTransfers();

  const hospitalById = new Map(hospitals.map((h) => [h.id, h]));
  const arcs: TransferArc[] = transfers
    .filter((t) => t.status !== "cancelled")
    .flatMap((t): TransferArc[] => {
      const source = hospitalById.get(t.source_hospital_id);
      const destination = hospitalById.get(t.destination_hospital_id);
      if (!source || !destination) return [];
      return [
        {
          id: t.id,
          source,
          destination,
          color: t.recommended_by === "ai" ? "hsl(var(--chart-1))" : "hsl(var(--muted-foreground))",
        },
      ];
    });

  return (
    <div>
      <PageHeader
        title="Optimization"
        description="OR-Tools network transfer solver — surplus hospitals to deficit hospitals."
      />

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Run a network optimization</CardTitle>
          <CardDescription>
            {canRunOptimization(user?.role_name)
              ? "Admin-only — spans the whole network, not one hospital."
              : "Viewing only — running an optimization is restricted to admins."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Medicine</Label>
            <Select value={medicineId} onValueChange={setMedicineId}>
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Choose a medicine" />
              </SelectTrigger>
              <SelectContent>
                {medicines.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {canRunOptimization(user?.role_name) && (
            <Button
              disabled={!medicineId || optimize.isPending}
              onClick={() => medicineId && optimize.mutate(medicineId)}
            >
              <Shuffle className="h-4 w-4" /> {optimize.isPending ? "Solving…" : "Run optimization"}
            </Button>
          )}
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Transfer network</CardTitle>
          <CardDescription>
            Blue dashed lines are AI-recommended; gray are manually proposed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <HospitalMap hospitals={hospitals} arcs={arcs} className="h-96" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Transfers for {medicineId ? medicineName(medicineId) : "—"}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Route</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Recommended by</TableHead>
                <TableHead>Proposed</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {transfers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No transfers proposed for this medicine yet.
                  </TableCell>
                </TableRow>
              ) : (
                transfers.map((transfer) => (
                  <TableRow key={transfer.id}>
                    <TableCell className="text-sm">
                      {hospitalById.get(transfer.source_hospital_id)?.name ?? "—"} →{" "}
                      {hospitalById.get(transfer.destination_hospital_id)?.name ?? "—"}
                    </TableCell>
                    <TableCell className="tabular-nums">{transfer.quantity}</TableCell>
                    <TableCell>
                      <TransferStatusBadge status={transfer.status} />
                    </TableCell>
                    <TableCell>
                      <RecommendedByBadge recommendedBy={transfer.recommended_by} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTime(transfer.created_at)}
                    </TableCell>
                    <TableCell>
                      <ExplainButton kind="transfer" id={transfer.id} />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
