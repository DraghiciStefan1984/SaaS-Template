import {
  ArrowRight,
  CheckCircle2,
  FileText,
  PlayCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatLimit } from "../lib/format";

const fallbackPlans = [
  {
    name: "Free",
    price: "$0",
    description: "Validate the workflow with low limits and demo reports.",
    features: ["Core dashboard", "Manual report requests", "Console notifications"],
  },
  {
    name: "Pro",
    price: "TBD",
    description: "For a focused SaaS with higher limits and report delivery.",
    features: ["More reports", "Scheduled jobs", "Email delivery when configured"],
  },
  {
    name: "Business",
    price: "TBD",
    description: "For teams, clients, or larger recurring workflows.",
    features: ["Team access", "Advanced integrations", "Priority workflows"],
  },
  {
    name: "Custom",
    price: "Contact",
    description: "For custom providers, security needs, or high-volume use.",
    features: ["Custom limits", "Provider setup", "Launch support"],
  },
];

const outcomes = [
  "Launch with auth, organizations, plans, reports, jobs, and notifications already shaped.",
  "Keep AI calls behind backend policy so cost and model choice stay controlled.",
  "Start Free-first locally, then activate Stripe, AWS, email, and providers when needed.",
];

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const plansQuery = useQuery({
    queryKey: ["public-plans"],
    queryFn: api.plans,
  });
  const plans = plansQuery.data?.length
    ? plansQuery.data.map((plan) => ({
        name: plan.name,
        price: plan.slug === "free" ? "$0" : "TBD",
        description: plan.description || "Reusable SaaS plan",
        features: plan.features.length
          ? plan.features
          : Object.entries(plan.limits).map(
              ([metric, limit]) => `${metric.replaceAll("_", " ")}: ${formatLimit(limit)}`,
            ),
      }))
    : fallbackPlans;

  return (
    <main className="public-shell">
      <header className="public-nav">
        <Link className="brand-row" to="/">
          <div className="brand-mark">SC</div>
          <div>
            <strong>SaaS Core</strong>
            <span>Template</span>
          </div>
        </Link>
        <nav className="public-links" aria-label="Public navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#plans">Plans</a>
          <a href="#faq">FAQ</a>
          <Link to="/terms">Terms</Link>
        </nav>
        <div className="nav-actions">
          <Link className="text-button" to="/login">
            Login
          </Link>
          <Link className="primary-button" to={isAuthenticated ? "/dashboard" : "/register"}>
            {isAuthenticated ? "Open dashboard" : "Register"}
          </Link>
        </div>
      </header>

      <section className="hero-section">
        <div className="hero-backdrop" aria-hidden="true">
          <div className="hero-report-panel">
            <div className="hero-report-topline" />
            <div className="hero-report-row strong" />
            <div className="hero-report-row" />
            <div className="hero-report-row short" />
          </div>
          <div className="hero-status-panel">
            <span />
            <span />
            <span />
          </div>
        </div>
        <div className="hero-content">
          <p className="eyebrow">Reusable AI SaaS foundation</p>
          <h1>Launch clear SaaS products from one stable core</h1>
          <p>
            A practical template for free-first SaaS products that turn setup or input into
            reports, alerts, dashboards, and controlled AI conclusions.
          </p>
          <div className="hero-actions">
            <Link className="primary-button" to={isAuthenticated ? "/dashboard" : "/register"}>
              <ArrowRight aria-hidden="true" size={18} />
              {isAuthenticated ? "Open dashboard" : "Start free"}
            </Link>
            <a className="secondary-button" href="#demo">
              <PlayCircle aria-hidden="true" size={18} />
              Watch demo
            </a>
          </div>
        </div>
      </section>

      <section className="public-section" id="how-it-works">
        <div className="section-heading">
          <p className="eyebrow">How it works</p>
          <h2>One reusable flow for one-click and no-click products</h2>
        </div>
        <div className="process-grid">
          <article>
            <Sparkles aria-hidden="true" size={22} />
            <h3>Input or connect</h3>
            <p>Users add data, connect a provider, or configure a recurring monitor.</p>
          </article>
          <article>
            <ShieldCheck aria-hidden="true" size={22} />
            <h3>Analyze safely</h3>
            <p>Backend services enforce organization scope, usage limits, and AI policy.</p>
          </article>
          <article>
            <FileText aria-hidden="true" size={22} />
            <h3>Deliver output</h3>
            <p>Jobs create reports, artifacts, status history, and notifications.</p>
          </article>
        </div>
      </section>

      <section className="public-section demo-section" id="demo">
        <div className="demo-copy">
          <p className="eyebrow">Demo</p>
          <h2>Product preview in one screen</h2>
          <p>
            The default shell shows the first SaaS as if it already exists: plan, usage,
            reports, jobs, notifications, and product workflow.
          </p>
        </div>
        <div className="demo-window" aria-label="Dashboard preview">
          <div className="demo-window-bar">
            <span />
            <span />
            <span />
          </div>
          <div className="demo-window-grid">
            <div className="demo-sidebar" />
            <div className="demo-main">
              <div className="demo-line wide" />
              <div className="demo-cards">
                <span />
                <span />
                <span />
              </div>
              <div className="demo-table" />
            </div>
          </div>
        </div>
      </section>

      <section className="public-section">
        <div className="section-heading">
          <p className="eyebrow">What you get</p>
          <h2>Built for reusable SaaS launches</h2>
        </div>
        <div className="outcome-list">
          {outcomes.map((outcome) => (
            <div className="outcome-row" key={outcome}>
              <CheckCircle2 aria-hidden="true" size={20} />
              <span>{outcome}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="public-section" id="plans">
        <div className="section-heading">
          <p className="eyebrow">Plans</p>
          <h2>Free-first now, Stripe-ready later</h2>
          {plansQuery.isError ? (
            <p className="section-note">Showing fallback plans until the billing API is available.</p>
          ) : null}
        </div>
        <div className="pricing-grid">
          {plans.map((plan) => (
            <article className="plan-card" key={plan.name}>
              <div>
                <h3>{plan.name}</h3>
                <strong>{plan.price}</strong>
                <p>{plan.description}</p>
              </div>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <Link className="secondary-button" to={plan.name === "Free" ? "/register" : "/terms"}>
                {plan.name === "Free" ? "Register" : "Register for full version"}
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="public-section faq-section" id="faq">
        <div className="section-heading">
          <p className="eyebrow">FAQ</p>
          <h2>Production-ready shape, local-friendly defaults</h2>
        </div>
        <div className="faq-grid">
          <article>
            <h3>Do we need Stripe now?</h3>
            <p>No. The Free flow works first; Stripe can be enabled when paid billing starts.</p>
          </article>
          <article>
            <h3>Can it send real email?</h3>
            <p>Local mode tracks console delivery. Real inbox delivery needs an email provider.</p>
          </article>
          <article>
            <h3>Does the frontend call AI?</h3>
            <p>No. AI decisions and provider calls stay behind backend services.</p>
          </article>
        </div>
      </section>

      <footer className="public-footer">
        <div>
          <strong>SaaS Core Template</strong>
          <span>Reusable SaaS foundation</span>
        </div>
        <div>
          <a href="mailto:contact@example.com">contact@example.com</a>
          <Link to="/terms">Terms, privacy, and liability</Link>
        </div>
      </footer>
    </main>
  );
}
