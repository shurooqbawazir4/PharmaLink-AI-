"use client";

import { Snowflake, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { QuantityActionDialog } from "@/components/common/QuantityActionDialog";
import { MedicineFormDialog } from "@/features/medicines/components/MedicineFormDialog";
import { useDeactivateMedicine, useMedicines, useUpdateMedicineUnitCost } from "@/features/medicines/hooks";
import { useCurrentUser } from "@/features/auth/hooks";
import { canDeleteMedicines, canManageMedicines, isAdmin } from "@/lib/rbac";
import { formatCurrency } from "@/lib/utils";

export default function MedicinesPage() {
  const { data: user } = useCurrentUser();
  const { data: medicines = [], isLoading } = useMedicines();
  const updateCost = useUpdateMedicineUnitCost();
  const deactivate = useDeactivateMedicine();
  const canManage = canManageMedicines(user);

  return (
    <div>
      <PageHeader
        title="Medicines"
        description="The catalogue every inventory, forecast, and order references."
        actions={canManage ? <MedicineFormDialog /> : undefined}
      />

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Unit cost</TableHead>
                <TableHead>Flags</TableHead>
                <TableHead>Status</TableHead>
                {canManage && <TableHead />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                medicines.map((medicine) => (
                  <TableRow key={medicine.id}>
                    <TableCell>
                      <p className="font-medium">{medicine.name}</p>
                      <p className="text-xs text-muted-foreground">{medicine.generic_name}</p>
                    </TableCell>
                    <TableCell>{medicine.category}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{medicine.unit}</TableCell>
                    <TableCell className="tabular-nums">{formatCurrency(medicine.unit_cost)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {medicine.requires_refrigeration && (
                          <Badge variant="secondary" className="gap-1">
                            <Snowflake className="h-3 w-3" /> Cold chain
                          </Badge>
                        )}
                        {medicine.is_controlled && (
                          <Badge variant="warning" className="gap-1">
                            <ShieldAlert className="h-3 w-3" /> Controlled
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={medicine.is_active ? "success" : "destructive"}>
                        {medicine.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <QuantityActionDialog
                            trigger={
                              <Button variant="outline" size="sm">
                                Update cost
                              </Button>
                            }
                            title={`Update unit cost — ${medicine.name}`}
                            description="Enter the new per-unit cost."
                            label="Unit cost"
                            isPending={updateCost.isPending}
                            onSubmit={(unitCost) => updateCost.mutate({ id: medicine.id, unitCost })}
                          />
                          {isAdmin(user) && canDeleteMedicines(user) && medicine.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={deactivate.isPending}
                              onClick={() => deactivate.mutate(medicine.id)}
                            >
                              Deactivate
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    )}
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
