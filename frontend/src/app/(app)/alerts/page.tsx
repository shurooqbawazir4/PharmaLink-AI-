"use client";

import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { AlertSeverityBadge } from "@/components/charts/StatusBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAlerts, useResolveAlert } from "@/features/notifications/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { useLookupMaps } from "@/hooks/useLookupMaps";
import type { AlertSeverity, AlertType } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const SEVERITIES: AlertSeverity[] = ["critical", "warning", "info"];
const TYPES: AlertType[] = ["shortage_risk", "expiry_risk", "low_stock", "transfer_suggested"];

export default function AlertsPage() {
  const scope = useHospitalScope();
  const { hospitalName, medicineName } = useLookupMaps();
  const [severity, setSeverity] = useState<AlertSeverity | "all">("all");
  const [type, setType] = useState<AlertType | "all">("all");
  const [resolvedFilter, setResolvedFilter] = useState<"unresolved" | "resolved" | "all">("unresolved");

  const { data: alerts = [], isLoading } = useAlerts({
    hospitalId: scope.hospitalId ?? undefined,
    severity: severity === "all" ? undefined : severity,
    type: type === "all" ? undefined : type,
    isResolved: resolvedFilter === "all" ? undefined : resolvedFilter === "resolved",
  });
  const resolveAlert = useResolveAlert();

  return (
    <div>
      <PageHeader title="Alerts" description="Shortage, expiry, low-stock, and transfer-suggested notifications." actions={<HospitalScopeSelect scope={scope} />} />

      <div className="mb-4 flex flex-wrap gap-3">
        <Select value={resolvedFilter} onValueChange={(v) => setResolvedFilter(v as typeof resolvedFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="unresolved">Unresolved</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="all">All</SelectItem>
          </SelectContent>
        </Select>
        <Select value={severity} onValueChange={(v) => setSeverity(v as typeof severity)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            {SEVERITIES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={type} onValueChange={(v) => setType(v as typeof type)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t.replace(/_/g, " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Severity</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Hospital</TableHead>
                <TableHead>Medicine</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Raised</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  </TableRow>
                ))
              ) : alerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    No alerts match these filters.
                  </TableCell>
                </TableRow>
              ) : (
                alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>
                      <AlertSeverityBadge severity={alert.severity} />
                    </TableCell>
                    <TableCell className="text-xs capitalize text-muted-foreground">
                      {alert.type.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell className="text-sm">{hospitalName(alert.hospital_id)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {alert.medicine_id ? medicineName(alert.medicine_id) : "—"}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-sm">{alert.message}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTime(alert.created_at)}
                    </TableCell>
                    <TableCell>
                      {!alert.is_resolved && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={resolveAlert.isPending}
                          onClick={() => resolveAlert.mutate(alert.id)}
                        >
                          Resolve
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
