# PharmaLink AI — Frontend

Next.js 15 (App Router) + React 19 + TypeScript + TailwindCSS + shadcn/ui +
Framer Motion + TanStack Query + React Hook Form/Zod + Recharts + MapLibre GL.
Runs as its own dev-mode Docker service — see
[../docs/architecture.md](../docs/architecture.md#frontend-milestone-d) for
the full design writeup (module boundaries, API client, auth/RBAC, testing
scope).

All 10 spec pages: Dashboard, Medicines, Hospitals (+ per-hospital
inventory/expiry drill-down), Forecast, Optimization, Alerts, Procurement
(purchase orders + suppliers), Analytics, Sustainability, AI Assistant — plus
Login/Register. Dark mode, responsive, Framer Motion micro-interactions.

Talks to the FastAPI backend at `NEXT_PUBLIC_API_URL` (see
`docker/.env.example`) — no other configuration needed to run against the
seeded demo dataset.

## Structure

```
src/
  app/                # routes — app/(app)/* is the authenticated dashboard shell
  components/ui/      # shadcn-generated primitives
  components/layout/  # AppShell, Sidebar, Topbar, ThemeToggle
  components/charts/  # KpiCard, LineChartCard, BarChartCard, StatusBadges
  components/map/     # HospitalMap (MapLibre)
  features/<module>/  # one per backend module: api.ts, hooks.ts, components
  lib/                 # api-client.ts, types/*.ts, auth-store.ts, rbac.ts
```

## Commands (run inside the container — no local Node needed)

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm run lint
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm run typecheck
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm test
```
