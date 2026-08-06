"use client";

import Link from "next/link";
import { AlertTriangle, Package, PackageX, TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { KpiCard } from "@/components/charts/KpiCard";
import { AlertSeverityBadge } from "@/components/charts/StatusBadges";
import { HospitalMap } from "@/components/map/HospitalMap";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import { useKpiSummary } from "@/features/analytics/hooks";
import { useHighRiskExpiry } from "@/features/expiry/hooks";
import { useAlerts, useResolveAlert } from "@/features/notifications/hooks";
import { useInventory } from "@/features/inventory/hooks";
import { formatCurrency, formatPercent } from "@/lib/utils";

export default function DashboardPage() {
  const scope = useHospitalScope();
  const { hospitalName, medicineName } = useLookupMaps();
  const { data: kpis, isLoading: kpisLoading } = useKpiSummary(scope.hospitalId);
  const { data: highRisk = [] } = useHighRiskExpiry({ hospitalId: scope.hospitalId ?? undefined });
  const { data: unresolvedAlerts = [] } = useAlerts({
    hospitalId: scope.hospitalId ?? undefined,
    isResolved: false,
  });
  const { data: inventory = [] } = useInventory({ hospitalId: scope.hospitalId ?? undefined });
  const resolveAlert = useResolveAlert();

  const inventoryById = new Map(inventory.map((batch) => [batch.id, batch]));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Network-wide overview of demand, risk, and redistribution."
        actions={<HospitalScopeSelect scope={scope} />}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpisLoading || !kpis ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <KpiCard
              label="Unresolved alerts"
              value={String(kpis.alerts_unresolved_count)}
              icon={AlertTriangle}
              tone={kpis.alerts_unresolved_count > 0 ? "negative" : "positive"}
            />
            <KpiCard
              label="Stockouts"
              value={String(kpis.stockout_count)}
              icon={PackageX}
              tone={kpis.stockout_count > 0 ? "negative" : "positive"}
            />
            <KpiCard
              label="Transfer success rate"
              value={kpis.transfer_success_rate !== null ? formatPercent(kpis.transfer_success_rate) : "—"}
              icon={TrendingUp}
              tone="positive"
            />
            <KpiCard
              label="Medicine waste (value)"
              value={formatCurrency(kpis.medicine_waste_value)}
              icon={Package}
              hint={`${kpis.medicine_waste_units} units written off`}
              tone="negative"
            />
          </>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top expiry risks</CardTitle>
            <CardDescription>Highest probability-of-waste batches network-wide.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {highRisk.length === 0 ? (
              <p className="text-sm text-muted-foreground">No high-risk batches evaluated yet.</p>
            ) : (
              highRisk.slice(0, 5).map((risk) => {
                const batch = inventoryById.get(risk.inventory_id);
                return (
                  <div key={risk.id} className="flex items-center justify-between gap-3 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {batch ? medicineName(batch.medicine_id) : `Batch ${risk.inventory_id.slice(0, 8)}`}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {batch ? hospitalName(batch.hospital_id) : "—"} · loss estimate{" "}
                        {formatCurrency(risk.estimated_financial_loss)}
                      </p>
                    </div>
                    <Badge variant={risk.probability_expires_before_use >= 0.7 ? "destructive" : "warning"}>
                      {formatPercent(risk.probability_expires_before_use)}
                    </Badge>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent alerts</CardTitle>
            <CardDescription>Unresolved alerts requiring attention.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {unresolvedAlerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No unresolved alerts. Nice.</p>
            ) : (
              unresolvedAlerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="flex items-start justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <AlertSeverityBadge severity={alert.severity} />
                      <span className="truncate text-xs text-muted-foreground">
                        {hospitalName(alert.hospital_id)}
                      </span>
                    </div>
                    <p className="mt-1 truncate">{alert.message}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => resolveAlert.mutate(alert.id)}
                    disabled={resolveAlert.isPending}
                  >
                    Resolve
                  </Button>
                </div>
              ))
            )}
            {unresolvedAlerts.length > 5 && (
              <Link href="/alerts" className="text-xs font-medium text-primary hover:underline">
                View all {unresolvedAlerts.length} alerts →
              </Link>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Hospital network</CardTitle>
          <CardDescription>{scope.hospitals.length} hospitals in the network.</CardDescription>
        </CardHeader>
        <CardContent>
          <HospitalMap hospitals={scope.hospitals} className="h-96" />
        </CardContent>
      </Card>
    </div>
  );
}
