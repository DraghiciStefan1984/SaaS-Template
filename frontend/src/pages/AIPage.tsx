import { Bot, WandSparkles } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

export function AIPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const canViewDecisionLogs = isOrganizationAdmin(selectedOrganization);
  const [taskKey, setTaskKey] = useState("table_analysis");
  const [strategyMode, setStrategyMode] = useState("can_use_classic_ml");

  const providersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryKey: ["ai-providers"],
    queryFn: () => api.aiProviders(accessToken),
  });
  const taskProfilesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryKey: ["ai-task-profiles"],
    queryFn: () => api.aiTaskProfiles(accessToken),
  });
  const decisionLogsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId && canViewDecisionLogs),
    queryKey: ["ai-decision-logs", organizationId],
    queryFn: () => api.aiDecisionLogs(accessToken, organizationId!),
  });

  const taskProfiles = listResults(taskProfilesQuery.data);
  const decisionLogs = listResults(decisionLogsQuery.data);
  const activeTaskProfile = useMemo(
    () => taskProfiles.find((profile) => profile.key === taskKey),
    [taskKey, taskProfiles],
  );

  const executionPlanMutation = useMutation({
    mutationFn: () =>
      api.aiExecutionPlan(accessToken, {
        organization_id: organizationId!,
        task_key: taskKey,
        input_payload: { sample: true, rows: 1000 },
        constraints:
          strategyMode === "cost_sensitivity"
            ? { cost_sensitivity: "high" }
            : { [strategyMode]: true },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-decision-logs", organizationId] });
    },
  });

  function handleExecutionPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    executionPlanMutation.mutate();
  }

  return (
    <>
      <PageHeader eyebrow="AI" icon={Bot} title="Decision Layer">
        <form className="inline-form" onSubmit={handleExecutionPlan}>
          <select
            aria-label="AI task profile"
            onChange={(event) => setTaskKey(event.target.value)}
            value={taskKey}
          >
            {taskProfiles.map((profile) => (
              <option key={profile.key} value={profile.key}>
                {profile.name}
              </option>
            ))}
          </select>
          <select
            aria-label="AI strategy condition"
            onChange={(event) => setStrategyMode(event.target.value)}
            value={strategyMode}
          >
            <option value="can_solve_without_ai">Deterministic</option>
            <option value="can_use_classic_ml">Classic ML</option>
            <option value="can_use_local_model">Local model</option>
            <option value="cost_sensitivity">Cost sensitive</option>
          </select>
          <button
            className="primary-button"
            disabled={!organizationId || executionPlanMutation.isPending}
            type="submit"
          >
            <WandSparkles aria-hidden="true" size={18} />
            {executionPlanMutation.isPending ? "Planning" : "Plan"}
          </button>
        </form>
      </PageHeader>

      {providersQuery.isLoading ||
      taskProfilesQuery.isLoading ||
      (canViewDecisionLogs && decisionLogsQuery.isLoading) ? (
        <LoadingState title="Loading AI data" />
      ) : null}
      {providersQuery.isError ||
      taskProfilesQuery.isError ||
      (canViewDecisionLogs && decisionLogsQuery.isError) ? (
        <ErrorState title="AI data unavailable" />
      ) : null}
      {executionPlanMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(executionPlanMutation.error)}
          title="Execution plan failed"
        />
      ) : null}
      {executionPlanMutation.isSuccess ? (
        <SuccessState title="Execution plan created" />
      ) : null}

      {executionPlanMutation.data ? (
        <section className="tool-panel">
          <div className="panel-heading">
            <h2>Latest Execution Plan</h2>
            <StatusBadge value={executionPlanMutation.data.strategy} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Reason</dt>
              <dd>{executionPlanMutation.data.reason}</dd>
            </div>
            <div>
              <dt>Provider</dt>
              <dd>{executionPlanMutation.data.provider_slug || "not required"}</dd>
            </div>
            <div>
              <dt>Configuration</dt>
              <dd>{executionPlanMutation.data.configuration.status}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Providers</h2>
          </div>
          <div className="compact-list">
            {(providersQuery.data ?? []).map((provider) => (
              <div className="compact-row" key={provider.id}>
                <div>
                  <strong>{provider.name}</strong>
                  <span>{provider.default_model || "default model not set"}</span>
                </div>
                <StatusBadge value={provider.configuration.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Task Profiles</h2>
            {activeTaskProfile ? <StatusBadge value={activeTaskProfile.default_strategy} /> : null}
          </div>
          <div className="compact-list">
            {taskProfiles.map((profile) => (
              <div className="compact-row" key={profile.id}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.expected_runs_per_month} runs/month</span>
                </div>
                <StatusBadge value={profile.default_strategy} />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="tool-panel">
        <div className="panel-heading">
          <h2>Decision Logs</h2>
        </div>
        {decisionLogs.length ? (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Strategy</th>
                  <th>Reason</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {decisionLogs.slice(0, 10).map((log) => (
                  <tr key={log.id}>
                    <td>{log.task_key}</td>
                    <td>
                      <StatusBadge value={log.selected_strategy} />
                    </td>
                    <td>{log.decision_reason}</td>
                    <td>{formatDate(log.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No decision logs" />
        )}
      </section>
    </>
  );
}
