"use client";

import { useState } from "react";
import { Ban, CheckCircle2, PackagePlus, Truck } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { PurchaseOrderStatusBadge, RecommendedByBadge } from "@/components/charts/StatusBadges";
import { ExplainButton } from "@/features/assistant/components/ExplainButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ReceiveOrderDialog } from "@/features/procurement/components/ReceiveOrderDialog";
import { SupplierFormDialog } from "@/features/procurement/components/SupplierFormDialog";
import {
  useApprovePurchaseOrder,
  useCancelPurchaseOrder,
  useDeactivateSupplier,
  useMarkPurchaseOrderOrdered,
  usePurchaseOrders,
  useRecommendPurchaseOrders,
  useSuppliers,
} from "@/features/procurement/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import { canManageProcurement, isAdmin } from "@/lib/rbac";
import { useCurrentUser } from "@/features/auth/hooks";
import type { PurchaseOrderStatus } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

const STATUSES: PurchaseOrderStatus[] = ["recommended", "approved", "ordered", "received", "cancelled"];

export default function ProcurementPage() {
  const { data: user } = useCurrentUser();
  const scope = useHospitalScope();
  const { hospitalName, medicineName, supplierName } = useLookupMaps();
  const canManage = canManageProcurement(user?.role_name);

  return (
    <div>
      <PageHeader
        title="Procurement"
        description="AI-recommended purchase orders and the supplier catalogue."
        actions={<HospitalScopeSelect scope={scope} />}
      />

      <Tabs defaultValue="orders">
        <TabsList>
          <TabsTrigger value="orders">Purchase orders</TabsTrigger>
          <TabsTrigger value="suppliers">Suppliers</TabsTrigger>
        </TabsList>

        <TabsContent value="orders">
          <PurchaseOrdersTab
            hospitalId={scope.hospitalId}
            canManage={canManage}
            hospitalName={hospitalName}
            medicineName={medicineName}
            supplierName={supplierName}
          />
        </TabsContent>

        <TabsContent value="suppliers">
          <SuppliersTab canManage={canManage} isAdminUser={isAdmin(user?.role_name)} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PurchaseOrdersTab({
  hospitalId,
  canManage,
  hospitalName,
  medicineName,
  supplierName,
}: {
  hospitalId: string | null;
  canManage: boolean;
  hospitalName: (id: string) => string;
  medicineName: (id: string) => string;
  supplierName: (id: string) => string;
}) {
  const [status, setStatus] = useState<PurchaseOrderStatus | "all">("all");
  const { data: orders = [], isLoading } = usePurchaseOrders({
    hospitalId: hospitalId ?? undefined,
    status: status === "all" ? undefined : status,
  });
  const recommend = useRecommendPurchaseOrders();
  const approve = useApprovePurchaseOrder();
  const markOrdered = useMarkPurchaseOrderOrdered();
  const cancel = useCancelPurchaseOrder();

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {canManage && hospitalId && (
          <Button
            size="sm"
            variant="outline"
            disabled={recommend.isPending}
            onClick={() => recommend.mutate(hospitalId)}
          >
            <PackagePlus className="h-4 w-4" /> Recommend reorders for this hospital
          </Button>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Medicine</TableHead>
                <TableHead>Hospital</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Total cost</TableHead>
                <TableHead>Expected delivery</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={8}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  </TableRow>
                ))
              ) : orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    No purchase orders match these filters.
                  </TableCell>
                </TableRow>
              ) : (
                orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <PurchaseOrderStatusBadge status={order.status} />
                        <RecommendedByBadge recommendedBy={order.recommended_by} />
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{medicineName(order.medicine_id)}</TableCell>
                    <TableCell className="text-sm">{hospitalName(order.hospital_id)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {supplierName(order.supplier_id)}
                    </TableCell>
                    <TableCell className="tabular-nums">{order.quantity}</TableCell>
                    <TableCell className="tabular-nums">{formatCurrency(order.total_cost)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {order.expected_delivery_date ? formatDate(order.expected_delivery_date) : "—"}
                    </TableCell>
                    <TableCell>
                      {canManage && (
                        <div className="flex items-center gap-1">
                          {order.status === "recommended" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={approve.isPending}
                              onClick={() => approve.mutate(order.id)}
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                            </Button>
                          )}
                          {order.status === "approved" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={markOrdered.isPending}
                              onClick={() => markOrdered.mutate(order.id)}
                            >
                              <Truck className="h-3.5 w-3.5" /> Mark ordered
                            </Button>
                          )}
                          {order.status === "ordered" && <ReceiveOrderDialog orderId={order.id} />}
                          {(order.status === "recommended" || order.status === "approved") && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={cancel.isPending}
                              onClick={() => cancel.mutate(order.id)}
                            >
                              <Ban className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <ExplainButton kind="purchase-order" id={order.id} />
                        </div>
                      )}
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

function SuppliersTab({ canManage, isAdminUser }: { canManage: boolean; isAdminUser: boolean }) {
  const { data: suppliers = [], isLoading } = useSuppliers({ includeInactive: true });
  const deactivate = useDeactivateSupplier();

  return (
    <div>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <SupplierFormDialog />
        </div>
      )}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Lead time</TableHead>
                <TableHead>Reliability</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={6}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                suppliers.map((supplier) => (
                  <TableRow key={supplier.id}>
                    <TableCell className="font-medium">{supplier.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {supplier.contact_email ?? "—"}
                    </TableCell>
                    <TableCell className="tabular-nums">{supplier.lead_time_days}d</TableCell>
                    <TableCell className="tabular-nums">
                      {(supplier.reliability_score * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      <Badge variant={supplier.is_active ? "success" : "outline"}>
                        {supplier.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {isAdminUser && supplier.is_active && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={deactivate.isPending}
                          onClick={() => deactivate.mutate(supplier.id)}
                        >
                          Deactivate
                        </Button>
                      )}
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
