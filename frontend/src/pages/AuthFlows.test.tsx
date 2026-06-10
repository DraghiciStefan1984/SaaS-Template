import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { AuthPage } from "./AuthPage";
import { InvitationAcceptPage } from "./InvitationAcceptPage";
import { PasswordResetPage } from "./PasswordResetPage";

vi.mock("../lib/auth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../components/GoogleLoginButton", () => ({
  GoogleLoginButton: () => <button disabled>Google login not configured</button>,
}));

vi.mock("../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../lib/api")>();
  return {
    ...original,
    api: {
      ...original.api,
      recoverPassword: vi.fn(),
      resetPassword: vi.fn(),
      acceptOrganizationInvitation: vi.fn(),
    },
  };
});

function renderRoute(element: React.ReactNode, route: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route element={element} path="*" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const guestAuth = {
  accessToken: "",
  user: null,
  isAuthenticated: false,
  isBootstrapping: false,
  login: vi.fn(),
  loginWithGoogle: vi.fn(),
  register: vi.fn(),
  updateProfile: vi.fn(),
  logout: vi.fn(),
};

describe("Authentication workflows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue(guestAuth);
  });

  it("submits password recovery and displays the generic success response", async () => {
    vi.mocked(api.recoverPassword).mockResolvedValue({
      detail: "If the account exists, a recovery email was sent.",
    });
    const user = userEvent.setup();
    renderRoute(<AuthPage initialMode="recover" />, "/recover-password");

    await user.type(screen.getByLabelText("Email"), "recover@example.com");
    await user.click(screen.getByRole("button", { name: "Send recovery email" }));

    await screen.findByText("If the account exists, a recovery email was sent.");
    expect(api.recoverPassword).toHaveBeenCalledWith("recover@example.com");
  });

  it("renders backend password recovery validation errors", async () => {
    vi.mocked(api.recoverPassword).mockRejectedValue(
      new ApiError("Invalid email", 400, { email: ["Enter a valid email address."] }),
    );
    const user = userEvent.setup();
    renderRoute(<AuthPage initialMode="recover" />, "/recover-password");

    await user.type(screen.getByLabelText("Email"), "recover@example.com");
    await user.click(screen.getByRole("button", { name: "Send recovery email" }));

    await screen.findByText("email: Enter a valid email address.");
  });

  it("rejects incomplete and mismatched password reset forms before API calls", async () => {
    const user = userEvent.setup();
    const { unmount } = renderRoute(<PasswordResetPage />, "/reset-password");
    await user.type(screen.getByLabelText("New password"), "NewPassword!123");
    await user.type(screen.getByLabelText("Confirm password"), "NewPassword!123");
    await user.click(screen.getByRole("button", { name: "Reset password" }));
    expect(screen.getByText("This password reset link is incomplete.")).toBeInTheDocument();
    expect(api.resetPassword).not.toHaveBeenCalled();
    unmount();

    renderRoute(<PasswordResetPage />, "/reset-password?uid=user-1&token=token-1");
    await user.type(screen.getByLabelText("New password"), "NewPassword!123");
    await user.type(screen.getByLabelText("Confirm password"), "DifferentPassword!123");
    await user.click(screen.getByRole("button", { name: "Reset password" }));
    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
    expect(api.resetPassword).not.toHaveBeenCalled();
  });

  it("submits a valid password reset and displays success", async () => {
    vi.mocked(api.resetPassword).mockResolvedValue({ detail: "Password reset completed." });
    const user = userEvent.setup();
    renderRoute(<PasswordResetPage />, "/reset-password?uid=user-1&token=token-1");

    await user.type(screen.getByLabelText("New password"), "NewPassword!123");
    await user.type(screen.getByLabelText("Confirm password"), "NewPassword!123");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await screen.findByText("Password reset completed.");
    expect(api.resetPassword).toHaveBeenCalledWith({
      uid: "user-1",
      token: "token-1",
      new_password: "NewPassword!123",
    });
    expect(screen.getByRole("link", { name: "Continue to login" })).toBeInTheDocument();
  });

  it("accepts an authenticated organization invitation and handles rejection", async () => {
    vi.mocked(useAuth).mockReturnValue({
      ...guestAuth,
      accessToken: "access-token",
      isAuthenticated: true,
    });
    vi.mocked(api.acceptOrganizationInvitation).mockResolvedValue({
      id: 9,
      organization: 3,
      user: null,
      role: "member",
      status: "active",
      invited_email: "",
      joined_at: "2026-06-10T00:00:00Z",
      created_at: "2026-06-10T00:00:00Z",
    });
    const user = userEvent.setup();
    const { unmount } = renderRoute(
      <InvitationAcceptPage />,
      "/accept-invitation?token=signed-token",
    );

    await user.click(screen.getByRole("button", { name: "Accept Invitation" }));
    await screen.findByText("Invitation accepted");
    expect(api.acceptOrganizationInvitation).toHaveBeenCalledWith("access-token", "signed-token");
    unmount();

    vi.mocked(api.acceptOrganizationInvitation).mockRejectedValue(
      new ApiError("Invitation invalid", 400, { token: ["This invitation is no longer available."] }),
    );
    renderRoute(<InvitationAcceptPage />, "/accept-invitation?token=reused-token");
    await user.click(screen.getByRole("button", { name: "Accept Invitation" }));
    await waitFor(() =>
      expect(screen.getByText("token: This invitation is no longer available.")).toBeInTheDocument(),
    );
  });
});
