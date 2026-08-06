"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { CHART_AXIS_COLOR, CHART_COLORS, CHART_GRID_COLOR } from "@/components/charts/colors";

export interface BarChartPoint {
  label: string;
  value: number;
  /** Per-bar color override — used for status-colored bars (e.g. alert
   * severity) where color carries meaning beyond series identity. Falls
   * back to the fixed categorical order when omitted. */
  color?: string;
}

interface BarChartCardProps {
  title: string;
  description?: string;
  data: BarChartPoint[];
  valueLabel: string;
  emptyMessage?: string;
  horizontal?: boolean;
}

export function BarChartCard({
  title,
  description,
  data,
  valueLabel,
  emptyMessage = "No data yet.",
  horizontal = false,
}: BarChartCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="flex h-64 items-center justify-center text-sm text-muted-foreground">
            {emptyMessage}
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={data}
              layout={horizontal ? "vertical" : "horizontal"}
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid stroke={CHART_GRID_COLOR} strokeDasharray="3 3" vertical={horizontal} horizontal={!horizontal} />
              {horizontal ? (
                <>
                  <XAxis type="number" stroke={CHART_AXIS_COLOR} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="label"
                    stroke={CHART_AXIS_COLOR}
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={100}
                  />
                </>
              ) : (
                <>
                  <XAxis
                    dataKey="label"
                    stroke={CHART_AXIS_COLOR}
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: CHART_GRID_COLOR }}
                  />
                  <YAxis stroke={CHART_AXIS_COLOR} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={40} />
                </>
              )}
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="value" name={valueLabel} radius={[4, 4, 4, 4]} maxBarSize={40}>
                {data.map((point, index) => (
                  <Cell key={point.label} fill={point.color ?? CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
