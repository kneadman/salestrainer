import type { ReactNode } from "react";

type BadgeProps = {
  tone?: "good" | "warning" | "danger" | "neutral";
  children: ReactNode;
};

type StateProps = {
  title: string;
  detail?: string;
};

type StatCardProps = {
  label: string;
  value: ReactNode;
  detail?: string;
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  /** Render a compact status badge with a semantic tone. */
  return <span className={`admin-badge admin-badge--${tone}`}>{children}</span>;
}

export function LoadingState({ title, detail }: StateProps) {
  /** Render a consistent loading placeholder for admin pages. */
  return (
    <div className="admin-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function ErrorState({ title, detail }: StateProps) {
  /** Render a consistent error placeholder for admin pages. */
  return (
    <div className="admin-state admin-state--error">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function EmptyState({ title, detail }: StateProps) {
  /** Render a consistent empty placeholder for admin pages. */
  return (
    <div className="admin-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function StatCard({ label, value, detail }: StatCardProps) {
  /** Render a dashboard metric card. */
  return (
    <section className="admin-stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </section>
  );
}
