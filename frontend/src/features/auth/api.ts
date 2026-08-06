import { apiFetch } from "@/lib/api-client";
import type { TokenResponse, UserRead } from "@/lib/types";

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: { email, password },
  });
}

export function register(email: string, password: string, full_name: string): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/register", {
    method: "POST",
    auth: false,
    body: { email, password, full_name },
  });
}

export function getMe(): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/me");
}
