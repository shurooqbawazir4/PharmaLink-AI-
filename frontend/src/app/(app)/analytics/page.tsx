"use client";

import { Package, RefreshCw, ShoppingBag, TrendingUp, Users } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { BarChartCard, type BarChartPoint } from "@/components/charts/BarChartCard";
import { KpiCard, KpiCardEmpty } from "@/components/charts/KpiCard";
import { STATUS_COLORS } from "@/components/charts/colors";
import { Skeleton } from "@/components/ui/skeleton";
import { useKpiSummary } from "@/features/analytics/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";

const SEVERITY_COLOR: Record<string, string> = {
  critical: STATUS_COLORS.critical,
  warning: STATUS_COLORS.warning,
  info: STATUS_COLORS.good,
};

export default function AnalyticsPage() {
  const scope = useHospitalScope();
  const { data: kpis, isLoading } = useKpiSummary(scope.hospitalId);

  const alertsData: BarChartPoint[] = kpis
    ? Object.entries(kpis.alerts_by_severity).map(([severity, count]) => ({
        label: severity,
        value: count,
        color: SEVERITY_COLOR[severity],
      }))
    : [];

  const transferOutcomeData: BarChartPoint[] = kpis
    ? [
        { label: "Completed", value: kpis.transfers_completed, color: STATUS_COLORS.good },
        { label: "Cancelled", value: kpis.transfers_cancelled, color: STATUS_COLORS.critical },
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Operational and financial KPIs — medicine waste, transfers, procurement, inventory."
        actions={<HospitalScopeSelect scope={scope} />}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading || !kpis ? (
          Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <KpiCard
              label="Medicine waste"
              value={formatCurrency(kpis.medicine_waste_value)}
              hint={`${formatNumber(kpis.medicine_waste_units)} units written off`}
              icon={Package}
              tone="negative"
            />
            <KpiCard
              label="Transfer success rate"
              value={kpis.transfer_success_rate !== null ? formatPercent(kpis.transfer_success_rate) : "—"}
              hint={`${kpis.transfers_completed} completed / ${kpis.transfers_cancelled} cancelled`}
              icon={TrendingUp}
              tone="positive"
            />
            <KpiCard
              label="Inventory turnover"
              value={kpis.inventory_turnover_ratio !== null ? kpis.inventory_turnover_ratio.toFixed(2) : "—"}
              hint="90-day consumption ÷ current stock"
              icon={RefreshCw}
              tone="neutral"
            />
            <KpiCard
              label="Procurement spend"
              value={formatCurrency(kpis.procurement_spend)}
              hint={`${kpis.procurement_orders_count} active orders`}
              icon={ShoppingBag}
              tone="neutral"
            />
            <KpiCard
              label="Patients impacted"
              value={formatNumber(kpis.patients_impacted_count)}
              hint="Distinct patients with recorded consumption, trailing 90 days"
              icon={Users}
              tone="positive"
            />
            <KpiCardEmpty
              label="Forecast accuracy"
              reason="Forecasts predict forward from today — there's no elapsed history yet to compare predictions against actual consumption."
            />
          </>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard
          title="Alerts by severity"
          description="Currently open + resolved alerts in scope, grouped by severity."
          data={alertsData}
          valueLabel="Alerts"
          emptyMessage="No alerts recorded yet."
        />
        <BarChartCard
          title="Transfer outcomes"
          description="Completed vs. cancelled transfers — the transfer success rate's raw counts."
          data={transferOutcomeData}
          valueLabel="Transfers"
          emptyMessage="No completed or cancelled transfers yet."
        />
      </div>
    </div>
  );
}
