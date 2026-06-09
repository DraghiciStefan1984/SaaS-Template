import { PlugZap, RefreshCw, Unplug } from "lucide-react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

export function IntegrationsPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const canManage = isOrganizationAdmin(selectedOrganization);
  const [reconnectAccountId, setReconnectAccountId] = useState<number | null>(null);
  const [apiKey, setApiKey] = useState("");

  const providersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryKey: ["integration-providers"],
    queryFn: () => api.integrationProviders(accessToken),
  });
  const accountsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["integration-accounts", organizationId],
    queryFn: () => api.integrationAccounts(accessToken, organizationId!),
  });

  const accounts = listResults(accountsQuery.data);
  const disconnectMutation = useMutation({
    mutationFn: (accountId: number) => api.disconnectIntegration(accessToken, accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-accounts", organizationId] });
    },
  });
  const reconnectMutation = useMutation({
    mutationFn: (accountId: number) => {
      const account = accounts.find((candidate) => candidate.id === accountId);
      const payload =
        account?.provider.auth_type === "api_key"
          ? { credential_type: "api_key", credential_payload: { api_key: apiKey } }
          : {};
      return api.reconnectIntegration(accessToken, accountId, payload);
    },
    onSuccess: () => {
      setApiKey("");
      setReconnectAccountId(null);
      queryClient.invalidateQueries({ queryKey: ["integration-accounts", organizationId] });
    },
  });
  const mutationError = disconnectMutation.error ?? reconnectMutation.error;

  return (
    <>
      <PageHeader eyebrow="Integrations" icon={PlugZap} title="Provider Registry" />

      {providersQuery.isLoading || accountsQuery.isLoading ? (
        <LoadingState title="Loading integrations" />
      ) : null}
      {providersQuery.isError || accountsQuery.isError ? (
        <ErrorState title="Integrations unavailable" />
      ) : null}
      {mutationError ? (
        <ErrorState detail={getApiErrorMessage(mutationError)} title="Integration action failed" />
      ) : null}
      {disconnectMutation.isSuccess ? <SuccessState title="Integration disconnected" /> : null}
      {reconnectMutation.isSuccess ? <SuccessState title="Integration reconnected" /> : null}

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Providers</h2>
          </div>
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Auth</th>
                  <th>Status</th>
                  <th>Health</th>
                </tr>
              </thead>
              <tbody>
                {(providersQuery.data ?? []).map((provider) => (
                  <tr key={provider.id}>
                    <td>{provider.name}</td>
                    <td>{provider.auth_type}</td>
                    <td>
                      <StatusBadge value={provider.status} />
                    </td>
                    <td>
                      <StatusBadge value={provider.health.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Connected Accounts</h2>
          </div>
          {accounts.length ? (
            <div className="compact-list">
              {accounts.map((account) => (
                <div className="compact-row" key={account.id}>
                  <div>
                    <strong>{account.display_name || account.provider.name}</strong>
                    <span>{formatDate(account.last_sync_at ?? account.created_at)}</span>
                  </div>
                  <div className="row-actions">
                    <StatusBadge value={account.status} />
                    {canManage && account.status === "connected" ? (
                      <button
                        aria-label={`Disconnect ${account.display_name || account.provider.name}`}
                        className="icon-button"
                        disabled={disconnectMutation.isPending}
                        onClick={() => disconnectMutation.mutate(account.id)}
                        title="Disconnect"
                        type="button"
                      >
                        <Unplug aria-hidden="true" size={16} />
                      </button>
                    ) : null}
                    {canManage &&
                    account.status !== "connected" &&
                    account.provider.auth_type !== "oauth2" ? (
                      <button
                        aria-label={`Reconnect ${account.display_name || account.provider.name}`}
                        className="icon-button"
                        disabled={reconnectMutation.isPending}
                        onClick={() => {
                          if (account.provider.auth_type === "api_key") {
                            setReconnectAccountId(account.id);
                          } else {
                            reconnectMutation.mutate(account.id);
                          }
                        }}
                        title="Reconnect"
                        type="button"
                      >
                        <RefreshCw aria-hidden="true" size={16} />
                      </button>
                    ) : null}
                    {canManage &&
                    account.status !== "connected" &&
                    account.provider.auth_type === "oauth2" ? (
                      <span>OAuth setup required</span>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No connected accounts" />
          )}
          {reconnectAccountId ? (
            <form
              className="form-grid panel-action"
              onSubmit={(event) => {
                event.preventDefault();
                reconnectMutation.mutate(reconnectAccountId);
              }}
            >
              <label>
                Replacement API key
                <input
                  autoComplete="off"
                  onChange={(event) => setApiKey(event.target.value)}
                  required
                  type="password"
                  value={apiKey}
                />
              </label>
              <div className="row-actions">
                <button
                  className="secondary-button"
                  onClick={() => {
                    setApiKey("");
                    setReconnectAccountId(null);
                  }}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className="primary-button"
                  disabled={reconnectMutation.isPending}
                  type="submit"
                >
                  <RefreshCw aria-hidden="true" size={16} />
                  Reconnect
                </button>
              </div>
            </form>
          ) : null}
        </div>
      </section>
    </>
  );
}
