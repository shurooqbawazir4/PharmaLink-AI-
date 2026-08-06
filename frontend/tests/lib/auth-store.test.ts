import { beforeEach, describe, expect, it } from "vitest";

import { getAuthState, useAuthStore } from "@/lib/auth-store";
import type { UserRead } from "@/lib/types";

const USER: UserRead = {
  id: "user-1",
  email: "admin@medcycle.test",
  full_name: "Admin User",
  role_name: "admin",
  is_active: true,
  hospital_id: null,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  useAuthStore.setState({ accessToken: null, refreshToken: null, user: null });
});

describe("useAuthStore", () => {
  it("starts logged out", () => {
    expect(getAuthState().accessToken).toBeNull();
    expect(getAuthState().user).toBeNull();
  });

  it("setSession stores tokens and the user together", () => {
    useAuthStore.getState().setSession({ accessToken: "at", refreshToken: "rt" }, USER);

    const state = getAuthState();
    expect(state.accessToken).toBe("at");
    expect(state.refreshToken).toBe("rt");
    expect(state.user).toEqual(USER);
  });

  it("setTokens updates tokens without touching the cached user", () => {
    useAuthStore.getState().setSession({ accessToken: "at", refreshToken: "rt" }, USER);
    useAuthStore.getState().setTokens({ accessToken: "at2", refreshToken: "rt2" });

    const state = getAuthState();
    expect(state.accessToken).toBe("at2");
    expect(state.user).toEqual(USER);
  });

  it("logout clears tokens and the user", () => {
    useAuthStore.getState().setSession({ accessToken: "at", refreshToken: "rt" }, USER);
    useAuthStore.getState().logout();

    const state = getAuthState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
