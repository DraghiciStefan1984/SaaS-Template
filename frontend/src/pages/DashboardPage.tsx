import {
  Bot,
  BriefcaseBusiness,
  Clock3,
  CreditCard,
  FileText,
  Mail,
  type LucideIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { ErrorState, LoadingState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatNumber } from "../lib/format";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

function MetricTile({
  label,
  value,
  icon: Icon,
  status,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  status?: string;
}) {
  return (
    <article className="metric-card">
      <Icon aria-hidden="true" size={22} />
      <span>{label}</span>
      <strong>{value}</strong>
      {status ? <StatusBadge value={status} /> : null}
    </article>
  );
}

export function DashboardPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const enabled = Boolean(accessToken && organizationId);
  const canViewOperations = isOrganizationAdmin(selectedOrganization);

  const subscriptionQuery = useQuery({
    enabled,
    queryKey: ["subscription", organizationId],
    queryFn: () => api.subscription(accessToken, organizationId!),
  });
  const usageQuery = useQuery({
    enabled,
    queryKey: ["usage", organizationId],
    queryFn: () => api.usageSummary(accessToken, organizationId!),
  });
  const reportsQuery = useQuery({
    enabled,
    queryKey: ["reports", organizationId],
    queryFn: () => api.reports(accessToken, organizationId!),
  });
  const jobsQuery = useQuery({
    enabled: enabled && canViewOperations,
    queryKey: ["jobs", organizationId],
    queryFn: () => api.jobs(accessToken, organizationId!),
  });
  const decisionsQuery = useQuery({
    enabled: enabled && canViewOperations,
    queryKey: ["ai-decision-logs", organizationId],
    queryFn: () => api.aiDecisionLogs(accessToken, organizationId!),
  });
  const notificationQuery = useQuery({
    enabled: enabled && canViewOperations,
    queryKey: ["notification-delivery-logs", organizationId],
    queryFn: () => api.notificationDeliveryLogs(accessToken, organizationId!),
  });

  if (!selectedOrganization) {
    return <ErrorState title="No organization available" />;
  }

  const isLoading =
    subscriptionQuery.isLoading ||
    usageQuery.isLoading ||
    reportsQuery.isLoading ||
    (canViewOperations && jobsQuery.isLoading) ||
    (canViewOperations && decisionsQuery.isLoading) ||
    (canViewOperations && notificationQuery.isLoading);

  const hasError =
    subscriptionQuery.isError ||
    usageQuery.isError ||
    reportsQuery.isError ||
    (canViewOperations && jobsQuery.isError) ||
    (canViewOperations && decisionsQuery.isError) ||
    (canViewOperations && notificationQuery.isError);

  const reports = listResults(reportsQuery.data);
  const jobs = listResults(jobsQuery.data);
  const decisions = listResults(decisionsQuery.data);
  const notifications = listResults(notificationQuery.data);
  const runningJobs = jobs.filter((job) => ["queued", "running", "retrying"].includes(job.status));

  return (
    <>
      <PageHeader eyebrow={selectedOrganization.name} icon={BriefcaseBusiness} title="Workspace Overview" />

      {isLoading ? <LoadingState title="Loading workspace data" /> : null}
      {hasError ? <ErrorState title="Workspace data unavailable" /> : null}

      <section className="metric-grid" aria-label="Workspace status">
        <MetricTile
          icon={CreditCard}
          label="Plan"
          status={subscriptionQuery.data?.status}
          value={subscriptionQuery.data?.plan?.name ?? "n/a"}
        />
        <MetricTile
          icon={FileText}
          label="Reports"
          value={formatNumber(reportsQuery.data?.count ?? reports.length)}
        />
        <MetricTile icon={Clock3} label="Active Jobs" value={formatNumber(runningJobs.length)} />
        <MetricTile
          icon={Bot}
          label="AI Decisions"
          value={canViewOperations ? formatNumber(decisionsQuery.data?.count ?? decisions.length) : "n/a"}
        />
        <MetricTile
          icon={Mail}
          label="Notifications"
          value={
            canViewOperations ? formatNumber(notificationQuery.data?.count ?? notifications.length) : "n/a"
          }
        />
      </section>

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Next Actions</h2>
          </div>
          <div className="compact-list">
            <div className="compact-row">
              <div>
                <strong>Configure product settings</strong>
                <span>Review workflow, schedule, and delivery defaults</span>
              </div>
              <StatusBadge value="settings" />
            </div>
            <div className="compact-row">
              <div>
                <strong>Generate a report</strong>
                <span>Use the reports or product section to create a workflow run</span>
              </div>
              <StatusBadge value="report" />
            </div>
          </div>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Usage</h2>
            {usageQuery.data?.plan ? <StatusBadge value={usageQuery.data.plan.status} /> : null}
          </div>
          <div className="usage-list">
            {(usageQuery.data?.metrics ?? []).slice(0, 4).map((metric) => (
              <div className="usage-row" key={metric.metric_name}>
                <span>{metric.metric_name.replaceAll("_", " ")}</span>
                <strong>{metric.used}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Latest Jobs</h2>
          </div>
          <div className="compact-list">
            {jobs.slice(0, 5).map((job) => (
              <div className="compact-row" key={job.id}>
                <span>{job.name}</span>
                <StatusBadge value={job.status} />
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
