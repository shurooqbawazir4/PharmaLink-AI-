"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Database,
  Leaf,
  MessageSquare,
  Shuffle,
  TrendingUp,
} from "lucide-react";

import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuthStore } from "@/lib/auth-store";

// The pipeline, in the order data actually flows through the backend
// modules (see docs/architecture.md) — this is the literal request-flow,
// not marketing copy dressed up to look like one.
const PIPELINE_STEPS = [
  {
    icon: Database,
    title: "1. Ingest real data",
    description:
      "Consumption, inventory, hospital occupancy, and real CDC FluView seasonality feed every hospital × medicine pair.",
  },
  {
    icon: TrendingUp,
    title: "2. Forecast demand",
    description:
      "A LightGBM model trained on that history predicts 7/30/90-day demand per hospital and medicine, with a confidence band.",
  },
  {
    icon: AlertTriangle,
    title: "3. Flag risk",
    description:
      "Expiry-risk and shortage-risk scoring turn that forecast into a probability, a dollar estimate, and an alert.",
  },
  {
    icon: Shuffle,
    title: "4. Optimize transfers",
    description:
      "Instead of one hospital's medicine expiring unused while another runs short, an OR-Tools solver finds the exact transfer that fixes both — at the lowest transport cost.",
  },
  {
    icon: MessageSquare,
    title: "5. Explain every recommendation",
    description:
      "A Groq-backed assistant narrates each decision in plain language — it never predicts a number, only explains one.",
  },
];

const FEATURE_PAGES = [
  { title: "Dashboard", body: "Network-wide overview: KPIs, top expiry risks, open alerts." },
  { title: "Demand Forecast", body: "Trained demand predictions per hospital and medicine." },
  { title: "Transfer Optimization", body: "Real transfer recommendations, mapped and costed." },
  { title: "AI Assistant", body: "Ask why a recommendation was made — grounded, never guessed." },
];

export default function LandingPage() {
  const router = useRouter();
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const accessToken = useAuthStore((state) => state.accessToken);

  // Logged-in visitors skip straight to the dashboard — this page is the
  // pitch/explainer for people who aren't signed in yet, not a second home
  // screen for people who already are.
  useEffect(() => {
    if (hasHydrated && accessToken) {
      router.replace("/dashboard");
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || accessToken) {
    return (
      <div className="flex h-dvh items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Logo />
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild>
              <Link href="/login">Log in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-20 text-center">
        <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Stop hospitals from running short on one shelf while another writes off a batch
          to waste.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
          PharmaLink AI forecasts medication demand per hospital, scores expiry and shortage
          risk, and recommends the specific transfers and purchase orders that prevent
          waste and stockouts — every recommendation explained in plain language, never a
          black box.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Button size="lg" asChild>
            <Link href="/register">
              Get started <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/login">Log in</Link>
          </Button>
        </div>
      </section>

      <section className="border-t border-border bg-muted/30 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <h2 className="text-2xl font-semibold tracking-tight">How PharmaLink AI works</h2>
            <p className="mt-2 text-muted-foreground">
              The same six steps, every time — from raw consumption data to a plain-language
              explanation.
            </p>
          </div>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE_STEPS.map((step) => (
              <Card key={step.title}>
                <CardContent className="flex flex-col gap-3 p-5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <step.icon className="h-4.5 w-4.5" />
                  </div>
                  <h3 className="font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <h2 className="text-2xl font-semibold tracking-tight">One platform, ten views</h2>
            <p className="mt-2 text-muted-foreground">
              Everything above is a live page once you&apos;re logged in — a preview of four:
            </p>
          </div>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURE_PAGES.map((page) => (
              <div key={page.title} className="rounded-lg border border-border p-5">
                <h3 className="font-semibold">{page.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{page.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-6 text-center">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Leaf className="h-4 w-4" />
            <span className="text-sm">
              Every number on this dashboard is real or clearly labeled as an estimate —
              nothing here is fabricated to look impressive.
            </span>
          </div>
          <Button asChild>
            <Link href="/register">
              Get started <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </footer>
    </div>
  );
}
