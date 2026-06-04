export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type User = {
  id: number;
  email: string;
  name: string;
  is_email_verified: boolean;
  account_status: string;
  date_joined: string;
};

export type AuthTokens = {
  access: string;
  refresh?: string;
};

export type AuthResponse = {
  access?: string;
  refresh?: string;
  user: User;
  tokens?: AuthTokens;
};

export type Organization = {
  id: number;
  name: string;
  timezone: string;
  default_language: string;
  my_role: string | null;
  created_at: string;
  updated_at: string;
};

export type Plan = {
  id: number;
  name: string;
  slug: string;
  description: string;
  features: string[];
  limits: Record<string, unknown>;
  is_public: boolean;
  display_order: number;
};

export type Subscription = {
  id: number;
  organization: number;
  plan: Plan;
  status: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  cancel_at_period_end: boolean;
  current_period_start: string | null;
  current_period_end: string | null;
};

export type UsageMetric = {
  metric_name: string;
  used: string;
  limit: unknown;
};

export type UsageSummary = {
  plan: {
    slug: string;
    name: string;
    status: string;
  } | null;
  period: {
    start: string;
    end: string;
  } | null;
  metrics: UsageMetric[];
};

export type IntegrationProvider = {
  id: number;
  name: string;
  slug: string;
  category: string;
  auth_type: string;
  status: string;
  health: {
    status: string;
    detail: string;
  };
};

export type IntegrationAccount = {
  id: number;
  organization: number;
  provider: IntegrationProvider;
  external_account_id: string;
  display_name: string;
  status: string;
  has_credential: boolean;
  last_sync_at: string | null;
  created_at: string;
};

export type AIProvider = {
  id: number;
  name: string;
  slug: string;
  status: string;
  default_model: string;
  supported_features: Record<string, unknown>;
  configuration: {
    status: string;
    detail: string;
  };
};

export type AITaskProfile = {
  id: number;
  key: string;
  name: string;
  product_area: string;
  default_strategy: string;
  allowed_strategies: string[];
  expected_runs_per_month: number;
  max_cost_per_run: string;
  is_high_risk: boolean;
};

export type AIExecutionPlan = {
  task_key: string;
  task_profile_id: number;
  decision_log_id: number | null;
  strategy: string;
  provider_slug: string;
  model: string;
  policy_id: number | null;
  requires_human_review: boolean;
  fallback: {
    strategy: string;
    provider_slug: string;
    model: string;
  };
  fallback_chain: string[];
  reason: string;
  configuration: {
    status: string;
    detail: string;
  };
};

export type AIModelDecisionLog = {
  id: number;
  organization: number;
  task_key: string;
  selected_strategy: string;
  selected_model: string;
  requires_human_review: boolean;
  decision_reason: string;
  created_at: string;
};

export type ReportTemplate = {
  id: number;
  key: string;
  name: string;
  description: string;
  default_format: string;
  ai_task_profile: number | null;
};

export type Report = {
  id: number;
  organization: number;
  title: string;
  status: string;
  requested_format: string;
  result_summary: Record<string, unknown>;
  error_message: string;
  completed_at: string | null;
  created_at: string;
  job_run_id?: number;
};

export type JobRun = {
  id: number;
  organization: number;
  name: string;
  task_name: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_error: string;
  created_at: string;
};

export type NotificationPreference = {
  id: number;
  organization: number;
  user: number | null;
  event: string;
  channel: string;
  is_enabled: boolean;
};

export type NotificationDeliveryLog = {
  id: number;
  organization: number;
  event: string;
  channel: string;
  status: string;
  recipient: string;
  subject: string;
  provider: string;
  error_message: string;
  created_at: string;
};

export type ExampleInsightRequest = {
  id: number;
  organization: number;
  report: number | null;
  job_run: number | null;
  title: string;
  status: string;
  strategy: string;
  created_at: string;
};
