import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Organization } from "../lib/types";
import { useWorkspace } from "../lib/workspace";
import { AIPage } from "./AIPage";
import { AccountPage } from "./AccountPage";
import { BillingPage } from "./BillingPage";
import { DangerZonePage } from "./DangerZonePage";
import { IntegrationsPage } from "./IntegrationsPage";
import { NotificationsPage } from "./NotificationsPage";
import { ReportsPage } from "./ReportsPage";
import { SecurityPage } from "./SecurityPage";
import { SettingsPage } from "./SettingsPage";

vi.mock("../lib/auth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../lib/workspace", async (importOriginal) => {
  const original = await importOriginal<typeof import("../lib/workspace")>();
  return {
    ...original,
    useWorkspace: vi.fn(),
  };
});

vi.mock("../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../lib/api")>();
  return {
    ...original,
    api: Object.fromEntries(
      Object.keys(original.api).map((key) => [key, vi.fn()]),
    ) as unknown as typeof original.api,
  };
});

const baseOrganization: Organization = {
  id: 1,
  name: "Workspace",
  timezone: "UTC",
  default_language: "en",
  my_role: "owner",
  created_at: "2026-06-10T00:00:00Z",
  updated_at: "2026-06-10T00:00:00Z",
};

const user = {
  id: 1,
  email: "owner@example.com",
  name: "Owner",
  is_email_verified: true,
  account_status: "active",
  date_joined: "2026-06-10T00:00:00Z",
};

