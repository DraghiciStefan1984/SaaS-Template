import { useOutletContext } from "react-router-dom";

import type { Organization } from "./types";

export type WorkspaceContext = {
  organizations: Organization[];
  selectedOrganization: Organization | null;
};

export function useWorkspace() {
  return useOutletContext<WorkspaceContext>();
}

export function isOrganizationAdmin(organization: Organization | null) {
  return organization?.my_role === "owner" || organization?.my_role === "admin";
}
