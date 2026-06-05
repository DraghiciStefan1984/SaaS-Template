import { AlertTriangle, Trash2 } from "lucide-react";

import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../lib/auth";
import { useWorkspace } from "../lib/workspace";

export function DangerZonePage() {
  const { user } = useAuth();
  const { selectedOrganization } = useWorkspace();

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
        <button className="danger-button" disabled type="button">
          Request account removal
        </button>
      </section>
    </>
  );
}
