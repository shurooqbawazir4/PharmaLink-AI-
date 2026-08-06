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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useReceiveStock } from "@/features/inventory/hooks";
import { useMedicines } from "@/features/medicines/hooks";
import { useSuppliers } from "@/features/procurement/hooks";

const schema = z.object({
  medicine_id: z.string().min(1, "Required"),
  batch_number: z.string().min(1).max(100),
  quantity: z.coerce.number().int().positive(),
  safety_stock: z.coerce.number().int().min(0).default(0),
  expiry_date: z.string().min(1, "Required"),
  unit_cost_at_receipt: z.coerce.number().positive(),
  supplier_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function ReceiveStockDialog({ hospitalId }: { hospitalId: string }) {
  const [open, setOpen] = useState(false);
  const { data: medicines = [] } = useMedicines();
  const { data: suppliers = [] } = useSuppliers();
  const receiveStock = useReceiveStock();

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = (values: FormValues) => {
    receiveStock.mutate(
      {
        hospital_id: hospitalId,
        medicine_id: values.medicine_id,
        batch_number: values.batch_number,
        quantity: values.quantity,
        safety_stock: values.safety_stock,
        expiry_date: values.expiry_date,
        unit_cost_at_receipt: values.unit_cost_at_receipt,
        supplier_id: values.supplier_id || null,
      },
      {
        onSuccess: () => {
          setOpen(false);
          reset();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" /> Receive stock
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Receive stock</DialogTitle>
          <DialogDescription>Records a new inventory batch for this hospital.</DialogDescription>
        </DialogHeader>
        <form className="grid grid-cols-2 gap-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="col-span-2 flex flex-col gap-1.5">
            <Label>Medicine</Label>
            <Controller
              control={control}
              name="medicine_id"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a medicine" />
                  </SelectTrigger>
                  <SelectContent>
                    {medicines.map((medicine) => (
                      <SelectItem key={medicine.id} value={medicine.id}>
                        {medicine.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.medicine_id && <p className="text-xs text-destructive">{errors.medicine_id.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="batch_number">Batch number</Label>
            <Input id="batch_number" {...register("batch_number")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quantity">Quantity</Label>
            <Input id="quantity" type="number" {...register("quantity")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="safety_stock">Safety stock</Label>
            <Input id="safety_stock" type="number" {...register("safety_stock")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="unit_cost_at_receipt">Unit cost</Label>
            <Input id="unit_cost_at_receipt" type="number" step="0.01" {...register("unit_cost_at_receipt")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="expiry_date">Expiry date</Label>
            <Input id="expiry_date" type="date" {...register("expiry_date")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Supplier (optional)</Label>
            <Controller
              control={control}
              name="supplier_id"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliers.map((supplier) => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <DialogFooter className="col-span-2">
            <Button type="submit" disabled={receiveStock.isPending}>
              {receiveStock.isPending ? "Saving…" : "Receive stock"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
