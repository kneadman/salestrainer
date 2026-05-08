import type { ReactNode } from "react";

export function ClientBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "good" | "warning" | "danger" | "neutral" }) {
  /** Render a compact client cabinet badge. */
  return <span className={`client-badge client-badge--${tone}`}>{children}</span>;
}

export function ClientState({ title, detail, tone = "neutral" }: { title: string; detail?: string; tone?: "neutral" | "error" }) {
  /** Render loading, empty, or error states with one consistent surface. */
  return (
    <div className={`client-state client-state--${tone}`}>
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function ClientStat({ label, value, detail }: { label: string; value: ReactNode; detail?: string }) {
  /** Render a client dashboard analytics card. */
  return (
    <section className="client-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </section>
  );
}

export function SimpleBars({ values, labelFormatter }: { values: Record<string, number>; labelFormatter?: (key: string) => string }) {
  /** Render tiny CSS bars without adding a chart dependency. */
  const max = Math.max(1, ...Object.values(values));
  return (
    <div className="client-bars">
      {Object.entries(values).map(([key, value]) => (
        <div key={key} className="client-bars__row">
          <span>{labelFormatter ? labelFormatter(key) : key}</span>
          <div><i style={{ width: `${Math.max(6, (value / max) * 100)}%` }} /></div>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}
