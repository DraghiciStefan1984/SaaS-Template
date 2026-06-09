import { CreditCard, Gauge } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatLimit } from "../lib/format";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

export function BillingPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const canInspectBillingProvider = isOrganizationAdmin(selectedOrganization);
  const billingReturnUrl = `${window.location.origin}/dashboard/plan`;

  const plansQuery = useQuery({
    queryKey: ["plans"],
    queryFn: api.plans,
  });
  const subscriptionQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["subscription", organizationId],
    queryFn: () => api.subscription(accessToken, organizationId!),
  });
  const usageQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["usage", organizationId],
    queryFn: () => api.usageSummary(accessToken, organizationId!),
  });
  const entitlementsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["entitlements", organizationId],
    queryFn: () => api.entitlements(accessToken, organizationId!),
  });
  const checkoutMutation = useMutation({
    mutationFn: (planSlug: string) =>
      api.createCheckoutSession(accessToken, {
        organization_id: organizationId!,
        plan_slug: planSlug,
        success_url: billingReturnUrl,
        cancel_url: billingReturnUrl,
      }),
    onSuccess: (session) => {
      window.location.assign(session.checkout_url);
    },
  });
  const portalMutation = useMutation({
    mutationFn: () =>
      api.createCustomerPortalSession(accessToken, {
        organization_id: organizationId!,
        return_url: billingReturnUrl,
      }),
    onSuccess: (session) => {
      window.location.assign(session.portal_url);
    },
  });

  return (
    <>
      <PageHeader eyebrow="Plan" icon={CreditCard} title="Plan and Usage" />

      {plansQuery.isLoading ||
      subscriptionQuery.isLoading ||
      usageQuery.isLoading ||
      entitlementsQuery.isLoading ? (
        <LoadingState title="Loading billing data" />
      ) : null}
      {plansQuery.isError ||
      subscriptionQuery.isError ||
      usageQuery.isError ||
      entitlementsQuery.isError ? (
        <ErrorState title="Billing data unavailable" />
      ) : null}
      {checkoutMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(checkoutMutation.error)}
          title="Checkout unavailable"
        />
      ) : null}
      {portalMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(portalMutation.error)}
          title="Customer portal unavailable"
        />
      ) : null}

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Current Subscription</h2>
            {subscriptionQuery.data?.status ? (
              <StatusBadge value={subscriptionQuery.data.status} />
            ) : null}
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Plan</dt>
              <dd>{subscriptionQuery.data?.plan?.name ?? "n/a"}</dd>
            </div>
            <div>
              <dt>Cancel at period end</dt>
              <dd>{subscriptionQuery.data?.cancel_at_period_end ? "Yes" : "No"}</dd>
            </div>
            {canInspectBillingProvider ? (
              <div>
                <dt>Stripe customer</dt>
                <dd>{subscriptionQuery.data?.stripe_customer_id ? "Connected" : "Not connected"}</dd>
              </div>
            ) : null}
          </dl>
          <button
            className="secondary-button panel-action"
            disabled={!organizationId || !canInspectBillingProvider || portalMutation.isPending}
            onClick={() => portalMutation.mutate()}
            type="button"
          >
            {portalMutation.isPending ? "Opening" : "Manage billing"}
          </button>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Usage Limits</h2>
            <Gauge aria-hidden="true" size={18} />
          </div>
          {usageQuery.data?.metrics.length ? (
            <div className="usage-list">
              {usageQuery.data.metrics.map((metric) => (
                <div className="usage-row" key={metric.metric_name}>
                  <span>{metric.metric_name.replaceAll("_", " ")}</span>
                  <strong>
                    {metric.used} / {formatLimit(metric.limit)}
                  </strong>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No usage metrics" />
          )}
        </div>
      </section>

      <section className="tool-panel">
        <div className="panel-heading">
          <h2>Enabled Features</h2>
          <StatusBadge value={entitlementsQuery.data?.plan?.slug ?? "none"} />
        </div>
        {Object.entries(entitlementsQuery.data?.features ?? {}).filter(([, enabled]) => enabled)
          .length ? (
          <div className="tag-list">
            {Object.entries(entitlementsQuery.data?.features ?? {})
              .filter(([, enabled]) => enabled)
              .map(([feature]) => (
                <span key={feature}>{feature.replaceAll("_", " ")}</span>
              ))}
          </div>
        ) : (
          <EmptyState title="No optional features enabled" />
        )}
      </section>

      <section className="list-grid" aria-label="Available plans">
        {(plansQuery.data ?? []).map((plan) => (
          <article className="list-card" key={plan.slug}>
            <div className="card-heading">
              <h3>{plan.name}</h3>
              <StatusBadge value={plan.slug} />
            </div>
            <p>{plan.description || "Core SaaS plan"}</p>
            <div className="tag-list">
              {Object.entries(plan.limits).map(([metric, limit]) => (
                <span key={metric}>
                  {metric.replaceAll("_", " ")}: {formatLimit(limit)}
                </span>
              ))}
            </div>
            <button
              className="secondary-button"
              disabled={
                !organizationId ||
                !canInspectBillingProvider ||
                plan.slug === "free" ||
                checkoutMutation.isPending
              }
              onClick={() => checkoutMutation.mutate(plan.slug)}
              type="button"
            >
              {plan.slug === "free" ? "Current free option" : "Modify plan"}
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
