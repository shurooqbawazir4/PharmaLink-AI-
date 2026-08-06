"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { UserRead } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserRead | null;
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (tokens: { accessToken: string; refreshToken: string }, user: UserRead) => void;
  setTokens: (tokens: { accessToken: string; refreshToken: string }) => void;
  setUser: (user: UserRead) => void;
  logout: () => void;
}

// Tokens live in localStorage (via zustand's `persist`), not an httpOnly
// cookie — the backend issues them as a JSON body (`TokenResponse`), not
// `Set-Cookie`, so matching that contract without a backend change means
// client-side storage. This is XSS-exposed compared to httpOnly cookies;
// an accepted MVP tradeoff, flagged as a Milestone E hardening candidate
// in docs/architecture.md, not silently glossed over.
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      // localStorage rehydration happens after the first client render —
      // the (app) layout's auth guard waits for this flag before deciding
      // to redirect, so a logged-in user never flashes to /login on reload.
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setSession: (tokens, user) =>
        set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken, user }),
      setTokens: (tokens) => set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken }),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: "medcycle-auth",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);

/** Non-hook accessor for use outside React (api-client.ts's interceptor). */
export function getAuthState(): AuthState {
  return useAuthStore.getState();
}
