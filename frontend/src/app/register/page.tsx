"use client";

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRegister } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api-client";

// Mirrors backend/app/api/v1/schemas/auth.py::UserRegisterRequest exactly.
const registerSchema = z.object({
  fullName: z.string().min(1, "Full name is required.").max(255),
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "At least 8 characters.").max(128),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const register = useRegister();

  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const onSubmit = (values: RegisterForm) => register.mutate(values);

  return (
    <AuthLayout
      title="Create an account"
      description="New accounts start as viewers — an admin promotes you to a working role."
    >
      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)}>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="fullName">Full name</Label>
          <Input id="fullName" autoComplete="name" {...field("fullName")} />
          {errors.fullName && <p className="text-xs text-destructive">{errors.fullName.message}</p>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" {...field("email")} />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" {...field("password")} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        {register.isError && (
          <p className="text-sm text-destructive">
            {register.error instanceof ApiError && typeof register.error.detail === "string"
              ? register.error.detail
              : "Could not create the account."}
          </p>
        )}
        <Button type="submit" disabled={register.isPending}>
          {register.isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
