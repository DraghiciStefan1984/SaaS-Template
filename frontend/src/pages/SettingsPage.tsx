import { BellRing, CalendarClock, Settings, SlidersHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { ErrorState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
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

export function SettingsPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const [frequency, setFrequency] = useState("weekly");
  const [timezone, setTimezone] = useState("UTC");
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

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Schedule</h2>
            <CalendarClock aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Frequency
              <select onChange={(event) => setFrequency(event.target.value)} value={frequency}>
                <option value="manual">Manual only</option>
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
            <StatusBadge value={frequency === "manual" ? "manual" : "scheduled"} />
          </form>
        </div>

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
