"use client";

import { useState } from "react";

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

/** Shared one-field-quantity dialog — used for inventory "consume" and
 * "adjust" actions, which differ only in label/sign, not shape. */
export function QuantityActionDialog({
  trigger,
  title,
  description,
  label,
  allowNegative = false,
  onSubmit,
  isPending,
}: {
  trigger: React.ReactNode;
  title: string;
  description: string;
  label: string;
  allowNegative?: boolean;
  onSubmit: (quantity: number) => void;
  isPending?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const quantity = Number(value);
    if (!Number.isFinite(quantity) || quantity === 0) return;
    onSubmit(quantity);
    setOpen(false);
    setValue("");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quantity">{label}</Label>
            <Input
              id="quantity"
              type="number"
              min={allowNegative ? undefined : 1}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Saving…" : "Confirm"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
