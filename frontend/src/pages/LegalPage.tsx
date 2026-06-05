import { ArrowLeft, FileWarning, Scale, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

const legalSections = [
  {
    title: "Terms of Use",
    icon: Scale,
    body:
      "The template provides software workflows for data processing, reports, notifications, and AI-assisted summaries. Each product must publish product-specific commercial terms before production launch.",
  },
  {
    title: "Privacy and Data Handling",
    icon: ShieldCheck,
    body:
      "Customer data should be stored only when necessary, scoped by organization, protected by role permissions, and covered by export/anonymization workflows.",
  },
  {
    title: "AI Disclaimer and Liability",
    icon: FileWarning,
    body:
      "AI-generated output is assistive and must be validated for high-risk use cases. Product-specific disclaimers should define limitations, human review needs, and liability boundaries.",
  },
];

export function LegalPage() {
  return (
    <main className="public-shell legal-page">
      <header className="public-nav">
        <Link className="brand-row" to="/">
          <div className="brand-mark">SC</div>
          <div>
            <strong>SaaS Core</strong>
            <span>Template</span>
          </div>
        </Link>
        <div className="nav-actions">
          <Link className="secondary-button" to="/">
            <ArrowLeft aria-hidden="true" size={18} />
            Home
          </Link>
        </div>
      </header>

      <section className="legal-hero">
        <p className="eyebrow">Legal foundation</p>
        <h1>Terms, privacy, disclaimer, and liability</h1>
        <p>
          The template keeps legal surfaces visible from the public site and dashboard.
          Product-specific legal text should be reviewed before production launch.
        </p>
      </section>

      <section className="legal-grid" aria-label="Legal sections">
        {legalSections.map((section) => {
          const Icon = section.icon;
          return (
            <article className="tool-panel" key={section.title}>
              <div className="panel-heading">
                <h2>{section.title}</h2>
                <Icon aria-hidden="true" size={20} />
              </div>
              <p>{section.body}</p>
            </article>
          );
        })}
      </section>
    </main>
  );
}
