import { PlugZap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function IntegrationsPage() {
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;

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

  return (
    <>
      <PageHeader eyebrow="Integrations" icon={PlugZap} title="Provider Registry" />

      {providersQuery.isLoading || accountsQuery.isLoading ? (
        <LoadingState title="Loading integrations" />
      ) : null}
      {providersQuery.isError || accountsQuery.isError ? (
        <ErrorState title="Integrations unavailable" />
      ) : null}

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
                  <StatusBadge value={account.status} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No connected accounts" />
          )}
        </div>
      </section>
    </>
  );
}
