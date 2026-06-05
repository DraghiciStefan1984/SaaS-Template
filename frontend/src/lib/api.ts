import type {
  AIExecutionPlan,
  AIModelDecisionLog,
  AIProvider,
  AITaskProfile,
  AuthResponse,
  DataDeletionRequest,
  ExampleInsightRequest,
  IntegrationAccount,
  IntegrationProvider,
  JobRun,
  NotificationDeliveryLog,
  NotificationPreference,
  Organization,
  Paginated,
  Plan,
  Report,
  ReportTemplate,
  Subscription,
  UsageSummary,
  User,
} from "./types";

const API_PREFIX = "/api/v1";
const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
export function normalizeApiBaseUrl(value: string) {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

const API_BASE_URL = normalizeApiBaseUrl(RAW_API_BASE_URL);

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function flattenPayloadMessages(payload: unknown, prefix = ""): string[] {
  if (!payload) {
    return [];
  }
  if (typeof payload === "string") {
    return [prefix ? `${prefix}: ${payload}` : payload];
  }
  if (Array.isArray(payload)) {
    return payload.flatMap((item) => flattenPayloadMessages(item, prefix));
  }
  if (typeof payload === "object") {
    return Object.entries(payload).flatMap(([key, value]) =>
      flattenPayloadMessages(value, key === "non_field_errors" ? prefix : key),
    );
  }
  return [prefix ? `${prefix}: ${String(payload)}` : String(payload)];
}

export function getApiErrorMessage(error: unknown, fallback = "Request failed.") {
  if (error instanceof ApiError) {
    const fieldMessages = flattenPayloadMessages(error.payload);
    return fieldMessages.length ? fieldMessages.join(" ") : error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

type RequestOptions = {
  method?: string;
  token?: string;
  body?: unknown;
  skipAuthRefresh?: boolean;
};

type AuthTokenHandlers = {
  setAccessToken?: (token: string) => void;
  clearAuth?: () => void;
};

let authTokenHandlers: AuthTokenHandlers = {};

export function configureAuthTokenHandlers(handlers: AuthTokenHandlers) {
  authTokenHandlers = handlers;
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();
  headers.set("Accept", "application/json");
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (
      response.status === 401 &&
      options.token &&
      !options.skipAuthRefresh &&
      path !== "/auth/refresh/"
    ) {
      try {
        const refreshResponse = await api.refresh();
        authTokenHandlers.setAccessToken?.(refreshResponse.access);
        return apiRequest<T>(path, {
          ...options,
          token: refreshResponse.access,
          skipAuthRefresh: true,
        });
      } catch {
        authTokenHandlers.clearAuth?.();
      }
    }
    const fieldMessages = flattenPayloadMessages(payload);
    const message = fieldMessages[0] ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

export function listResults<T>(payload: Paginated<T> | T[] | undefined): T[] {
  if (!payload) {
    return [];
  }
  return Array.isArray(payload) ? payload : payload.results;
}

export const api = {
  login: (email: string, password: string) =>
    apiRequest<AuthResponse>("/auth/login/", {
      method: "POST",
      body: { email, password },
    }),
  register: (payload: {
    email: string;
    password: string;
    name: string;
    organization_name: string;
  }) =>
    apiRequest<AuthResponse>("/auth/register/", {
      method: "POST",
      body: payload,
    }),
  refresh: () =>
    apiRequest<{ access: string }>("/auth/refresh/", {
      method: "POST",
      body: {},
    }),
  logout: (token: string) =>
    apiRequest<void>("/auth/logout/", {
      method: "POST",
      token,
      body: {},
    }),
  me: (token: string) => apiRequest<User>("/auth/me/", { token }),
  updateMe: (token: string, payload: { name: string }) =>
    apiRequest<User>("/auth/me/", {
      method: "PATCH",
      token,
      body: payload,
    }),
  recoverPassword: (email: string) =>
    apiRequest<{ detail: string }>("/auth/password/recover/", {
      method: "POST",
      body: { email },
    }),
  changePassword: (
    token: string,
    payload: {
      current_password: string;
      new_password: string;
    },
  ) =>
    apiRequest<{ detail: string }>("/auth/password/change/", {
      method: "POST",
      token,
      body: payload,
    }),
  organizations: (token: string) =>
    apiRequest<Paginated<Organization> | Organization[]>("/organizations/", { token }),
  updateOrganization: (
    token: string,
    organizationId: number,
    payload: {
      name?: string;
      timezone?: string;
      default_language?: string;
    },
  ) =>
    apiRequest<Organization>(`/organizations/${organizationId}/`, {
      method: "PATCH",
      token,
      body: payload,
    }),
  plans: () => apiRequest<Plan[]>("/billing/plans/"),
  subscription: (token: string, organizationId: number) =>
    apiRequest<Subscription>(`/billing/subscription/?organization_id=${organizationId}`, { token }),
  createCheckoutSession: (
    token: string,
    payload: {
      organization_id: number;
      plan_slug: string;
      success_url?: string;
      cancel_url?: string;
    },
  ) =>
    apiRequest<{ checkout_url: string; checkout_session_id: string }>("/billing/checkout/", {
      method: "POST",
      token,
      body: payload,
    }),
  createCustomerPortalSession: (
    token: string,
    payload: {
      organization_id: number;
      return_url?: string;
    },
  ) =>
    apiRequest<{ portal_url: string }>("/billing/customer-portal/", {
      method: "POST",
      token,
      body: payload,
    }),
  usageSummary: (token: string, organizationId: number) =>
    apiRequest<UsageSummary>(`/usage/summary/?organization_id=${organizationId}`, { token }),
  integrationProviders: (token: string) =>
    apiRequest<IntegrationProvider[]>("/integrations/providers/", { token }),
  integrationAccounts: (token: string, organizationId: number) =>
    apiRequest<Paginated<IntegrationAccount>>(
      `/integrations/accounts/?organization_id=${organizationId}`,
      { token },
    ),
  aiProviders: (token: string) => apiRequest<AIProvider[]>("/ai/providers/", { token }),
  aiTaskProfiles: (token: string) =>
    apiRequest<Paginated<AITaskProfile>>("/ai/task-profiles/", { token }),
  aiExecutionPlan: (
    token: string,
    payload: {
      organization_id: number;
      task_key: string;
      input_payload?: Record<string, unknown>;
      constraints?: Record<string, unknown>;
      log_decision?: boolean;
    },
  ) =>
    apiRequest<AIExecutionPlan>("/ai/execution-plan/", {
      method: "POST",
      token,
      body: payload,
    }),
  aiDecisionLogs: (token: string, organizationId: number) =>
    apiRequest<Paginated<AIModelDecisionLog>>(
      `/ai/decision-logs/?organization_id=${organizationId}`,
      { token },
    ),
  reportTemplates: (token: string) =>
    apiRequest<ReportTemplate[]>("/reports/templates/", { token }),
  reports: (token: string, organizationId: number) =>
    apiRequest<Paginated<Report>>(`/reports/?organization_id=${organizationId}`, { token }),
  createReport: (
    token: string,
    payload: {
      organization_id: number;
      title: string;
      template_key: string;
      requested_format: string;
      input_payload: Record<string, unknown>;
    },
  ) =>
    apiRequest<Report>("/reports/", {
      method: "POST",
      token,
      body: payload,
    }),
  jobs: (token: string, organizationId: number) =>
    apiRequest<Paginated<JobRun>>(`/jobs/?organization_id=${organizationId}`, { token }),
  notificationPreferences: (token: string, organizationId: number) =>
    apiRequest<Paginated<NotificationPreference>>(
      `/notifications/preferences/?organization_id=${organizationId}`,
      { token },
    ),
  upsertNotificationPreference: (
    token: string,
    payload: {
      organization_id: number;
      user_id?: number;
      event: string;
      channel: string;
      is_enabled: boolean;
    },
  ) =>
    apiRequest<NotificationPreference>("/notifications/preferences/", {
      method: "POST",
      token,
      body: payload,
    }),
  notificationDeliveryLogs: (token: string, organizationId: number) =>
    apiRequest<Paginated<NotificationDeliveryLog>>(
      `/notifications/delivery-logs/?organization_id=${organizationId}`,
      { token },
    ),
  dataDeletionRequests: (token: string, organizationId: number) =>
    apiRequest<Paginated<DataDeletionRequest>>(
      `/privacy/deletion-requests/?organization_id=${organizationId}`,
      { token },
    ),
  createDataDeletionRequest: (
    token: string,
    payload: {
      organization_id: number;
      target: "account" | "organization";
      reason: string;
    },
  ) =>
    apiRequest<DataDeletionRequest>("/privacy/deletion-requests/", {
      method: "POST",
      token,
      body: payload,
    }),
  exampleInsightRequests: (token: string, organizationId: number) =>
    apiRequest<Paginated<ExampleInsightRequest>>(
      `/products/example-insights/requests/?organization_id=${organizationId}`,
      { token },
    ),
  createExampleInsightRequest: (
    token: string,
    payload: {
      organization_id: number;
      title: string;
      input_payload: Record<string, unknown>;
      constraints: Record<string, unknown>;
    },
  ) =>
    apiRequest<ExampleInsightRequest>("/products/example-insights/requests/", {
      method: "POST",
      token,
      body: payload,
    }),
};
