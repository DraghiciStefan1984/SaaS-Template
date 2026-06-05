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
  Settings,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../lib/auth";
import type { Organization } from "../lib/types";
import type { WorkspaceContext } from "../lib/workspace";

const navItems = [
  { to: "/dashboard", label: "Overview", icon: Gauge },
  { to: "/dashboard/product", label: "Product", icon: FlaskConical },
  { to: "/dashboard/reports", label: "Reports", icon: FileText },
  { to: "/dashboard/account", label: "Account", icon: UserRound },
  { to: "/dashboard/settings", label: "Settings", icon: Settings },
  { to: "/dashboard/plan", label: "Plan", icon: CreditCard },
  { to: "/dashboard/security", label: "Security", icon: ShieldCheck },
  { to: "/dashboard/integrations", label: "Integrations", icon: PlugZap },
  { to: "/dashboard/notifications", label: "Notifications", icon: Mail },
  { to: "/dashboard/ai", label: "AI Layer", icon: Bot },
  { to: "/dashboard/danger-zone", label: "Danger Zone", icon: Trash2 },
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
                end={item.to === "/dashboard"}
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
