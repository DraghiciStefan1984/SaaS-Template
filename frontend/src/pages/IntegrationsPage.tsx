import { KeyRound, Link, PlugZap, RefreshCw, Unplug, X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import type { IntegrationProvider } from "../lib/types";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

type CredentialValues = Record<string, string>;

function CredentialForm({
  provider,
  isPending,
  onCancel,
  onSubmit,
}: {
  provider: IntegrationProvider;
  isPending: boolean;
  onCancel: () => void;
  onSubmit: (values: CredentialValues) => void;
}) {
  const [values, setValues] = useState<CredentialValues>({});

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <form className="form-grid panel-action integration-credential-form" onSubmit={handleSubmit}>
      {provider.credential_fields.map((field) => (
        <label key={field.key}>
          {field.label}
          <input
            autoComplete="new-password"
            onChange={(event) =>
              setValues((current) => ({ ...current, [field.key]: event.target.value }))
            }
            required={field.required}
            type={field.secret ? "password" : "text"}
            value={values[field.key] ?? ""}
          />
        </label>
      ))}
      <div className="row-actions">
        <button className="secondary-button" onClick={onCancel} type="button">
          <X aria-hidden="true" size={16} />
          Cancel
        </button>
        <button className="primary-button" disabled={isPending} type="submit">
          <KeyRound aria-hidden="true" size={16} />
          Connect
        </button>
      </div>
    </form>
  );
}

export function IntegrationsPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const canManage = isOrganizationAdmin(selectedOrganization);
  const [connectProviderSlug, setConnectProviderSlug] = useState<string | null>(null);
  const [reconnectAccountId, setReconnectAccountId] = useState<number | null>(null);

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

  const providers = useMemo(
    () => (providersQuery.data ?? []).filter((provider) => provider.is_customer_configurable),
    [providersQuery.data],
  );
  const accounts = listResults(accountsQuery.data);
  const connectProvider =
    providers.find((provider) => provider.slug === connectProviderSlug) ?? null;
  const reconnectAccount =
    accounts.find((account) => account.id === reconnectAccountId) ?? null;

  function refreshAccounts() {
    queryClient.invalidateQueries({ queryKey: ["integration-accounts", organizationId] });
  }

  const connectMutation = useMutation({
    mutationFn: ({
      provider,
      credentials,
    }: {
      provider: IntegrationProvider;
      credentials: CredentialValues;
    }) =>
      api.connectIntegration(accessToken, provider.slug, {
        organization_id: organizationId!,
        display_name: provider.name,
        credential_type: "api_key",
        credential_payload: credentials,
      }),
    onSuccess: () => {
      setConnectProviderSlug(null);
      refreshAccounts();
    },
  });
  const disconnectMutation = useMutation({
    mutationFn: (accountId: number) => api.disconnectIntegration(accessToken, accountId),
    onSuccess: refreshAccounts,
  });
  const reconnectMutation = useMutation({
    mutationFn: ({
      accountId,
      credentials,
    }: {
      accountId: number;
      credentials: CredentialValues;
    }) =>
      api.reconnectIntegration(accessToken, accountId, {
        credential_type: "api_key",
        credential_payload: credentials,
      }),
    onSuccess: () => {
      setReconnectAccountId(null);
      refreshAccounts();
    },
  });
  const mutationError =
    connectMutation.error ?? disconnectMutation.error ?? reconnectMutation.error;

  return (
    <>
      <PageHeader eyebrow="Workspace" icon={PlugZap} title="Connections & API Keys" />

      {providersQuery.isLoading || accountsQuery.isLoading ? (
        <LoadingState title="Loading integrations" />
      ) : null}
      {providersQuery.isError || accountsQuery.isError ? (
        <ErrorState title="Integrations unavailable" />
      ) : null}
      {mutationError ? (
        <ErrorState detail={getApiErrorMessage(mutationError)} title="Integration action failed" />
      ) : null}
      {connectMutation.isSuccess ? <SuccessState title="Integration connected" /> : null}
      {disconnectMutation.isSuccess ? <SuccessState title="Integration disconnected" /> : null}
      {reconnectMutation.isSuccess ? <SuccessState title="Integration reconnected" /> : null}

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Available Providers</h2>
            <StatusBadge value={canManage ? "admin access" : "view only"} />
          </div>
          {providers.length ? (
            <div className="compact-list">
              {providers.map((provider) => {
                const account = accounts.find(
                  (candidate) =>
                    candidate.provider.slug === provider.slug && candidate.status === "connected",
                );
                return (
                  <div className="compact-row" key={provider.id}>
                    <div>
                      <strong>{provider.name}</strong>
                      <span>{provider.description || provider.category}</span>
                    </div>
                    <div className="row-actions">
                      <StatusBadge value={account ? "connected" : provider.health.status} />
                      {canManage && !account && provider.auth_type === "api_key" ? (
                        <button
                          aria-label={`Connect ${provider.name}`}
                          className="icon-button"
                          onClick={() => {
                            setReconnectAccountId(null);
                            setConnectProviderSlug(provider.slug);
                          }}
                          title="Connect"
                          type="button"
                        >
                          <Link aria-hidden="true" size={16} />
                        </button>
                      ) : null}
                      {!account && provider.auth_type === "oauth2" ? (
                        <span>OAuth setup required</span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState title="No providers available" />
          )}
          {connectProvider ? (
            <CredentialForm
              isPending={connectMutation.isPending}
              onCancel={() => setConnectProviderSlug(null)}
              onSubmit={(credentials) =>
                connectMutation.mutate({ provider: connectProvider, credentials })
              }
              provider={connectProvider}
            />
          ) : null}
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
                        title="Disconnect and delete credential"
                        type="button"
                      >
                        <Unplug aria-hidden="true" size={16} />
                      </button>
                    ) : null}
                    {canManage &&
                    account.status !== "connected" &&
                    account.provider.auth_type === "api_key" ? (
                      <button
                        aria-label={`Reconnect ${account.display_name || account.provider.name}`}
                        className="icon-button"
                        disabled={reconnectMutation.isPending}
                        onClick={() => {
                          setConnectProviderSlug(null);
                          setReconnectAccountId(account.id);
                        }}
                        title="Replace credential"
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
          {reconnectAccount ? (
            <CredentialForm
              isPending={reconnectMutation.isPending}
              onCancel={() => setReconnectAccountId(null)}
              onSubmit={(credentials) =>
                reconnectMutation.mutate({ accountId: reconnectAccount.id, credentials })
              }
              provider={reconnectAccount.provider}
            />
          ) : null}
        </div>
      </section>
    </>
  );
}
