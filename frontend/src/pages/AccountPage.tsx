import { Mail, Save, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { ErrorState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function AccountPage() {
  const { accessToken, user, updateProfile } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const [name, setName] = useState(user?.name ?? "");

  const updateProfileMutation = useMutation({
    mutationFn: () => updateProfile({ name }),
  });
  const resendVerificationMutation = useMutation({
    mutationFn: () => api.resendEmailVerification(accessToken),
  });

  function handleProfileSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateProfileMutation.mutate();
  }

  return (
    <>
      <PageHeader eyebrow="Account" icon={UserRound} title="Personal Details" />

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Profile</h2>
            <StatusBadge value={user?.account_status ?? "unknown"} />
          </div>
          <dl className="detail-grid account-detail-grid">
            <div>
              <dt>Name</dt>
              <dd>{user?.name || "n/a"}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user?.email || "n/a"}</dd>
            </div>
            <div>
              <dt>Email verified</dt>
              <dd>{user?.is_email_verified ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>Not set</dd>
            </div>
            <div>
              <dt>Joined</dt>
              <dd>{user?.date_joined ? formatDate(user.date_joined) : "n/a"}</dd>
            </div>
            <div>
              <dt>Workspace role</dt>
              <dd>{selectedOrganization?.my_role ?? "n/a"}</dd>
            </div>
          </dl>
          {!user?.is_email_verified ? (
            <button
              className="secondary-button panel-action"
              disabled={resendVerificationMutation.isPending}
              onClick={() => resendVerificationMutation.mutate()}
              type="button"
            >
              <Mail aria-hidden="true" size={18} />
              {resendVerificationMutation.isPending ? "Sending" : "Resend verification email"}
            </button>
          ) : null}
          {resendVerificationMutation.isError ? (
            <ErrorState
              detail={getApiErrorMessage(resendVerificationMutation.error)}
              title="Verification email unavailable"
            />
          ) : null}
          {resendVerificationMutation.data ? (
            <SuccessState title={resendVerificationMutation.data.detail} />
          ) : null}
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Contact</h2>
            <Mail aria-hidden="true" size={18} />
          </div>
          {updateProfileMutation.isError ? (
            <ErrorState
              detail={getApiErrorMessage(updateProfileMutation.error)}
              title="Profile update failed"
            />
          ) : null}
          {updateProfileMutation.isSuccess ? <SuccessState title="Profile updated" /> : null}
          <form className="form-grid" onSubmit={handleProfileSave}>
            <label>
              Name
              <input
                autoComplete="name"
                onChange={(event) => setName(event.target.value)}
                type="text"
                value={name}
              />
            </label>
            <label>
              Contact email
              <input readOnly type="email" value={user?.email ?? ""} />
            </label>
            <label>
              Phone
              <input placeholder="Not modeled in the core user profile" readOnly type="tel" />
            </label>
            <label>
              Organization
              <input readOnly type="text" value={selectedOrganization?.name ?? ""} />
            </label>
            <button
              className="secondary-button"
              disabled={updateProfileMutation.isPending}
              type="submit"
            >
              <Save aria-hidden="true" size={18} />
              {updateProfileMutation.isPending ? "Saving" : "Save profile"}
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