function renderPage(page: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function setRole(role: Organization["my_role"]) {
  vi.mocked(useWorkspace).mockReturnValue({
    organizations: [{ ...baseOrganization, my_role: role }],
    selectedOrganization: { ...baseOrganization, my_role: role },
  });
}

describe("Dashboard workflows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      accessToken: "access-token",
      user,
      isAuthenticated: true,
      isBootstrapping: false,
      login: vi.fn(),
      loginWithGoogle: vi.fn(),
      register: vi.fn(),
      updateProfile: vi.fn(),
      logout: vi.fn(),
    });
    setRole("owner");

    vi.mocked(api.reportTemplates).mockResolvedValue([
      {
        id: 1,
        key: "weekly_summary",
        name: "Weekly Summary",
        description: "",
        default_format: "json",
        ai_task_profile: null,
      },
    ]);
    vi.mocked(api.reports).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    vi.mocked(api.jobs).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    vi.mocked(api.notificationPreferences).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.notificationDeliveryLogs).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.inAppNotifications).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.organizationMembers).mockResolvedValue([]);
    vi.mocked(api.scheduledWorkflows).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.integrationProviders).mockResolvedValue([]);
    vi.mocked(api.integrationAccounts).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.dataDeletionRequests).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.aiProviders).mockResolvedValue([]);
    vi.mocked(api.aiTaskProfiles).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
    vi.mocked(api.aiDecisionLogs).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  });

  it("creates a report and renders backend report errors", async () => {
    vi.mocked(api.createReport).mockResolvedValue({
      id: 11,
      organization: 1,
      title: "Weekly KPI Summary",
      status: "queued",
      requested_format: "json",
      result_summary: {},
      error_message: "",
      completed_at: null,
      created_at: "2026-06-10T00:00:00Z",
    });
    const browserUser = userEvent.setup();
    const { unmount } = renderPage(<ReportsPage />);

    await screen.findByRole("option", { name: "Weekly Summary" });
    await browserUser.click(screen.getByRole("button", { name: "Create" }));
    await screen.findByText("Report request created");
    expect(api.createReport).toHaveBeenCalledWith(
      "access-token",
      expect.objectContaining({
        organization_id: 1,
        template_key: "weekly_summary",
      }),
    );
    unmount();

    vi.mocked(api.createReport).mockRejectedValue(
      new ApiError("Limit reached", 402, { detail: "Generated report limit reached." }),
    );
    renderPage(<ReportsPage />);
    await screen.findByRole("option", { name: "Weekly Summary" });
    await browserUser.click(screen.getByRole("button", { name: "Create" }));
    await screen.findByText("detail: Generated report limit reached.");
  });

  it("hides sensitive job queries from members while keeping report summaries available", async () => {
    setRole("member");
    vi.mocked(api.reports).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 4,
          organization: 1,
          title: "Member-visible report",
          status: "succeeded",
          requested_format: "json",
          result_summary: {},
          error_message: "",
          completed_at: "2026-06-10T00:00:00Z",
          created_at: "2026-06-10T00:00:00Z",
        },
      ],
    });

    renderPage(<ReportsPage />);

    await screen.findByText("Member-visible report");
    expect(api.jobs).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Download Member-visible report" })).toBeNull();
  });

  it("marks in-app notifications read without exposing delivery-log queries to members", async () => {
    setRole("member");
    vi.mocked(api.inAppNotifications).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 8,
          organization: 1,
          event: "system_alert",
          title: "Member alert",
          message: "Review the report",
          target_url: "/dashboard/reports",
          is_read: false,
          read_at: null,
          created_at: "2026-06-10T00:00:00Z",
        },
      ],
    });
    vi.mocked(api.markInAppNotificationRead).mockResolvedValue({
      id: 8,
      organization: 1,
      event: "system_alert",
      title: "Member alert",
      message: "Review the report",
      target_url: "/dashboard/reports",
      is_read: true,
      read_at: "2026-06-10T00:01:00Z",
      created_at: "2026-06-10T00:00:00Z",
    });
    const browserUser = userEvent.setup();

    renderPage(<NotificationsPage />);

    await screen.findByText("Member alert");
    expect(api.notificationDeliveryLogs).not.toHaveBeenCalled();
    await browserUser.click(screen.getByRole("button", { name: "Mark Member alert read" }));
    await waitFor(() => expect(api.markInAppNotificationRead).toHaveBeenCalledWith("access-token", 8));
  });

  it("keeps billing provider actions role-gated and renders checkout failures for admins", async () => {
    const plans = [
      {
        id: 1,
        name: "Free",
        slug: "free",
        description: "",
        features: {},
        limits: {},
        is_public: true,
        display_order: 1,
      },
      {
        id: 2,
        name: "Pro",
        slug: "pro",
        description: "",
        features: {},
        limits: {},
        is_public: true,
        display_order: 2,
      },
    ];
    vi.mocked(api.plans).mockResolvedValue(plans);
    vi.mocked(api.subscription).mockResolvedValue({
      id: 1,
      organization: 1,
      plan: plans[0],
      status: "free",
      cancel_at_period_end: false,
      current_period_start: null,
      current_period_end: null,
    });
    vi.mocked(api.usageSummary).mockResolvedValue({
      plan: { slug: "free", name: "Free", status: "free" },
      period: null,
      metrics: [],
    });
    vi.mocked(api.entitlements).mockResolvedValue({
      organization: 1,
      plan: { slug: "free", name: "Free", status: "free" },
      features: {},
    });
    setRole("member");
    const { unmount } = renderPage(<BillingPage />);

    const memberModifyButton = await screen.findByRole("button", { name: "Modify plan" });
    expect(memberModifyButton).toBeDisabled();
    expect(screen.queryByText("Stripe customer")).toBeNull();
    unmount();

    setRole("owner");
    vi.mocked(api.createCheckoutSession).mockRejectedValue(
      new ApiError("Stripe unavailable", 503, { detail: "Stripe is not configured yet." }),
    );
    const browserUser = userEvent.setup();
    renderPage(<BillingPage />);
    await browserUser.click(await screen.findByRole("button", { name: "Modify plan" }));
    await screen.findByText("detail: Stripe is not configured yet.");
  });

  it("updates profile details and reports password-change validation errors", async () => {
    const updateProfile = vi.fn().mockResolvedValue({ ...user, name: "Updated Owner" });
    vi.mocked(useAuth).mockReturnValue({
      accessToken: "access-token",
      user,
      isAuthenticated: true,
      isBootstrapping: false,
      login: vi.fn(),
      loginWithGoogle: vi.fn(),
      register: vi.fn(),
      updateProfile,
      logout: vi.fn(),
    });
    const browserUser = userEvent.setup();
    const { unmount } = renderPage(<AccountPage />);

    await browserUser.clear(screen.getByLabelText("Name"));
    await browserUser.type(screen.getByLabelText("Name"), "Updated Owner");
    await browserUser.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText("Profile updated");
    expect(updateProfile).toHaveBeenCalledWith({ name: "Updated Owner" });
    unmount();

    vi.mocked(api.changePassword).mockRejectedValue(
      new ApiError("Invalid current password", 400, {
        current_password: ["Current password is incorrect."],
      }),
    );
    renderPage(<SecurityPage />);
    await browserUser.type(screen.getByLabelText("Current password"), "WrongPassword!123");
    await browserUser.type(screen.getByLabelText("New password"), "NewPassword!123");
    await browserUser.click(screen.getByRole("button", { name: "Change password" }));
    await screen.findByText("current_password: Current password is incorrect.");
  });

  it("creates account deletion requests and renders privacy workflow failures", async () => {
    vi.mocked(api.createDataDeletionRequest).mockResolvedValue({
      id: 1,
      organization: 1,
      requested_by: 1,
      target: "account",
      status: "pending",
      reason: "User requested account removal from dashboard.",
      metadata: {},
      scheduled_for: null,
      completed_at: null,
      created_at: "2026-06-10T00:00:00Z",
      updated_at: "2026-06-10T00:00:00Z",
    });
    const browserUser = userEvent.setup();
    const { unmount } = renderPage(<DangerZonePage />);

    await browserUser.click(screen.getByRole("button", { name: "Request account removal" }));
    await screen.findByText("Account deletion request created");
    expect(api.createDataDeletionRequest).toHaveBeenCalledWith(
      "access-token",
      expect.objectContaining({ organization_id: 1, target: "account" }),
    );
    unmount();

    vi.mocked(api.createDataDeletionRequest).mockRejectedValue(
      new ApiError("Request blocked", 400, { detail: "A pending request already exists." }),
    );
    renderPage(<DangerZonePage />);
    await browserUser.click(screen.getByRole("button", { name: "Request account removal" }));
    await screen.findByText("detail: A pending request already exists.");
  });

  it("lets an organization admin connect a customer-managed API key provider", async () => {
    const openaiProvider = {
      id: 10,
      name: "OpenAI",
      slug: "openai",
      category: "ai",
      auth_type: "api_key",
      status: "available",
      description: "Use an organization-owned OpenAI API key.",
      credential_fields: [
        { key: "api_key", label: "OpenAI API key", secret: true, required: true },
      ],
      is_customer_configurable: true,
      health: { status: "ok", detail: "Available" },
    };
    vi.mocked(api.integrationProviders).mockResolvedValue([openaiProvider]);
    vi.mocked(api.connectIntegration).mockResolvedValue({
      id: 10,
      organization: 1,
      provider: openaiProvider,
      display_name: "OpenAI",
      status: "connected",
      has_credential: true,
      last_sync_at: null,
      created_at: "2026-06-11T00:00:00Z",
    });
    const browserUser = userEvent.setup();
    renderPage(<IntegrationsPage />);

    await browserUser.click(await screen.findByRole("button", { name: "Connect OpenAI" }));
    await browserUser.type(screen.getByLabelText("OpenAI API key"), "organization-secret");
    await browserUser.click(screen.getByRole("button", { name: "Connect" }));

    await screen.findByText("Integration connected");
    expect(api.connectIntegration).toHaveBeenCalledWith("access-token", "openai", {
      organization_id: 1,
      display_name: "OpenAI",
      credential_type: "api_key",
      credential_payload: { api_key: "organization-secret" },
    });
  });

  it("enforces member role-gating in settings and integrations", async () => {
    setRole("member");
    vi.mocked(api.integrationAccounts).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 3,
          organization: 1,
          provider: {
            id: 1,
            name: "Provider",
            slug: "provider",
            category: "test",
            auth_type: "api_key",
            status: "active",
            description: "Connected provider",
            credential_fields: [
              { key: "api_key", label: "API key", secret: true, required: true },
            ],
            is_customer_configurable: true,
            health: { status: "ok", detail: "Available" },
          },
          display_name: "Connected Provider",
          status: "connected",
          has_credential: true,
          last_sync_at: null,
          created_at: "2026-06-10T00:00:00Z",
        },
      ],
    });
    const { unmount } = renderPage(<SettingsPage />);

    await screen.findAllByText("Owner or admin access required");
    expect(api.organizationMembers).not.toHaveBeenCalled();
    expect(api.scheduledWorkflows).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save workspace" })).toBeDisabled();
    unmount();

    renderPage(<IntegrationsPage />);
    await screen.findByText("Connected Provider");
    expect(screen.queryByRole("button", { name: "Disconnect Connected Provider" })).toBeNull();
  });

  it("supports admin invitation actions and renders integration provider failures", async () => {
    vi.mocked(api.inviteOrganizationMember).mockResolvedValue({
      id: 4,
      organization: 1,
      user: null,
      role: "member",
      status: "invited",
      invited_email: "invitee@example.com",
      joined_at: "",
      created_at: "2026-06-10T00:00:00Z",
    });
    const browserUser = userEvent.setup();
    const { unmount } = renderPage(<SettingsPage />);

    await browserUser.type(screen.getByLabelText("Invite email"), "invitee@example.com");
    await browserUser.click(screen.getByRole("button", { name: "Invite" }));
    await screen.findByText("Invitation sent");
    expect(api.inviteOrganizationMember).toHaveBeenCalledWith("access-token", 1, {
      email: "invitee@example.com",
      role: "member",
    });
    unmount();

    vi.mocked(api.integrationAccounts).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 5,
          organization: 1,
          provider: {
            id: 1,
            name: "Provider",
            slug: "provider",
            category: "test",
            auth_type: "api_key",
            status: "active",
            description: "Connected provider",
            credential_fields: [
              { key: "api_key", label: "API key", secret: true, required: true },
            ],
            is_customer_configurable: true,
            health: { status: "ok", detail: "Available" },
          },
          display_name: "Connected Provider",
          status: "connected",
          has_credential: true,
          last_sync_at: null,
          created_at: "2026-06-10T00:00:00Z",
        },
      ],
    });
    vi.mocked(api.disconnectIntegration).mockRejectedValue(
      new ApiError("Provider failure", 503, { detail: "Provider is unavailable." }),
    );
    renderPage(<IntegrationsPage />);
    await browserUser.click(
      await screen.findByRole("button", { name: "Disconnect Connected Provider" }),
    );
    await screen.findByText("detail: Provider is unavailable.");
  });

  it("plans AI execution while keeping decision logs hidden from members", async () => {
    setRole("member");
    vi.mocked(api.aiTaskProfiles).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          key: "table_analysis",
          name: "Table Analysis",
          description: "",
          product_area: "reports",
        },
      ],
    });
    vi.mocked(api.aiExecutionPlan).mockResolvedValue({
      task_key: "table_analysis",
      task_profile_id: 1,
      decision_log_id: 1,
      strategy: "classic_ml",
      provider_slug: "",
      model: "",
      policy_id: null,
      requires_human_review: false,
      fallback: { strategy: "low_cost_llm", provider_slug: "", model: "" },
      fallback_chain: ["low_cost_llm"],
      reason: "Task can be solved by classic ML/DL libraries.",
      configuration: { status: "not_required", detail: "No provider needed." },
    });
    const browserUser = userEvent.setup();

    renderPage(<AIPage />);

    await screen.findByRole("option", { name: "Table Analysis" });
    expect(api.aiDecisionLogs).not.toHaveBeenCalled();
    await browserUser.click(screen.getByRole("button", { name: "Plan" }));
    await screen.findByText("Execution plan created");
    expect(api.aiExecutionPlan).toHaveBeenCalledWith(
      "access-token",
      expect.objectContaining({
        organization_id: 1,
        task_key: "table_analysis",
        constraints: { can_use_classic_ml: true },
      }),
    );
  });
});
