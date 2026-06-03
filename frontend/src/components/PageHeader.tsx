import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  icon: Icon,
  children,
}: {
  eyebrow: string;
  title: string;
  icon: LucideIcon;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div className="page-title">
        <span className="title-icon">
          <Icon aria-hidden="true" size={20} />
        </span>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
        </div>
      </div>
      {children ? <div className="page-actions">{children}</div> : null}
    </header>
  );
}
