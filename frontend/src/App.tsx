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
import { AccountPage } from "./pages/AccountPage";
import { DangerZonePage } from "./pages/DangerZonePage";
import { DashboardPage } from "./pages/DashboardPage";
import { ExampleProductPage } from "./pages/ExampleProductPage";
import { EmailVerificationPage } from "./pages/EmailVerificationPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { LandingPage } from "./pages/LandingPage";
import { LegalPage } from "./pages/LegalPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PasswordResetPage } from "./pages/PasswordResetPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SecurityPage } from "./pages/SecurityPage";
import { SettingsPage } from "./pages/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 20_000,
    },
  },
});

function ProtectedWorkspace() {
  const { accessToken, isAuthenticated, isBootstrapping } = useAuth();
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

  if (isBootstrapping || organizationsQuery.isLoading) {
    return (
      <main className="center-layout">
        <LoadingState title="Loading organizations" />
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Navigate replace to="/login" />;
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
      <Route element={<LandingPage />} path="/" />
      <Route element={<LegalPage />} path="/terms" />
      <Route element={<Navigate replace to="/login" />} path="/auth" />
      <Route element={<AuthPage initialMode="login" />} path="/login" />
      <Route element={<AuthPage initialMode="register" />} path="/register" />
      <Route element={<AuthPage initialMode="recover" />} path="/recover-password" />
      <Route element={<PasswordResetPage />} path="/reset-password" />
      <Route element={<EmailVerificationPage />} path="/verify-email" />
      <Route element={<ProtectedWorkspace />} path="/dashboard">
        <Route element={<DashboardPage />} index />
        <Route element={<ExampleProductPage />} path="product" />
        <Route element={<ReportsPage />} path="reports" />
        <Route element={<AccountPage />} path="account" />
        <Route element={<SettingsPage />} path="settings" />
        <Route element={<BillingPage />} path="plan" />
        <Route element={<SecurityPage />} path="security" />
        <Route element={<IntegrationsPage />} path="integrations" />
        <Route element={<NotificationsPage />} path="notifications" />
        <Route element={<AIPage />} path="ai" />
        <Route element={<DangerZonePage />} path="danger-zone" />
      </Route>
      <Route element={<Navigate replace to="/dashboard" />} path="/app" />
      <Route element={<Navigate replace to="/dashboard/plan" />} path="/billing" />
      <Route element={<Navigate replace to="/dashboard/integrations" />} path="/integrations" />
      <Route element={<Navigate replace to="/dashboard/ai" />} path="/ai" />
      <Route element={<Navigate replace to="/dashboard/reports" />} path="/reports" />
      <Route element={<Navigate replace to="/dashboard/notifications" />} path="/notifications" />
      <Route element={<Navigate replace to="/dashboard/product" />} path="/example-product" />
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
