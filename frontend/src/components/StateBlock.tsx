import { AlertTriangle, CheckCircle2, Inbox } from "lucide-react";

export function EmptyState({ title }: { title: string }) {
  return (
    <div className="state-block">
      <Inbox aria-hidden="true" size={18} />
      <span>{title}</span>
    </div>
  );
}

export function ErrorState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="state-block error">
      <AlertTriangle aria-hidden="true" size={18} />
      <div>
        <strong>{title}</strong>
        {detail ? <span>{detail}</span> : null}
      </div>
    </div>
  );
}

export function SuccessState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="state-block success">
      <CheckCircle2 aria-hidden="true" size={18} />
      <div>
        <strong>{title}</strong>
        {detail ? <span>{detail}</span> : null}
      </div>
    </div>
  );
}

export function LoadingState({ title = "Loading" }: { title?: string }) {
  return <div className="state-block loading">{title}</div>;
}
