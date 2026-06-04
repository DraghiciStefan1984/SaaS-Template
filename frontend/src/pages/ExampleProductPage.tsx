import { FlaskConical, Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function ExampleProductPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const [title, setTitle] = useState("Revenue Trend Insight");

  const requestsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["example-insight-requests", organizationId],
    queryFn: () => api.exampleInsightRequests(accessToken, organizationId!),
  });

  const createRequestMutation = useMutation({
    mutationFn: () =>
      api.createExampleInsightRequest(accessToken, {
        organization_id: organizationId!,
        title,
        input_payload: {
          rows: [
            { month: "January", revenue: 1000, users: 75 },
            { month: "February", revenue: 1250, users: 91 },
          ],
          metrics: ["revenue", "users"],
        },
        constraints: {
          can_use_classic_ml: true,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["example-insight-requests", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["reports", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["ai-decision-logs", organizationId] });
    },
  });

  function handleCreateRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createRequestMutation.mutate();
  }

  const requests = listResults(requestsQuery.data);

  return (
    <>
      <PageHeader eyebrow="Product Module" icon={FlaskConical} title="Example Insights">
        <form className="inline-form" onSubmit={handleCreateRequest}>
          <input
            aria-label="Insight title"
            onChange={(event) => setTitle(event.target.value)}
            required
            type="text"
            value={title}
          />
          <button
            className="primary-button"
            disabled={!organizationId || createRequestMutation.isPending}
            type="submit"
          >
            <Send aria-hidden="true" size={18} />
            {createRequestMutation.isPending ? "Creating" : "Create"}
          </button>
        </form>
      </PageHeader>

      {requestsQuery.isLoading ? <LoadingState title="Loading example product" /> : null}
      {requestsQuery.isError ? <ErrorState title="Example product unavailable" /> : null}
      {createRequestMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(createRequestMutation.error)}
          title="Insight request failed"
        />
      ) : null}
      {createRequestMutation.isSuccess ? (
        <SuccessState
          detail={`Strategy: ${createRequestMutation.data.strategy}`}
          title="Insight request created"
        />
      ) : null}

      <section className="tool-panel">
        <div className="panel-heading">
          <h2>Insight Requests</h2>
        </div>
        {requests.length ? (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Strategy</th>
                  <th>Report</th>
                  <th>Job</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.title}</td>
                    <td>
                      <StatusBadge value={request.status} />
                    </td>
                    <td>
                      <StatusBadge value={request.strategy || "planned"} />
                    </td>
                    <td>{request.report ?? "n/a"}</td>
                    <td>{request.job_run ?? "n/a"}</td>
                    <td>{formatDate(request.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No insight requests" />
        )}
      </section>
    </>
  );
}
