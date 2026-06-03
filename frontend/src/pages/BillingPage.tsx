import { CreditCard, Gauge } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatLimit } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function BillingPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;

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

  return (
    <>
      <PageHeader eyebrow="Billing" icon={CreditCard} title="Plan and Usage" />

      {plansQuery.isLoading || subscriptionQuery.isLoading || usageQuery.isLoading ? (
        <LoadingState title="Loading billing data" />
      ) : null}
      {plansQuery.isError || subscriptionQuery.isError || usageQuery.isError ? (
        <ErrorState title="Billing data unavailable" />
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
            <div>
              <dt>Stripe customer</dt>
              <dd>{subscriptionQuery.data?.stripe_customer_id ? "Connected" : "Not connected"}</dd>
            </div>
          </dl>
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
          </article>
        ))}
      </section>
    </>
  );
}
