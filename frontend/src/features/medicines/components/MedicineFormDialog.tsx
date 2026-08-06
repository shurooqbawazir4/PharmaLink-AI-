"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
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
import { Switch } from "@/components/ui/switch";
import { useCreateMedicine } from "@/features/medicines/hooks";

const schema = z.object({
  name: z.string().min(1).max(255),
  generic_name: z.string().min(1).max(255),
  category: z.string().min(1).max(120),
  unit: z.string().min(1).max(30),
  unit_cost: z.coerce.number().positive(),
  atc_code: z.string().max(20).optional(),
  requires_refrigeration: z.boolean().default(false),
  is_controlled: z.boolean().default(false),
});

type FormValues = z.infer<typeof schema>;

export function MedicineFormDialog() {
  const [open, setOpen] = useState(false);
  const createMedicine = useCreateMedicine();
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { requires_refrigeration: false, is_controlled: false },
  });

  const onSubmit = (values: FormValues) => {
    createMedicine.mutate(
      { ...values, atc_code: values.atc_code || undefined },
      { onSuccess: () => { setOpen(false); reset(); } }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" /> Add medicine
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add medicine</DialogTitle>
          <DialogDescription>Adds an entry to the network-wide catalogue.</DialogDescription>
        </DialogHeader>
        <form className="grid grid-cols-2 gap-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="col-span-2 flex flex-col gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="generic_name">Generic name</Label>
            <Input id="generic_name" {...register("generic_name")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="category">Category</Label>
            <Input id="category" {...register("category")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="unit">Unit</Label>
            <Input id="unit" placeholder="e.g. tablet" {...register("unit")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="unit_cost">Unit cost</Label>
            <Input id="unit_cost" type="number" step="0.01" {...register("unit_cost")} />
          </div>
          <div className="col-span-2 flex flex-col gap-1.5">
            <Label htmlFor="atc_code">ATC code (optional)</Label>
            <Input id="atc_code" {...register("atc_code")} />
          </div>
          <div className="flex items-center gap-2">
            <Controller
              control={control}
              name="requires_refrigeration"
              render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} />}
            />
            <Label>Requires refrigeration</Label>
          </div>
          <div className="flex items-center gap-2">
            <Controller
              control={control}
              name="is_controlled"
              render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} />}
            />
            <Label>Controlled substance</Label>
          </div>
          <DialogFooter className="col-span-2">
            <Button type="submit" disabled={createMedicine.isPending}>
              {createMedicine.isPending ? "Creating…" : "Create medicine"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
