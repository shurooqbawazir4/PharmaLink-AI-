"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { getMe, login, register } from "@/features/auth/api";
import { useAuthStore } from "@/lib/auth-store";

/** The current user, refetched on mount — cheap, and keeps the auth store's
 * cached `user` (from login/register) honest against server-side changes
 * like an admin promoting a role mid-session. */
export function useCurrentUser() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const setUser = useAuthStore((state) => state.setUser);

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const user = await getMe();
      setUser(user);
      return user;
    },
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const setSession = useAuthStore((state) => state.setSession);
  const router = useRouter();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onSuccess: async (tokens) => {
      // setSession needs the user, but /auth/me needs the token in the
      // store first — two-step: stash tokens, fetch identity, then merge.
      setSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }, null as never);
      const user = await getMe();
      setSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }, user);
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: ({
      email,
      password,
      fullName,
    }: {
      email: string;
      password: string;
      fullName: string;
    }) => register(email, password, fullName),
    onSuccess: () => {
      router.push("/login?registered=1");
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((state) => state.logout);
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    logout();
    queryClient.clear();
    router.push("/login");
  };
}
