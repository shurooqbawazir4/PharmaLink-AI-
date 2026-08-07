import {
  LayoutDashboard,
  Building2,
  Pill,
  TrendingUp,
  Shuffle,
  Bell,
  BarChart3,
  Leaf,
  MessageSquare,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** One-line purpose, shown as a hover tooltip in the nav — so what a
   * page is for is clear before you click into it, not just after. */
  description: string;
}

/** The dashboard's pages, in nav order. Procurement/Suppliers was removed
 * from the UI for this demo (the backend module + API are untouched —
 * ReceiveStockDialog still uses features/procurement's supplier list). */
export const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    description: "Network-wide overview: top KPIs, expiry risks, and open alerts at a glance.",
  },
  {
    href: "/medicines",
    label: "Medicines",
    icon: Pill,
    description: "The shared medicine catalogue — names, categories, unit cost, controlled/refrigeration flags.",
  },
  {
    href: "/hospitals",
    label: "Hospitals",
    icon: Building2,
    description: "The hospital network map, plus a per-hospital inventory and expiry-risk drill-down.",
  },
  {
    href: "/forecast",
    label: "Demand Forecast",
    icon: TrendingUp,
    description: "Predicts how much of each medicine a hospital will need next, and why.",
  },
  {
    href: "/optimization",
    label: "Transfer Optimization",
    icon: Shuffle,
    description: "Finds which hospital should send medicine to which — instead of it expiring unused.",
  },
  {
    href: "/alerts",
    label: "Alerts",
    icon: Bell,
    description: "Shortage, expiry, low-stock, and AI transfer-suggested notifications, in one queue.",
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    description: "Operational KPIs: waste, transfer success, inventory turnover, procurement spend.",
  },
  {
    href: "/sustainability",
    label: "Sustainability",
    icon: Leaf,
    description: "The redistribution story: real waste value prevented, units saved, CO₂ estimate.",
  },
  {
    href: "/assistant",
    label: "AI Assistant",
    icon: MessageSquare,
    description: "Ask why a recommendation was made, or chat freeform — grounded in real numbers, never predicts.",
  },
];
