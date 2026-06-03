import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { ErrorState, LoadingState } from "./components/StateBlock";
import { api, listResults } from "./lib/api";
import { AuthProvider, useAuth } from "./lib/auth";
import type { Organization } from "./lib/types";
import { AIPage } from "./pages/AIPage";
import { AuthPage } from "./pages/AuthPage";
import { BillingPage } from "./pages/BillingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ExampleProductPage } from "./pages/ExampleProductPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { ReportsPage } from "./pages/ReportsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 20_000,
    },
  },
});

function ProtectedWorkspace() {
  const { accessToken, isAuthenticated } = useAuth();
  const [selectedOrganizationId, setSelectedOrganizationId] = useState<number | null>(null);

  const organizationsQuery = useQuery({
    enabled: isAuthenticated,
    queryKey: ["organizations"],
    queryFn: () => api.organizations(accessToken),
  });

  const organizations = useMemo<Organization[]>(
    () => listResults(organizationsQuery.data),
    [organizationsQuery.data],
  );
  const selectedOrganization = useMemo(
    () =>
      organizations.find((organization) => organization.id === selectedOrganizationId) ??
      organizations[0] ??
      null,
    [organizations, selectedOrganizationId],
  );

  if (!isAuthenticated) {
    return <Navigate replace to="/auth" />;
  }

  if (organizationsQuery.isLoading) {
    return (
      <main className="center-layout">
        <LoadingState title="Loading organizations" />
      </main>
    );
  }

  if (organizationsQuery.isError) {
    return (
      <main className="center-layout">
        <ErrorState title="Organizations unavailable" />
      </main>
    );
  }

  return (
    <AppLayout
      onOrganizationChange={setSelectedOrganizationId}
      organizations={organizations}
      outletContext={{ organizations, selectedOrganization }}
      selectedOrganizationId={selectedOrganization?.id ?? null}
    />
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthPage />} path="/auth" />
      <Route element={<ProtectedWorkspace />}>
        <Route element={<DashboardPage />} index />
        <Route element={<BillingPage />} path="billing" />
        <Route element={<IntegrationsPage />} path="integrations" />
        <Route element={<AIPage />} path="ai" />
        <Route element={<ReportsPage />} path="reports" />
        <Route element={<NotificationsPage />} path="notifications" />
        <Route element={<ExampleProductPage />} path="example-product" />
      </Route>
      <Route element={<Navigate replace to="/" />} path="*" />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
