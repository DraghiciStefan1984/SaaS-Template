import {
  Bot,
  BriefcaseBusiness,
  CreditCard,
  FileText,
  FlaskConical,
  Gauge,
  LogOut,
  Mail,
  PlugZap,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../lib/auth";
import type { Organization } from "../lib/types";
import type { WorkspaceContext } from "../lib/workspace";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/billing", label: "Billing", icon: CreditCard },
  { to: "/integrations", label: "Integrations", icon: PlugZap },
  { to: "/ai", label: "AI", icon: Bot },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/notifications", label: "Notifications", icon: Mail },
  { to: "/example-product", label: "Example Product", icon: FlaskConical },
];

export function AppLayout({
  organizations,
  selectedOrganizationId,
  onOrganizationChange,
  outletContext,
}: {
  organizations: Organization[];
  selectedOrganizationId: number | null;
  onOrganizationChange: (organizationId: number) => void;
  outletContext: WorkspaceContext;
}) {
  const { user, logout } = useAuth();

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-row">
          <div className="brand-mark">SC</div>
          <div>
            <strong>SaaS Core</strong>
            <span>Template</span>
          </div>
        </div>

        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                end={item.to === "/"}
                key={item.to}
                to={item.to}
              >
                <Icon aria-hidden="true" size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <label className="organization-select">
            <BriefcaseBusiness aria-hidden="true" size={18} />
            <select
              aria-label="Organization"
              disabled={organizations.length === 0}
              onChange={(event) => onOrganizationChange(Number(event.target.value))}
              value={selectedOrganizationId ?? ""}
            >
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
          </label>

          <div className="user-menu">
            <span>{user?.email}</span>
            <button aria-label="Log out" className="icon-button" onClick={logout} type="button">
              <LogOut aria-hidden="true" size={18} />
            </button>
          </div>
        </header>

        <Outlet context={outletContext} />
      </section>
    </main>
  );
}
