import { KeyRound, ShieldCheck } from "lucide-react";

import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../lib/auth";

export function SecurityPage() {
  const { user } = useAuth();

  return (
    <>
      <PageHeader eyebrow="Security" icon={ShieldCheck} title="Password and Session" />

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Password</h2>
            <KeyRound aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Current password
              <input autoComplete="current-password" disabled type="password" />
            </label>
            <label>
              New password
              <input autoComplete="new-password" disabled type="password" />
            </label>
            <button className="secondary-button" disabled type="button">
              Change password
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
