"use client";

import { Leaf, PackageCheck, ShieldCheck, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { BarChartCard, type BarChartPoint } from "@/components/charts/BarChartCard";
import { KpiCard } from "@/components/charts/KpiCard";
import { STATUS_COLORS } from "@/components/charts/colors";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useKpiSummary } from "@/features/analytics/hooks";
import { useExpiringSoon } from "@/features/inventory/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import { daysUntil, formatCurrency, formatNumber } from "@/lib/utils";

export default function SustainabilityPage() {
  const scope = useHospitalScope();
  const { medicineName, hospitalName } = useLookupMaps();
  const { data: kpis, isLoading } = useKpiSummary(scope.hospitalId);
  const { data: expiringSoon = [] } = useExpiringSoon({
    hospitalId: scope.hospitalId ?? undefined,
    withinDays: 60,
  });

  const timelineData: BarChartPoint[] = expiringSoon
    .slice()
    .sort((a, b) => daysUntil(a.expiry_date) - daysUntil(b.expiry_date))
    .slice(0, 10)
    .map((batch) => {
      const days = daysUntil(batch.expiry_date);
      return {
        label: `${medicineName(batch.medicine_id)} · ${hospitalName(batch.hospital_id)}`,
        value: days,
        color: days <= 7 ? STATUS_COLORS.critical : days <= 21 ? STATUS_COLORS.warning : STATUS_COLORS.good,
      };
    });

  return (
    <div>
      <PageHeader
        title="Sustainability"
        description="The redistribution story: waste prevented through transfers, not waste that already happened."
        actions={<HospitalScopeSelect scope={scope} />}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading || !kpis ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <KpiCard
              label="Waste value prevented"
              value={formatCurrency(kpis.expiry_value_prevented)}
              hint="Near-expiry stock value redirected by completed transfers"
              icon={ShieldCheck}
              tone="positive"
            />
            <KpiCard
              label="Units redistributed"
              value={formatNumber(kpis.medicine_units_redistributed)}
              hint="Total quantity moved by completed transfers"
              icon={PackageCheck}
              tone="positive"
            />
            <KpiCard
              label="CO₂ saved (estimate)"
              value={`${formatNumber(kpis.co2_saved_kg_estimate)} kg`}
              hint="Illustrative estimate, not a measured figure — see docs/database.md"
              icon={Leaf}
              tone="positive"
            />
            <KpiCard
              label="Waste that did occur"
              value={formatCurrency(kpis.medicine_waste_value)}
              hint={`${formatNumber(kpis.medicine_waste_units)} units written off — the contrast case`}
              icon={Trash2}
              tone="negative"
            />
          </>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard
          title="Expiry timeline"
          description="Batches expiring soonest, network-wide — the pool active redistribution draws from."
          data={timelineData}
          valueLabel="Days until expiry"
          emptyMessage="No batches expiring within 60 days."
          horizontal
        />

        <Card>
          <CardHeader>
            <CardTitle>How the CO₂ estimate works</CardTitle>
            <CardDescription>Full methodology in docs/database.md.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-relaxed text-muted-foreground">
            <p>
              Every completed transfer moves real medicine units that would otherwise have sat idle
              (and risked expiry) at the source hospital. The CO₂ figure multiplies those redistributed
              units by a fixed, documented per-unit estimate drawn from a rough pharmaceutical-
              manufacturing carbon-footprint ballpark — it is explicitly an illustrative planning figure,
              not a measured emissions value, and is labeled as such everywhere it&apos;s shown.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
