import Link from "next/link";

import { Logo } from "@/components/layout/Logo";

export function AuthLayout({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <Link href="/" className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo className="flex flex-col items-center gap-2" wordmarkClassName="text-xl font-semibold tracking-tight" />
          <p className="text-sm text-muted-foreground">Medication Intelligence Platform</p>
        </Link>
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
