import { BellRing, CalendarClock, Pause, Play, Plus, Settings, SlidersHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import type { Organization } from "../lib/types";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

function WorkspaceDefaultsPanel({
  accessToken,
  canEditWorkspace,
  selectedOrganization,
}: {
  accessToken: string;
  canEditWorkspace: boolean;
  selectedOrganization: Organization | null;
}) {
  const queryClient = useQueryClient();
  const [workspaceName, setWorkspaceName] = useState(selectedOrganization?.name ?? "");
  const [workspaceTimezone, setWorkspaceTimezone] = useState(
    selectedOrganization?.timezone ?? "UTC",
  );
  const [workspaceLanguage, setWorkspaceLanguage] = useState(
    selectedOrganization?.default_language ?? "en",
  );

  const updateOrganizationMutation = useMutation({
    mutationFn: () =>
      api.updateOrganization(accessToken, selectedOrganization!.id, {
        name: workspaceName,
        timezone: workspaceTimezone,
        default_language: workspaceLanguage,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });

  function handleWorkspaceSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateOrganizationMutation.mutate();
  }

  return (
    <div className="tool-panel">
      <div className="panel-heading">
        <h2>Workspace Defaults</h2>
        <StatusBadge value={canEditWorkspace ? "editable" : "admin only"} />
      </div>
      {updateOrganizationMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(updateOrganizationMutation.error)}
          title="Workspace settings failed"
        />
      ) : null}
      {updateOrganizationMutation.isSuccess ? <SuccessState title="Workspace settings saved" /> : null}
      <form className="form-grid" onSubmit={handleWorkspaceSave}>
        <label>
          Workspace name
          <input
            disabled={!canEditWorkspace}
            onChange={(event) => setWorkspaceName(event.target.value)}
            required
            type="text"
            value={workspaceName}
          />
        </label>
        <label>
          Workspace timezone
          <select
            disabled={!canEditWorkspace}
            onChange={(event) => setWorkspaceTimezone(event.target.value)}
            value={workspaceTimezone}
          >
            <option value="UTC">UTC</option>
            <option value="Europe/Bucharest">Europe/Bucharest</option>
            <option value="America/New_York">America/New_York</option>
          </select>
        </label>
        <label>
          Default language
          <select
            disabled={!canEditWorkspace}
            onChange={(event) => setWorkspaceLanguage(event.target.value)}
            value={workspaceLanguage}
          >
            <option value="en">English</option>
            <option value="ro">Romanian</option>
          </select>
        </label>
        <button
          className="secondary-button"
          disabled={!canEditWorkspace || updateOrganizationMutation.isPending}
          type="submit"
        >
          {updateOrganizationMutation.isPending ? "Saving" : "Save workspace"}
        </button>
      </form>
    </div>
  );
}

