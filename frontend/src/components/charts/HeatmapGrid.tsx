"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn, formatPercent } from "@/lib/utils";

// The validated sequential-blue ramp (see docs/architecture.md / the
// dataviz-skill reference palette) — light step = near zero, dark step =
// high magnitude. Bucketed into 7 steps rather than a continuous
// gradient so every cell's color is one of the pre-validated stops.
const SEQUENTIAL_STEPS = [
  "#cde2fb",
  "#9ec5f4",
  "#6da7ec",
  "#3987e5",
  "#2a78d6",
  "#1c5cab",
  "#0d366b",
];

function stepFor(ratio: number): string {
  const clamped = Math.max(0, Math.min(1, ratio));
  const index = Math.min(SEQUENTIAL_STEPS.length - 1, Math.floor(clamped * SEQUENTIAL_STEPS.length));
  return SEQUENTIAL_STEPS[index] ?? SEQUENTIAL_STEPS[0]!;
}

export interface HeatmapAxis {
  id: string;
  label: string;
}

interface HeatmapGridProps {
  rows: HeatmapAxis[];
  columns: HeatmapAxis[];
  /** Ratio in [0, 1] — callers normalize their own metric (e.g. current
   * stock / safety stock, capped at 1). `null` renders an empty cell
   * (no batch for that hospital × medicine pair, a real absence, not 0). */
  getValue: (rowId: string, columnId: string) => number | null;
  legendLabel?: string;
}

export function HeatmapGrid({ rows, columns, getValue, legendLabel = "Stock coverage" }: HeatmapGridProps) {
  if (rows.length === 0 || columns.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No data yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: `140px repeat(${columns.length}, minmax(48px, 1fr))` }}
      >
        <div />
        {columns.map((col) => (
          <div key={col.id} className="truncate px-1 text-center text-[11px] font-medium text-muted-foreground">
            {col.label}
          </div>
        ))}

        {rows.map((row) => (
          <FragmentRow key={row.id} row={row} columns={columns} getValue={getValue} />
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <span>{legendLabel}:</span>
        <span>Low</span>
        <div className="flex h-3 overflow-hidden rounded-sm">
          {SEQUENTIAL_STEPS.map((step) => (
            <div key={step} className="h-3 w-4" style={{ backgroundColor: step }} />
          ))}
        </div>
        <span>High</span>
      </div>
    </div>
  );
}

function FragmentRow({
  row,
  columns,
  getValue,
}: {
  row: HeatmapAxis;
  columns: HeatmapAxis[];
  getValue: (rowId: string, columnId: string) => number | null;
}) {
  return (
    <>
      <div className="truncate py-1 pr-2 text-xs font-medium">{row.label}</div>
      {columns.map((col) => {
        const value = getValue(row.id, col.id);
        return (
          <Tooltip key={col.id}>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  "aspect-square rounded-sm",
                  value === null && "border border-dashed border-border bg-transparent"
                )}
                style={value !== null ? { backgroundColor: stepFor(value) } : undefined}
              />
            </TooltipTrigger>
            <TooltipContent>
              {row.label} · {col.label}: {value === null ? "no stock" : formatPercent(value)}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </>
  );
}
