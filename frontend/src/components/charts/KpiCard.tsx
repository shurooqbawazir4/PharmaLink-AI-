import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  icon?: LucideIcon;
  /** Small supporting line under the value — a comparison, a unit
   * breakdown, or an explanation, never a second unrelated number. */
  hint?: string;
  /** "up"/"down" tints the hint text using the reserved status palette —
   * only pass this when the direction actually means good/bad (e.g.
   * transfer success up is good; waste value up is bad — the CALLER
   * decides which direction is "good" for its own metric). */
  tone?: "positive" | "negative" | "neutral";
  className?: string;
}

const TONE_CLASS: Record<NonNullable<KpiCardProps["tone"]>, string> = {
  positive: "text-success",
  negative: "text-destructive",
  neutral: "text-muted-foreground",
};

export function KpiCard({ label, value, icon: Icon, hint, tone = "neutral", className }: KpiCardProps) {
  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="tabular-nums text-2xl font-semibold leading-tight">{value}</p>
          {hint && <p className={cn("text-xs", TONE_CLASS[tone])}>{hint}</p>}
        </div>
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="h-4.5 w-4.5" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** For KPIs this project deliberately doesn't fabricate (forecast accuracy
 * today) — an honest "not enough data yet" state instead of a number. */
export function KpiCardEmpty({ label, reason }: { label: string; reason: string }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col gap-1 p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="text-sm text-muted-foreground">Not enough data yet</p>
        <p className="text-xs text-muted-foreground/80">{reason}</p>
      </CardContent>
    </Card>
  );
}
