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
import { useCreateHospital } from "@/features/hospitals/hooks";
import type { HospitalType } from "@/lib/types";

const schema = z.object({
  name: z.string().min(1).max(255),
  code: z.string().min(1).max(20),
  city: z.string().min(1).max(120),
  region: z.string().min(1).max(120),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  bed_capacity: z.coerce.number().int().positive(),
  type: z.enum(["general", "specialty", "teaching", "clinic"]),
});

type FormValues = z.infer<typeof schema>;

export function HospitalFormDialog() {
  const [open, setOpen] = useState(false);
  const createHospital = useCreateHospital();
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { type: "general" } });

  const onSubmit = (values: FormValues) => {
    createHospital.mutate(values as FormValues & { type: HospitalType }, {
      onSuccess: () => {
        setOpen(false);
        reset();
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" /> Add hospital
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add hospital</DialogTitle>
          <DialogDescription>Registers a new node in the network.</DialogDescription>
        </DialogHeader>
        <form className="grid grid-cols-2 gap-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="col-span-2 flex flex-col gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="code">Code</Label>
            <Input id="code" placeholder="e.g. RYD-01" {...register("code")} />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Type</Label>
            <Controller
              control={control}
              name="type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="specialty">Specialty</SelectItem>
                    <SelectItem value="teaching">Teaching</SelectItem>
                    <SelectItem value="clinic">Clinic</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="city">City</Label>
            <Input id="city" {...register("city")} />
            {errors.city && <p className="text-xs text-destructive">{errors.city.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="region">Region</Label>
            <Input id="region" {...register("region")} />
            {errors.region && <p className="text-xs text-destructive">{errors.region.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="latitude">Latitude</Label>
            <Input id="latitude" type="number" step="any" {...register("latitude")} />
            {errors.latitude && <p className="text-xs text-destructive">{errors.latitude.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="longitude">Longitude</Label>
            <Input id="longitude" type="number" step="any" {...register("longitude")} />
            {errors.longitude && <p className="text-xs text-destructive">{errors.longitude.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="bed_capacity">Bed capacity</Label>
            <Input id="bed_capacity" type="number" {...register("bed_capacity")} />
            {errors.bed_capacity && <p className="text-xs text-destructive">{errors.bed_capacity.message}</p>}
          </div>
          <DialogFooter className="col-span-2">
            <Button type="submit" disabled={createHospital.isPending}>
              {createHospital.isPending ? "Creating…" : "Create hospital"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
