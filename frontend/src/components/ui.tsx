import { useState, type ReactNode } from "react";
import type { CoverageStatus, GapStatus, Severity } from "../types";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Card({ title, children, actions, className = "" }: {
  title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint, tone = "default" }: {
  label: string; value: ReactNode; hint?: ReactNode; tone?: "default" | "good" | "warn" | "bad" | "info";
}) {
  return (
    <div className={`stat tone-${tone}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  covered: "good", accepted: "good", completed: "good", accept: "good",
  partial: "warn", revised: "warn", proposed: "info", running: "info",
  gap: "bad", rejected: "bad", reject: "bad", failed: "bad",
  escalated: "esc", withdrawn: "muted",
};

export function Pill({ value, tone }: { value: string; tone?: string }) {
  return <span className={`pill tone-${tone ?? STATUS_TONE[value] ?? "muted"}`}>{value}</span>;
}

export function StatusPill({ status }: { status: GapStatus | CoverageStatus | string }) {
  return <Pill value={status} />;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`sev sev-${severity}`}>{severity}</span>;
}

export function Loading({ label = "Loading..." }: { label?: string }) {
  return <div className="loading" role="status"><span className="spinner" aria-hidden />{label}</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <strong>Something went wrong.</strong>
      <p>{error}</p>
      {onRetry && <button className="btn btn-secondary" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function JsonView({ value, label = "Payload" }: { value: unknown; label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="json-view">
      <button className="link-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "Hide" : "Show"} {label.toLowerCase()}
      </button>
      {open && <pre>{JSON.stringify(value, null, 2)}</pre>}
    </div>
  );
}

export function ModeBadge({ mode }: { mode: string }) {
  return (
    <span className={`mode-badge mode-${mode}`} title={mode === "demo"
      ? "Deterministic demo responder over a synthetic dataset; graph and checks run for real"
      : "Live LLM reasoning"}>
      {mode === "demo" ? "DEMO - deterministic" : "LIVE - LLM"}
    </span>
  );
}