function ScheduledWorkflowsPanel({
  accessToken,
  canManage,
  selectedOrganization,
}: {
  accessToken: string;
  canManage: boolean;
  selectedOrganization: Organization | null;
}) {
  const queryClient = useQueryClient();
  const organizationId = selectedOrganization?.id;
  const [name, setName] = useState("Weekly report");
  const [title, setTitle] = useState("Weekly KPI Summary");
  const [frequency, setFrequency] = useState("weekly");
  const [timezone, setTimezone] = useState(selectedOrganization?.timezone ?? "UTC");
  const [templateKey, setTemplateKey] = useState("weekly_summary");

  const schedulesQuery = useQuery({
    enabled: Boolean(accessToken && organizationId && canManage),
    queryKey: ["scheduled-workflows", organizationId],
    queryFn: () => api.scheduledWorkflows(accessToken, organizationId!),
  });
  const templatesQuery = useQuery({
    enabled: Boolean(accessToken && canManage),
    queryKey: ["report-templates"],
    queryFn: () => api.reportTemplates(accessToken),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createScheduledWorkflow(accessToken, {
        organization_id: organizationId!,
        name,
        frequency,
        timezone,
        title,
        template_key: templateKey,
        requested_format:
          templatesQuery.data?.find((template) => template.key === templateKey)?.default_format ??
          "json",
        input_payload: {},
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduled-workflows", organizationId] });
    },
  });

  const actionMutation = useMutation({
    mutationFn: async ({ workflowId, action }: { workflowId: number; action: string }) => {
      if (action === "run") {
        await api.runScheduledWorkflow(accessToken, workflowId);
        return;
      }
      if (action === "pause") {
        await api.pauseScheduledWorkflow(accessToken, workflowId);
        return;
      }
      await api.resumeScheduledWorkflow(accessToken, workflowId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduled-workflows", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["reports", organizationId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", organizationId] });
    },
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createMutation.mutate();
  }

  const schedules = listResults(schedulesQuery.data);
  const mutationError = createMutation.error ?? actionMutation.error;

  return (
    <div className="tool-panel schedule-panel">
      <div className="panel-heading">
        <h2>Scheduled Reports</h2>
        <CalendarClock aria-hidden="true" size={18} />
      </div>
      {!canManage ? <EmptyState title="Owner or admin access required" /> : null}
      {schedulesQuery.isLoading || templatesQuery.isLoading ? (
        <LoadingState title="Loading schedules" />
      ) : null}
      {mutationError ? (
        <ErrorState detail={getApiErrorMessage(mutationError)} title="Schedule action failed" />
      ) : null}
      {createMutation.isSuccess ? <SuccessState title="Schedule created" /> : null}

      {canManage ? (
        <>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>
              Schedule name
              <input onChange={(event) => setName(event.target.value)} required value={name} />
            </label>
            <label>
              Report title
              <input onChange={(event) => setTitle(event.target.value)} required value={title} />
            </label>
            <label>
              Frequency
              <select onChange={(event) => setFrequency(event.target.value)} value={frequency}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label>
              Timezone
              <select onChange={(event) => setTimezone(event.target.value)} value={timezone}>
                <option value="UTC">UTC</option>
                <option value="Europe/Bucharest">Europe/Bucharest</option>
                <option value="America/New_York">America/New_York</option>
              </select>
            </label>
            <label>
              Template
              <select onChange={(event) => setTemplateKey(event.target.value)} value={templateKey}>
                {(templatesQuery.data ?? []).map((template) => (
                  <option key={template.key} value={template.key}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="secondary-button"
              disabled={!organizationId || createMutation.isPending || !templatesQuery.data?.length}
              type="submit"
            >
              <Plus aria-hidden="true" size={18} />
              {createMutation.isPending ? "Creating" : "Create schedule"}
            </button>
          </form>

          <div className="compact-list schedule-list">
            {schedules.map((schedule) => (
              <div className="compact-row" key={schedule.id}>
                <div>
                  <strong>{schedule.name}</strong>
                  <span>
                    {schedule.frequency} · next {formatDate(schedule.next_run_at)}
                  </span>
                </div>
                <div className="row-actions">
                  <StatusBadge value={schedule.status} />
                  <button
                    aria-label={`Run ${schedule.name}`}
                    className="icon-button"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate({ workflowId: schedule.id, action: "run" })}
                    title="Run now"
                    type="button"
                  >
                    <Play aria-hidden="true" size={16} />
                  </button>
                  <button
                    aria-label={`${schedule.status === "active" ? "Pause" : "Resume"} ${schedule.name}`}
                    className="icon-button"
                    disabled={actionMutation.isPending}
                    onClick={() =>
                      actionMutation.mutate({
                        workflowId: schedule.id,
                        action: schedule.status === "active" ? "pause" : "resume",
                      })
                    }
                    title={schedule.status === "active" ? "Pause" : "Resume"}
                    type="button"
                  >
                    {schedule.status === "active" ? (
                      <Pause aria-hidden="true" size={16} />
                    ) : (
                      <Play aria-hidden="true" size={16} />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
          {!schedulesQuery.isLoading && !schedules.length ? (
            <EmptyState title="No scheduled reports" />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export function SettingsPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const [summaryStyle, setSummaryStyle] = useState("concise");
  const canEditWorkspace = isOrganizationAdmin(selectedOrganization);

  return (
    <>
      <PageHeader eyebrow="Settings" icon={Settings} title="Product Settings" />

      <section className="settings-grid">
        <WorkspaceDefaultsPanel
          accessToken={accessToken}
          canEditWorkspace={canEditWorkspace}
          key={selectedOrganization?.id ?? "no-organization"}
          selectedOrganization={selectedOrganization}
        />

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Workflow</h2>
            <SlidersHorizontal aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Default workflow
              <select defaultValue="one_click">
                <option value="one_click">One-click report</option>
                <option value="no_click">No-click monitor</option>
              </select>
            </label>
            <label>
              Summary style
              <select onChange={(event) => setSummaryStyle(event.target.value)} value={summaryStyle}>
                <option value="concise">Concise</option>
                <option value="detailed">Detailed</option>
                <option value="executive">Executive</option>
              </select>
            </label>
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              Include AI conclusion
            </label>
          </form>
        </div>

        <ScheduledWorkflowsPanel
          accessToken={accessToken}
          canManage={canEditWorkspace}
          key={`schedules-${selectedOrganization?.id ?? "none"}`}
          selectedOrganization={selectedOrganization}
        />

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Delivery</h2>
            <BellRing aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              Email reports
            </label>
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              In-app alerts
            </label>
            <button className="secondary-button" disabled type="button">
              Save settings
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
