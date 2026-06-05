import { Mail, Phone, UserRound } from "lucide-react";

import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { useWorkspace } from "../lib/workspace";

export function AccountPage() {
  const { user } = useAuth();
  const { selectedOrganization } = useWorkspace();

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
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Contact</h2>
            <Mail aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Contact email
              <input readOnly type="email" value={user?.email ?? ""} />
            </label>
            <label>
              Phone
              <input placeholder="Not set" readOnly type="tel" />
            </label>
            <label>
              Organization
              <input readOnly type="text" value={selectedOrganization?.name ?? ""} />
            </label>
            <button className="secondary-button" disabled type="button">
              <Phone aria-hidden="true" size={18} />
              Save contact
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
