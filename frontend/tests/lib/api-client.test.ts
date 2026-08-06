import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, toQueryString } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  useAuthStore.setState({
    accessToken: "initial-access-token",
    refreshToken: "initial-refresh-token",
    user: null,
  });
  vi.restoreAllMocks();
});

describe("toQueryString", () => {
  it("drops undefined, null, and empty-string values", () => {
    expect(toQueryString({ a: "1", b: undefined, c: null, d: "" })).toBe("?a=1");
  });

  it("returns an empty string when nothing survives", () => {
    expect(toQueryString({ a: undefined, b: null })).toBe("");
  });

  it("stringifies numbers and booleans", () => {
    expect(toQueryString({ n: 3, flag: false })).toBe("?n=3&flag=false");
  });
});

describe("apiFetch", () => {
  it("attaches the bearer token and returns parsed JSON on success", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await apiFetch<{ ok: boolean }>("/hospitals/");

    expect(result).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls.at(0)!;
    expect((init?.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer initial-access-token"
    );
  });

  it("refreshes once on a 401, then retries the original request", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401)) // original request
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "new-access", refresh_token: "new-refresh", token_type: "bearer" })
      ) // /auth/refresh
      .mockResolvedValueOnce(jsonResponse({ ok: true })); // retried original request

    const result = await apiFetch<{ ok: boolean }>("/hospitals/");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls.at(1)![0])).toContain("/auth/refresh");
    // The retry carries the newly refreshed token, not the stale one.
    const retryInit = fetchMock.mock.calls.at(2)![1];
    expect((retryInit?.headers as Record<string, string>)["Authorization"]).toBe("Bearer new-access");
    expect(useAuthStore.getState().accessToken).toBe("new-access");
  });

  it("logs out and throws when the refresh token itself is rejected", async () => {
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401)) // original request
      .mockResolvedValueOnce(jsonResponse({ detail: "invalid refresh token" }, 401)); // /auth/refresh fails

    await expect(apiFetch("/hospitals/")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("does not attempt a refresh loop on a second consecutive 401", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "new-access", refresh_token: "new-refresh", token_type: "bearer" })
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "still unauthorized" }, 401));

    await expect(apiFetch("/hospitals/")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("raises ApiError with the parsed detail on a non-401 failure", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(jsonResponse({ detail: "not found" }, 404));

    await expect(apiFetch("/hospitals/missing")).rejects.toMatchObject({
      status: 404,
      detail: "not found",
    });
  });
});
