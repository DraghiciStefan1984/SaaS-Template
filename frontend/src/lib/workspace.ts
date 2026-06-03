import { useOutletContext } from "react-router-dom";

import type { Organization } from "./types";

export type WorkspaceContext = {
  organizations: Organization[];
  selectedOrganization: Organization | null;
};

export function useWorkspace() {
  return useOutletContext<WorkspaceContext>();
}
