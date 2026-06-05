import { AlertTriangle, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function DangerZonePage() {
  const queryClient = useQueryClient();
  const { accessToken, user } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const [reason, setReason] = useState("User requested account removal from dashboard.");

  const deletionRequestsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["privacy-deletion-requests", organizationId],
    queryFn: () => api.dataDeletionRequests(accessToken, organizationId!),
  });

  const createDeletionRequestMutation = useMutation({
    mutationFn: () =>
      api.createDataDeletionRequest(accessToken, {
        organization_id: organizationId!,
        target: "account",
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy-deletion-requests", organizationId] });
    },
  });

  function handleDeletionRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createDeletionRequestMutation.mutate();
  }

  const deletionRequests = listResults(deletionRequestsQuery.data);

  return (
    <>
      <PageHeader eyebrow="Danger zone" icon={Trash2} title="Remove Account" />

      <section className="danger-panel">
        <div className="panel-heading">
          <div>
            <h2>Account deletion request</h2>
            <p>
              {user?.email ?? "Current account"} in {selectedOrganization?.name ?? "workspace"}
            </p>
          </div>
          <StatusBadge value="manual review" />
        </div>
        <div className="danger-content">
          <AlertTriangle aria-hidden="true" size={22} />
          <p>
            Deletion should run through the privacy/anonymization workflow and preserve required
            compliance history.
          </p>
        </div>
        {deletionRequestsQuery.isLoading ? <LoadingState title="Loading deletion requests" /> : null}
        {deletionRequestsQuery.isError ? (
          <ErrorState title="Deletion requests unavailable" />
        ) : null}
        {createDeletionRequestMutation.isError ? (
          <ErrorState
            detail={getApiErrorMessage(createDeletionRequestMutation.error)}
            title="Deletion request failed"
          />
        ) : null}
        {createDeletionRequestMutation.isSuccess ? (
          <SuccessState title="Account deletion request created" />
        ) : null}
        <form className="form-grid" onSubmit={handleDeletionRequest}>
          <label>
            Reason
            <input
              onChange={(event) => setReason(event.target.value)}
              required
              type="text"
              value={reason}
            />
          </label>
          <button
            className="danger-button"
            disabled={!organizationId || createDeletionRequestMutation.isPending}
            type="submit"
          >
            {createDeletionRequestMutation.isPending ? "Requesting" : "Request account removal"}
          </button>
        </form>
        {deletionRequests.length ? (
          <div className="compact-list">
            {deletionRequests.slice(0, 5).map((request) => (
              <div className="compact-row" key={request.id}>
                <div>
                  <strong>{request.target} deletion</strong>
                  <span>{formatDate(request.created_at)}</span>
                </div>
                <StatusBadge value={request.status} />
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </>
  );
}
