import { redirect } from "next/navigation";

// Auth is decided client-side (zustand + localStorage — see lib/auth-store.ts),
// so this can't know here whether the visitor is logged in. Always point at
// /dashboard; the (app) route group's layout guard bounces to /login itself
// if there's no session.
export default function RootPage() {
  redirect("/dashboard");
}
