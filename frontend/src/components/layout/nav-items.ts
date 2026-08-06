import {
  LayoutDashboard,
  Building2,
  Pill,
  TrendingUp,
  Shuffle,
  Bell,
  ShoppingCart,
  BarChart3,
  Leaf,
  MessageSquare,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

/** The spec's 10 dashboard pages, in the order they're listed there. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/medicines", label: "Medicines", icon: Pill },
  { href: "/hospitals", label: "Hospitals", icon: Building2 },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/optimization", label: "Optimization", icon: Shuffle },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/procurement", label: "Procurement", icon: ShoppingCart },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/sustainability", label: "Sustainability", icon: Leaf },
  { href: "/assistant", label: "AI Assistant", icon: MessageSquare },
];
