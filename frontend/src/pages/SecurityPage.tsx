import { KeyRound, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { PageHeader } from "../components/PageHeader";
import { ErrorState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

export function SecurityPage() {
  const { accessToken, user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const changePasswordMutation = useMutation({
    mutationFn: () =>
      api.changePassword(accessToken, {
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
    },
  });

  function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    changePasswordMutation.mutate();
  }

  return (
    <>
      <PageHeader eyebrow="Security" icon={ShieldCheck} title="Password and Session" />

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Password</h2>
            <KeyRound aria-hidden="true" size={18} />
          </div>
          {changePasswordMutation.isError ? (
            <ErrorState
              detail={getApiErrorMessage(changePasswordMutation.error)}
              title="Password change failed"
            />
          ) : null}
          {changePasswordMutation.isSuccess ? (
            <SuccessState title={changePasswordMutation.data.detail} />
          ) : null}
          <form className="form-grid" onSubmit={handlePasswordChange}>
            <label>
              Current password
              <input
                autoComplete="current-password"
                minLength={8}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
                type="password"
                value={currentPassword}
              />
            </label>
            <label>
              New password
              <input
                autoComplete="new-password"
                minLength={8}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                type="password"
                value={newPassword}
              />
            </label>
            <button
              className="secondary-button"
              disabled={changePasswordMutation.isPending}
              type="submit"
            >
              {changePasswordMutation.isPending ? "Changing" : "Change password"}
            </button>
          </form>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Session</h2>
            <StatusBadge value={user?.account_status ?? "unknown"} />
          </div>
          <dl className="detail-grid account-detail-grid">
            <div>
              <dt>Signed in as</dt>
              <dd>{user?.email ?? "n/a"}</dd>
            </div>
            <div>
              <dt>Refresh token</dt>
              <dd>HttpOnly cookie</dd>
            </div>
            <div>
              <dt>Access token</dt>
              <dd>Memory only</dd>
            </div>
          </dl>
        </div>
      </section>
    </>
  );
}
