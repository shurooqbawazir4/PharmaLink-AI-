"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";

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
import { useCreateSupplier } from "@/features/procurement/hooks";

const schema = z.object({
  name: z.string().min(1).max(255),
  lead_time_days: z.coerce.number().int().positive(),
  reliability_score: z.coerce.number().min(0).max(1).default(1),
  contact_email: z.string().email().max(255).optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

export function SupplierFormDialog() {
  const [open, setOpen] = useState(false);
  const createSupplier = useCreateSupplier();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { reliability_score: 1 } });

  const onSubmit = (values: FormValues) => {
    createSupplier.mutate(
      { ...values, contact_email: values.contact_email || undefined },
      { onSuccess: () => { setOpen(false); reset(); } }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" /> Add supplier
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add supplier</DialogTitle>
          <DialogDescription>Adds a supplier to the network-wide catalogue.</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lead_time_days">Lead time (days)</Label>
              <Input id="lead_time_days" type="number" {...register("lead_time_days")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="reliability_score">Reliability (0–1)</Label>
              <Input id="reliability_score" type="number" step="0.01" min={0} max={1} {...register("reliability_score")} />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="contact_email">Contact email (optional)</Label>
            <Input id="contact_email" type="email" {...register("contact_email")} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createSupplier.isPending}>
              {createSupplier.isPending ? "Creating…" : "Create supplier"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
