import { AlertTriangle, Info, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type {
  AlertSeverity,
  ForecastModelType,
  PurchaseOrderStatus,
  RecommendedBy,
  TransferStatus,
} from "@/lib/types";

// Status colors always ship with an icon + label, never color alone (see
// docs/architecture.md's dataviz palette note).
export function AlertSeverityBadge({ severity }: { severity: AlertSeverity }) {
  switch (severity) {
    case "critical":
      return (
        <Badge variant="destructive">
          <ShieldAlert className="h-3 w-3" /> Critical
        </Badge>
      );
    case "warning":
      return (
        <Badge variant="warning">
          <AlertTriangle className="h-3 w-3" /> Warning
        </Badge>
      );
    default:
      return (
        <Badge variant="outline">
          <Info className="h-3 w-3" /> Info
        </Badge>
      );
  }
}

const TRANSFER_STATUS_VARIANT: Record<TransferStatus, "outline" | "secondary" | "success" | "destructive"> = {
  proposed: "outline",
  approved: "secondary",
  in_transit: "secondary",
  completed: "success",
  cancelled: "destructive",
};

export function TransferStatusBadge({ status }: { status: TransferStatus }) {
  return <Badge variant={TRANSFER_STATUS_VARIANT[status]}>{status.replace("_", " ")}</Badge>;
}

const ORDER_STATUS_VARIANT: Record<PurchaseOrderStatus, "outline" | "secondary" | "success" | "destructive"> = {
  recommended: "outline",
  approved: "secondary",
  ordered: "secondary",
  received: "success",
  cancelled: "destructive",
};

export function PurchaseOrderStatusBadge({ status }: { status: PurchaseOrderStatus }) {
  return <Badge variant={ORDER_STATUS_VARIANT[status]}>{status}</Badge>;
}

export function RecommendedByBadge({ recommendedBy }: { recommendedBy: RecommendedBy }) {
  return recommendedBy === "ai" ? (
    <Badge className="bg-accent text-accent-foreground" variant="default">
      AI
    </Badge>
  ) : (
    <Badge variant="outline">Manual</Badge>
  );
}

export function ForecastModelBadge({ model }: { model: ForecastModelType }) {
  return <Badge variant="secondary">{model}</Badge>;
}
