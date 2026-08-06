import { getAuthState } from "@/lib/auth-store";
import type { TokenResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Attach the bearer token. Defaults to true — pass false for /auth/login,
   * /auth/register, /auth/refresh, which are unauthenticated by design. */
  auth?: boolean;
  /** Internal — set on the retry attempt to stop an infinite refresh loop. */
  _isRetry?: boolean;
}

let refreshInFlight: Promise<boolean> | null = null;

/** Single-flight refresh: concurrent 401s all await the same in-flight
 * refresh call rather than each firing their own. Returns false (and logs
 * the session out) if the refresh token itself is invalid/expired. */
async function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const { refreshToken, setTokens, logout } = getAuthState();
    if (!refreshToken) {
      logout();
      return false;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        logout();
        return false;
      }
      const tokens = (await response.json()) as TokenResponse;
      setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      return true;
    } catch {
      logout();
      return false;
    }
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

/** Typed fetch wrapper: JSON body, auth header injection, and a single
 * refresh-and-retry on a 401 before giving up and logging out. Every
 * feature module's api.ts calls this rather than raw `fetch`. */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { auth = true, body, headers, _isRetry, ...rest } = options;

  const requestHeaders: Record<string, string> = { ...(headers as Record<string, string>) };
  if (body !== undefined) requestHeaders["Content-Type"] = "application/json";
  if (auth) {
    const { accessToken } = getAuthState();
    if (accessToken) requestHeaders["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && !_isRetry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiFetch<T>(path, { ...options, _isRetry: true });
    }
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      const parsed = (await response.json()) as { detail?: unknown };
      detail = parsed.detail ?? parsed;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Builds a query string, dropping undefined/null values — every
 * feature module's list-with-filters functions use this. */
export function toQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
