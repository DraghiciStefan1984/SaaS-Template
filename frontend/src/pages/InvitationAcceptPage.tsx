import { UserPlus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState, SuccessState } from "../components/StateBlock";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

export function InvitationAcceptPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const invitationToken = searchParams.get("token") ?? "";
  const { accessToken, isAuthenticated } = useAuth();
  const acceptMutation = useMutation({
    mutationFn: () => api.acceptOrganizationInvitation(accessToken, invitationToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  const returnPath = `/accept-invitation?token=${encodeURIComponent(invitationToken)}`;

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <div className="auth-heading">
          <span className="title-icon">
            <UserPlus aria-hidden="true" size={20} />
          </span>
          <div>
            <p className="eyebrow">Organization</p>
            <h1>Accept Invitation</h1>
          </div>
        </div>

        {!invitationToken ? (
          <ErrorState title="This invitation link is incomplete" />
        ) : acceptMutation.isError ? (
          <ErrorState
            detail={getApiErrorMessage(acceptMutation.error)}
            title="Invitation could not be accepted"
          />
        ) : acceptMutation.isSuccess ? (
          <SuccessState title="Invitation accepted" />
        ) : null}

        {acceptMutation.isSuccess ? (
          <Link className="primary-button" to="/dashboard">
            Open Dashboard
          </Link>
        ) : isAuthenticated ? (
          <button
            className="primary-button"
            disabled={!invitationToken || acceptMutation.isPending}
            onClick={() => acceptMutation.mutate()}
            type="button"
          >
            {acceptMutation.isPending ? "Accepting" : "Accept Invitation"}
          </button>
        ) : (
          <Link className="primary-button" to={`/login?next=${encodeURIComponent(returnPath)}`}>
            Sign In to Accept
          </Link>
        )}
      </section>
    </main>
  );
}
