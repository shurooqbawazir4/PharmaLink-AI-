"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { KpiCard } from "@/components/charts/KpiCard";
import { LineChartCard, type LineChartPoint } from "@/components/charts/LineChartCard";
import { ForecastModelBadge } from "@/components/charts/StatusBadges";
import { useCurrentUser } from "@/features/auth/hooks";
import { useForecasts, useGenerateForecast, useLatestForecast } from "@/features/forecast/hooks";
import { useMedicines } from "@/features/medicines/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { canGenerateForecast, isAdmin } from "@/lib/rbac";
import { formatDate, formatNumber } from "@/lib/utils";

export default function ForecastPage() {
  const { data: user } = useCurrentUser();
  const scope = useHospitalScope();
  const { data: medicines = [] } = useMedicines();
  const [medicineId, setMedicineId] = useState<string | undefined>(undefined);
  const [horizonDays, setHorizonDays] = useState(30);

  useEffect(() => {
    if (!medicineId && medicines.length > 0) setMedicineId(medicines[0]?.id);
  }, [medicines, medicineId]);

  // Admins must pick a hospital explicitly — there's no "network-wide"
  // forecast, it's always for one hospital × medicine pair.
  const hospitalId = scope.hospitalId ?? (isAdmin(user?.role_name) ? scope.selected : null);

  const { data: forecasts = [] } = useForecasts({ hospitalId: hospitalId ?? undefined, medicineId });
  const { data: latest } = useLatestForecast(hospitalId ?? undefined, medicineId);
  const generate = useGenerateForecast();

  const points: LineChartPoint[] = forecasts
    .slice()
    .sort((a, b) => new Date(a.generated_at).getTime() - new Date(b.generated_at).getTime())
    .map((f) => ({
      label: formatDate(f.generated_at),
      value: f.predicted_demand,
      low: f.confidence_low,
      high: f.confidence_high,
    }));

  return (
    <div>
      <PageHeader
        title="Forecast"
        description="LightGBM demand forecasts, trained on real consumption + weather history."
      />

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Select a pair</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          {isAdmin(user?.role_name) && (
            <div className="flex flex-col gap-1.5">
              <Label>Hospital</Label>
              <Select value={scope.selected ?? undefined} onValueChange={scope.setSelected}>
                <SelectTrigger className="w-56">
                  <SelectValue placeholder="Choose a hospital" />
                </SelectTrigger>
                <SelectContent>
                  {scope.hospitals.map((h) => (
                    <SelectItem key={h.id} value={h.id}>
                      {h.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
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
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="horizon">Horizon (days)</Label>
            <Input
              id="horizon"
              type="number"
              min={1}
              max={365}
              value={horizonDays}
              onChange={(e) => setHorizonDays(Number(e.target.value))}
              className="w-28"
            />
          </div>
          {canGenerateForecast(user?.role_name) && (
            <Button
              disabled={!hospitalId || !medicineId || generate.isPending}
              onClick={() => hospitalId && medicineId && generate.mutate({ hospitalId, medicineId, horizonDays })}
            >
              <Sparkles className="h-4 w-4" /> {generate.isPending ? "Generating…" : "Generate forecast"}
            </Button>
          )}
        </CardContent>
      </Card>

      {!hospitalId || !medicineId ? (
        <p className="text-sm text-muted-foreground">Select a hospital and medicine to see forecasts.</p>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard
              label="Predicted demand"
              value={latest ? formatNumber(Math.round(latest.predicted_demand)) : "—"}
              hint={latest ? `over ${latest.horizon_days} days` : "No forecast generated yet"}
            />
            <KpiCard
              label="Confidence range"
              value={
                latest
                  ? `${formatNumber(Math.round(latest.confidence_low))}–${formatNumber(Math.round(latest.confidence_high))}`
                  : "—"
              }
            />
            <Card>
              <CardContent className="flex flex-col gap-2 p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Model</p>
                {latest ? <ForecastModelBadge model={latest.model_used} /> : <span className="text-sm text-muted-foreground">—</span>}
              </CardContent>
            </Card>
          </div>

          <LineChartCard
            title="Forecast history"
            description="Predicted demand per generation run, with confidence band."
            data={points}
            valueLabel="Predicted demand"
            emptyMessage="No forecast generated yet for this pair — generate one above."
          />
        </>
      )}
    </div>
  );
}
