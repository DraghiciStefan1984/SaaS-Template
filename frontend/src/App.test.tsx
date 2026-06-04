import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";
import { normalizeApiBaseUrl } from "./lib/api";
import { isOrganizationAdmin } from "./lib/workspace";

describe("App", () => {
  it("renders the unauthenticated login screen", () => {
    sessionStorage.clear();
    render(<App />);

    expect(screen.getByRole("heading", { name: "Workspace Login" })).toBeInTheDocument();
  });

  it("does not retain access tokens in browser storage", async () => {
    sessionStorage.setItem("saas_core_access_token", "legacy-access-token");
    render(<App />);

    await waitFor(() => {
      expect(sessionStorage.getItem("saas_core_access_token")).toBeNull();
    });
  });

  it("normalizes API base URL values with or without the API prefix", () => {
    expect(normalizeApiBaseUrl("https://api.example.com")).toBe("https://api.example.com");
    expect(normalizeApiBaseUrl("https://api.example.com/api/v1")).toBe(
      "https://api.example.com",
    );
  });

  it("identifies organization admin roles for gated UI sections", () => {
    const baseOrganization = {
      id: 1,
      name: "Workspace",
      timezone: "UTC",
      default_language: "en",
      created_at: "2026-06-04T00:00:00Z",
      updated_at: "2026-06-04T00:00:00Z",
    };

    expect(isOrganizationAdmin({ ...baseOrganization, my_role: "owner" })).toBe(true);
    expect(isOrganizationAdmin({ ...baseOrganization, my_role: "admin" })).toBe(true);
    expect(isOrganizationAdmin({ ...baseOrganization, my_role: "member" })).toBe(false);
  });
});
