"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { CHART_AXIS_COLOR, CHART_COLORS, CHART_GRID_COLOR } from "@/components/charts/colors";

export interface LineChartPoint {
  label: string;
  value: number;
  /** Optional confidence band — rendered as a translucent area behind the
   * line. Only meaningful for one series (the forecast use case). */
  low?: number;
  high?: number;
}

interface LineChartCardProps {
  title: string;
  description?: string;
  data: LineChartPoint[];
  valueLabel: string;
  emptyMessage?: string;
}

/** Single-series line, optionally with a confidence band — the Forecast
 * page's demand-over-time chart. One axis (a second measure is a
 * different chart, never a second y-scale), thin 2px line, recessive
 * grid, hover tooltip. */
export function LineChartCard({
  title,
  description,
  data,
  valueLabel,
  emptyMessage = "No data yet.",
}: LineChartCardProps) {
  const hasBand = data.some((point) => point.low !== undefined && point.high !== undefined);

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
            <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={CHART_GRID_COLOR} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                stroke={CHART_AXIS_COLOR}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: CHART_GRID_COLOR }}
              />
              <YAxis
                stroke={CHART_AXIS_COLOR}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={40}
              />
              <Tooltip content={<ChartTooltip />} />
              {hasBand && (
                <Area
                  type="monotone"
                  dataKey="high"
                  stroke="none"
                  fill={CHART_COLORS[0]}
                  fillOpacity={0.12}
                  name="Confidence high"
                  isAnimationActive={false}
                />
              )}
              {hasBand && (
                <Area
                  type="monotone"
                  dataKey="low"
                  stroke="none"
                  fill="hsl(var(--card))"
                  fillOpacity={1}
                  name="Confidence low"
                  isAnimationActive={false}
                />
              )}
              <Line
                type="monotone"
                dataKey="value"
                name={valueLabel}
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={{ r: 3, fill: CHART_COLORS[0], strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
