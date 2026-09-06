"use client";

import { useState } from "react";
import { MoreHorizontal, ShieldQuestion } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QuantityActionDialog } from "@/components/common/QuantityActionDialog";
import { ReceiveStockDialog } from "@/features/inventory/components/ReceiveStockDialog";
import {
  useAdjustStock,
  useConsumeStock,
  useInventory,
  useWriteOffExpired,
} from "@/features/inventory/hooks";
import { useEvaluateHospital, useHighRiskExpiry } from "@/features/expiry/hooks";
import { useDeactivateHospital, useUpdateHospitalOccupancy } from "@/features/hospitals/hooks";
import { useCurrentUser } from "@/features/auth/hooks";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import type { HospitalRead } from "@/lib/types";
import { canDeleteHospitals, canManageHospitals, canManageInventory } from "@/lib/rbac";
import { formatCurrency, formatDate, formatPercent } from "@/lib/utils";

export function HospitalDrilldown({
  hospital,
  open,
  onOpenChange,
}: {
  hospital: HospitalRead | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!hospital) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{hospital.name}</DialogTitle>
          <DialogDescription>
            {hospital.code} · {hospital.city}, {hospital.region}
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
            <TabsTrigger value="expiry">Expiry risk</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <OverviewTab hospital={hospital} />
          </TabsContent>
          <TabsContent value="inventory">
            <InventoryTab hospital={hospital} />
          </TabsContent>
          <TabsContent value="expiry">
            <ExpiryTab hospital={hospital} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

function OverviewTab({ hospital }: { hospital: HospitalRead }) {
  const { data: user } = useCurrentUser();
  const [occupancy, setOccupancy] = useState(String(hospital.occupancy_rate));
  const updateOccupancy = useUpdateHospitalOccupancy();
  const deactivate = useDeactivateHospital();

  return (
    <div className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <p className="text-xs text-muted-foreground">Type</p>
        <p className="mt-0.5 capitalize">{hospital.type}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Bed capacity</p>
        <p className="mt-0.5">{hospital.bed_capacity}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Occupancy</p>
        <p className="mt-0.5">{formatPercent(hospital.occupancy_rate)}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Status</p>
        <Badge variant={hospital.is_active ? "success" : "destructive"} className="mt-0.5">
          {hospital.is_active ? "Active" : "Inactive"}
        </Badge>
      </div>

      {canManageHospitals(user) && (
        <div className="col-span-2 flex items-end gap-2 border-t border-border pt-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground" htmlFor="occupancy">
              Update occupancy (0–1)
            </label>
            <Input
              id="occupancy"
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={occupancy}
              onChange={(event) => setOccupancy(event.target.value)}
              className="w-32"
            />
          </div>
          <Button
            size="sm"
            variant="secondary"
            disabled={updateOccupancy.isPending}
            onClick={() =>
              updateOccupancy.mutate({ id: hospital.id, occupancyRate: Number(occupancy) })
            }
          >
            Save
          </Button>
          {canDeleteHospitals(user) && hospital.is_active && (
            <Button
              size="sm"
              variant="outline"
              className="ml-auto"
              disabled={deactivate.isPending}
              onClick={() => deactivate.mutate(hospital.id)}
            >
              Deactivate
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function InventoryTab({ hospital }: { hospital: HospitalRead }) {
  const { data: user } = useCurrentUser();
  const { data: batches = [], isLoading } = useInventory({ hospitalId: hospital.id });
  const { medicineName } = useLookupMaps();
  const consume = useConsumeStock();
  const writeOff = useWriteOffExpired();
  const adjust = useAdjustStock();
  const canManage = canManageInventory(user);

  return (
    <div>
      {canManage && (
        <div className="mb-3 flex justify-end">
          <ReceiveStockDialog hospitalId={hospital.id} />
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Medicine</TableHead>
            <TableHead>Batch</TableHead>
            <TableHead>Stock</TableHead>
            <TableHead>Safety</TableHead>
            <TableHead>Expiry</TableHead>
            {canManage && <TableHead className="w-10" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                Loading…
              </TableCell>
            </TableRow>
          ) : batches.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                No inventory batches yet.
              </TableCell>
            </TableRow>
          ) : (
            batches.map((batch) => (
              <TableRow key={batch.id}>
                <TableCell className="font-medium">{medicineName(batch.medicine_id)}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{batch.batch_number}</TableCell>
                <TableCell className="tabular-nums">
                  {batch.current_stock}{" "}
                  <span className="text-xs text-muted-foreground">({batch.available_stock} avail.)</span>
                </TableCell>
                <TableCell className="tabular-nums">{batch.safety_stock}</TableCell>
                <TableCell className="text-xs">{formatDate(batch.expiry_date)}</TableCell>
                {canManage && (
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <QuantityActionDialog
                          trigger={<DropdownMenuItem onSelect={(e) => e.preventDefault()}>Consume</DropdownMenuItem>}
                          title="Consume stock"
                          description={`Record consumption from batch ${batch.batch_number}.`}
                          label="Quantity"
                          isPending={consume.isPending}
                          onSubmit={(quantity) => consume.mutate({ id: batch.id, quantity })}
                        />
                        <QuantityActionDialog
                          trigger={<DropdownMenuItem onSelect={(e) => e.preventDefault()}>Adjust</DropdownMenuItem>}
                          title="Adjust stock"
                          description="Positive to add, negative to remove."
                          label="Change (+/-)"
                          allowNegative
                          isPending={adjust.isPending}
                          onSubmit={(changeQty) => adjust.mutate({ id: batch.id, changeQty })}
                        />
                        <DropdownMenuItem onClick={() => writeOff.mutate(batch.id)}>
                          Write off (expired)
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                )}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function ExpiryTab({ hospital }: { hospital: HospitalRead }) {
  const { data: user } = useCurrentUser();
  const { data: risks = [], isLoading } = useHighRiskExpiry({ hospitalId: hospital.id, threshold: 0 });
  const { data: batches = [] } = useInventory({ hospitalId: hospital.id });
  const { medicineName } = useLookupMaps();
  const evaluateHospital = useEvaluateHospital();
  const batchById = new Map(batches.map((b) => [b.id, b]));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {risks.length} batch{risks.length === 1 ? "" : "es"} evaluated.
        </p>
        {canManageInventory(user) && (
          <Button
            size="sm"
            variant="secondary"
            disabled={evaluateHospital.isPending}
            onClick={() => evaluateHospital.mutate(hospital.id)}
          >
            <ShieldQuestion className="h-4 w-4" /> Re-evaluate all
          </Button>
        )}
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Medicine</TableHead>
            <TableHead>Probability</TableHead>
            <TableHead>Est. loss</TableHead>
            <TableHead>Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                Loading…
              </TableCell>
            </TableRow>
          ) : risks.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                No evaluations yet — run &quot;Re-evaluate all&quot;.
              </TableCell>
            </TableRow>
          ) : (
            risks.map((risk) => {
              const batch = batchById.get(risk.inventory_id);
              return (
                <TableRow key={risk.id}>
                  <TableCell className="font-medium">
                    {batch ? medicineName(batch.medicine_id) : risk.inventory_id.slice(0, 8)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={risk.probability_expires_before_use >= 0.7 ? "destructive" : "warning"}>
                      {formatPercent(risk.probability_expires_before_use)}
                    </Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {formatCurrency(risk.estimated_financial_loss)}
                  </TableCell>
                  <TableCell className="tabular-nums text-xs text-muted-foreground">
                    {formatPercent(risk.confidence_score)}
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
