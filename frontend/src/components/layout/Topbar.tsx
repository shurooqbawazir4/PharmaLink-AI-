"use client";

import { usePathname } from "next/navigation";
import { LogOut, User as UserIcon } from "lucide-react";

import { NAV_ITEMS } from "@/components/layout/nav-items";
import { MobileNav } from "@/components/layout/MobileNav";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentUser, useLogout } from "@/features/auth/hooks";
import { isAdmin } from "@/lib/rbac";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function Topbar() {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  const pageTitle = NAV_ITEMS.find((item) => pathname.startsWith(item.href))?.label ?? "MedCycle AI";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <MobileNav />
        <h1 className="text-lg font-semibold tracking-tight">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-3">
        {user && (
          <Badge variant="outline" className="hidden sm:inline-flex">
            {isAdmin(user.role_name) ? "Network-wide" : "Hospital-scoped"}
          </Badge>
        )}
        <ThemeToggle />
        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Avatar>
                <AvatarFallback>{initials(user.full_name) || <UserIcon className="h-4 w-4" />}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-foreground">{user.full_name}</span>
                  <span className="text-xs text-muted-foreground">{user.email}</span>
                  <span className="text-xs capitalize text-muted-foreground">
                    {user.role_name.replace("_", " ")}
                  </span>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>
                <LogOut className="h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}
