"use client";

import { useState } from "react";
import { PackageCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReceivePurchaseOrder } from "@/features/procurement/hooks";

/** Receiving a purchase order creates the actual inventory batch — needs a
 * batch number + expiry date, the two fields `InventoryReceiveRequest`
 * can't infer from the order itself. See `ProcurementService.mark_received`. */
export function ReceiveOrderDialog({ orderId }: { orderId: string }) {
  const [open, setOpen] = useState(false);
  const [batchNumber, setBatchNumber] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const receiveOrder = useReceivePurchaseOrder();

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!batchNumber || !expiryDate) return;
    receiveOrder.mutate(
      { id: orderId, payload: { batch_number: batchNumber, expiry_date: expiryDate } },
      {
        onSuccess: () => {
          setOpen(false);
          setBatchNumber("");
          setExpiryDate("");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <PackageCheck className="h-3.5 w-3.5" /> Receive
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Receive order into inventory</DialogTitle>
          <DialogDescription>Creates a new inventory batch from this order.</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="batch_number">Batch number</Label>
            <Input
              id="batch_number"
              value={batchNumber}
              onChange={(event) => setBatchNumber(event.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="expiry_date">Expiry date</Label>
            <Input
              id="expiry_date"
              type="date"
              value={expiryDate}
              onChange={(event) => setExpiryDate(event.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={receiveOrder.isPending}>
              {receiveOrder.isPending ? "Receiving…" : "Receive into inventory"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
