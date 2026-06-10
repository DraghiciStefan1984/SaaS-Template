import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, configureAuthTokenHandlers } from "./api";
import { AuthProvider, useAuth } from "./auth";
import type { User } from "./types";

vi.mock("./api", () => ({
  api: {
    login: vi.fn(),
    googleLogin: vi.fn(),
    register: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    updateMe: vi.fn(),
    logout: vi.fn(),
  },
  configureAuthTokenHandlers: vi.fn(),
}));

const baseUser: User = {
  id: 1,
  email: "user@example.com",
  name: "User",
  is_email_verified: true,
  account_status: "active",
  date_joined: "2026-06-10T00:00:00Z",
};

function AuthProbe() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="status">
        {auth.isBootstrapping ? "bootstrapping" : auth.isAuthenticated ? "authenticated" : "guest"}
      </span>
      <span data-testid="user-name">{auth.user?.name ?? "none"}</span>
      <button onClick={() => auth.login("user@example.com", "password")} type="button">
        Login
      </button>
      <button
        onClick={() =>
          auth.register({
            email: "new@example.com",
            password: "password",
            name: "New User",
            organization_name: "New Workspace",
          })
        }
        type="button"
      >
        Register
      </button>
      <button onClick={() => auth.updateProfile({ name: "Updated User" })} type="button">
        Update
      </button>
      <button onClick={() => auth.logout()} type="button">
        Logout
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("starts as guest and removes legacy access-token storage", async () => {
    sessionStorage.setItem("saas_core_access_token", "legacy-token");

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("guest"));
    expect(sessionStorage.getItem("saas_core_access_token")).toBeNull();
    expect(api.refresh).not.toHaveBeenCalled();
  });

  it("restores a session from the refresh cookie and refreshes stored user data", async () => {
    sessionStorage.setItem("saas_core_user", JSON.stringify({ ...baseUser, name: "Stale User" }));
    vi.mocked(api.refresh).mockResolvedValue({ access: "restored-access" });
    vi.mocked(api.me).mockResolvedValue(baseUser);

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(api.refresh).toHaveBeenCalledOnce();
    expect(api.me).toHaveBeenCalledWith("restored-access");
    expect(screen.getByTestId("user-name")).toHaveTextContent("User");
    expect(JSON.parse(sessionStorage.getItem("saas_core_user") ?? "{}").name).toBe("User");
  });

  it("clears a stale stored session when refresh fails", async () => {
    sessionStorage.setItem("saas_core_user", JSON.stringify(baseUser));
    vi.mocked(api.refresh).mockRejectedValue(new Error("Refresh failed"));

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("guest"));
    expect(sessionStorage.getItem("saas_core_user")).toBeNull();
  });

  it("supports login, profile update, and local-first logout", async () => {
    vi.mocked(api.login).mockResolvedValue({ access: "login-access", user: baseUser });
    vi.mocked(api.updateMe).mockResolvedValue({ ...baseUser, name: "Updated User" });
    vi.mocked(api.logout).mockRejectedValue(new Error("Server already logged out"));

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("guest"));
    fireEvent.click(screen.getByRole("button", { name: "Login" }));
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(api.login).toHaveBeenCalledWith("user@example.com", "password");

    fireEvent.click(screen.getByRole("button", { name: "Update" }));
    await waitFor(() => expect(screen.getByTestId("user-name")).toHaveTextContent("Updated User"));
    expect(api.updateMe).toHaveBeenCalledWith("login-access", { name: "Updated User" });

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("guest"));
    expect(sessionStorage.getItem("saas_core_user")).toBeNull();
    expect(api.logout).toHaveBeenCalledWith("login-access");
  });

  it("supports registration responses that carry access under tokens", async () => {
    const registeredUser = { ...baseUser, id: 2, email: "new@example.com", name: "New User" };
    vi.mocked(api.register).mockResolvedValue({
      tokens: { access: "registration-access" },
      user: registeredUser,
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("guest"));
    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user-name")).toHaveTextContent("New User");
    expect(api.register).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password",
      name: "New User",
      organization_name: "New Workspace",
    });
  });

  it("registers and unregisters API token handlers with provider lifecycle", () => {
    const { unmount } = render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(configureAuthTokenHandlers).toHaveBeenCalledWith(
      expect.objectContaining({
        setAccessToken: expect.any(Function),
        clearAuth: expect.any(Function),
      }),
    );
    unmount();
    expect(configureAuthTokenHandlers).toHaveBeenLastCalledWith({});
  });
});
