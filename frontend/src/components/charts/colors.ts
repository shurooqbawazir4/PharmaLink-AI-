/** The fixed-order categorical palette from globals.css's --chart-1..8
 * tokens (see the dataviz-skill validated reference palette in
 * docs/architecture.md). Referenced as `hsl(var(--chart-N))` strings —
 * SVG accepts CSS custom properties directly, so these swap with the
 * light/dark theme with no JS re-computation needed. Assign in this fixed
 * order across a chart's series; never cycle or reassign by rank. */
export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
  "hsl(var(--chart-7))",
  "hsl(var(--chart-8))",
] as const;

/** Status colors — reserved for state (never a categorical series). */
export const STATUS_COLORS = {
  good: "hsl(var(--success))",
  warning: "hsl(var(--warning))",
  critical: "hsl(var(--destructive))",
} as const;

export const CHART_GRID_COLOR = "hsl(var(--border))";
export const CHART_AXIS_COLOR = "hsl(var(--muted-foreground))";
