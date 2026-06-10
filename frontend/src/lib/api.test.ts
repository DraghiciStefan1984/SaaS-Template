import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  api,
  configureAuthTokenHandlers,
  getApiErrorMessage,
  listResults,
} from "./api";

function jsonResponse(payload: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(payload === null ? "" : JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

describe("API client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    configureAuthTokenHandlers({});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    configureAuthTokenHandlers({});
  });

  it("sends authenticated JSON requests with the expected API path", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 7, name: "Updated" }));

    await api.updateOrganization("access-token", 7, {
      name: "Updated",
      timezone: "UTC",
    });

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/organizations/7/");
    expect(options?.method).toBe("PATCH");
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer access-token");
    expect(JSON.parse(String(options?.body))).toEqual({
      name: "Updated",
      timezone: "UTC",
    });
  });

  it("returns undefined for successful no-content responses", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(api.logout("access-token")).resolves.toBeUndefined();
  });

  it("refreshes once after an authenticated 401 and retries with the new token", async () => {
    const setAccessToken = vi.fn();
    const clearAuth = vi.fn();
    configureAuthTokenHandlers({ setAccessToken, clearAuth });
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ detail: "Expired access token" }, 401))
      .mockResolvedValueOnce(jsonResponse({ access: "new-access-token" }))
      .mockResolvedValueOnce(
        jsonResponse({
          id: 1,
          email: "user@example.com",
          name: "User",
          is_email_verified: true,
          account_status: "active",
          date_joined: "2026-06-10T00:00:00Z",
        }),
      );

    const user = await api.me("expired-access-token");

    expect(user.email).toBe("user@example.com");
    expect(setAccessToken).toHaveBeenCalledWith("new-access-token");
    expect(clearAuth).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(3);
    const retryHeaders = new Headers(vi.mocked(fetch).mock.calls[2][1]?.headers);
    expect(retryHeaders.get("Authorization")).toBe("Bearer new-access-token");
  });

  it("clears auth and preserves the original API error when refresh fails", async () => {
    const clearAuth = vi.fn();
    configureAuthTokenHandlers({ clearAuth });
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ detail: "Expired access token" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "Refresh token invalid" }, 401));

    await expect(api.me("expired-access-token")).rejects.toMatchObject({
      status: 401,
      payload: { detail: "Expired access token" },
    });
    expect(clearAuth).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("downloads report artifacts and extracts a safe response filename", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("report content", {
        status: 200,
        headers: {
          "content-disposition": 'attachment; filename="weekly-report.csv"',
          "content-type": "text/csv",
        },
      }),
    );

    const result = await api.downloadReportArtifact("access-token", 3, 9);

    expect(result.filename).toBe("weekly-report.csv");
    expect(await result.blob.text()).toBe("report content");
  });

  it("flattens backend validation errors and normalizes paginated results", () => {
    const error = new ApiError(
      "Validation failed",
      400,
      {
        email: ["Enter a valid email address."],
        non_field_errors: ["Request cannot be completed."],
      },
    );

    expect(getApiErrorMessage(error)).toBe(
      "email: Enter a valid email address. Request cannot be completed.",
    );
    expect(
      listResults({
        count: 1,
        next: null,
        previous: null,
        results: [{ id: 1 }],
      }),
    ).toEqual([{ id: 1 }]);
    expect(listResults(undefined)).toEqual([]);
  });
});
