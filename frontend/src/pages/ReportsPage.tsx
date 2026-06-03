import { FilePlus2, FileText } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function ReportsPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const [title, setTitle] = useState("Weekly KPI Summary");
  const [templateKey, setTemplateKey] = useState("weekly_summary");

  const templatesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryKey: ["report-templates"],
    queryFn: () => api.reportTemplates(accessToken),
  });
  const reportsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["reports", organizationId],
    queryFn: () => api.reports(accessToken, organizationId!),
  });
  const jobsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["jobs", organizationId],
    queryFn: () => api.jobs(accessToken, organizationId!),
  });

  const templates = useMemo(() => templatesQuery.data ?? [], [templatesQuery.data]);
  const reports = listResults(reportsQuery.data);
  const jobs = listResults(jobsQuery.data);
  const activeTemplate = useMemo(
    () => templates.find((template) => template.key === templateKey),
    [templateKey, templates],
  );

  const createReportMutation = useMutation({
    mutationFn: () =>
      api.createReport(accessToken, {
        organization_id: organizationId!,
        title,
        template_key: templateKey,
        requested_format: activeTemplate?.default_format ?? "json",
        input_payload: {
          metrics: {
            revenue: 1000,
            active_users: 120,
          },
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", organizationId] });
    },
  });

  function handleCreateReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createReportMutation.mutate();
  }

  return (
    <>
      <PageHeader eyebrow="Reports" icon={FileText} title="Report Workflow">
        <form className="inline-form" onSubmit={handleCreateReport}>
          <input
            aria-label="Report title"
            onChange={(event) => setTitle(event.target.value)}
            required
            type="text"
            value={title}
          />
          <select
            aria-label="Report template"
            onChange={(event) => setTemplateKey(event.target.value)}
            value={templateKey}
          >
            {templates.map((template) => (
              <option key={template.key} value={template.key}>
                {template.name}
              </option>
            ))}
          </select>
          <button
            className="primary-button"
            disabled={!organizationId || createReportMutation.isPending}
            type="submit"
          >
            <FilePlus2 aria-hidden="true" size={18} />
            {createReportMutation.isPending ? "Creating" : "Create"}
          </button>
        </form>
      </PageHeader>

      {templatesQuery.isLoading || reportsQuery.isLoading || jobsQuery.isLoading ? (
        <LoadingState title="Loading report workflow" />
      ) : null}
      {templatesQuery.isError || reportsQuery.isError || jobsQuery.isError ? (
        <ErrorState title="Report workflow unavailable" />
      ) : null}
      {createReportMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(createReportMutation.error)}
          title="Report request failed"
        />
      ) : null}
      {createReportMutation.isSuccess ? (
        <SuccessState
          detail={`Report ID ${createReportMutation.data.id}`}
          title="Report request created"
        />
      ) : null}

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Reports</h2>
          </div>
          {reports.length ? (
            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Format</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <tr key={report.id}>
                      <td>{report.title}</td>
                      <td>
                        <StatusBadge value={report.status} />
                      </td>
                      <td>{report.requested_format}</td>
                      <td>{formatDate(report.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No reports" />
          )}
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Job Runs</h2>
          </div>
          {jobs.length ? (
            <div className="compact-list">
              {jobs.slice(0, 10).map((job) => (
                <div className="compact-row" key={job.id}>
                  <div>
                    <strong>{job.name}</strong>
                    <span>
                      {job.attempts}/{job.max_attempts} attempts
                    </span>
                  </div>
                  <StatusBadge value={job.status} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No job runs" />
          )}
        </div>
      </section>
    </>
  );
}
