import type { TokenUsageSnapshotDTO } from "../types";

export type DateRangePreset = "today" | "yesterday" | "week" | "custom";

export function buildDateRange(preset: DateRangePreset, customFrom: string, customTo: string): { from_date: string; to_date: string } {
  const today = new Date();
  const isoDate = (d: Date) => d.toISOString().slice(0, 10);

  switch (preset) {
    case "today": {
      const d = isoDate(today);
      return { from_date: d, to_date: d };
    }
    case "yesterday": {
      const y = new Date(today);
      y.setDate(y.getDate() - 1);
      const d = isoDate(y);
      return { from_date: d, to_date: d };
    }
    case "week": {
      const from = new Date(today);
      from.setDate(from.getDate() - 6);
      return { from_date: isoDate(from), to_date: isoDate(today) };
    }
    case "custom":
    default:
      return {
        from_date: customFrom || isoDate(today),
        to_date: customTo || isoDate(today),
      };
  }
}

export function TokenUsageChart({ snapshots }: { snapshots: TokenUsageSnapshotDTO[] }) {
  if (snapshots.length === 0) {
    return (
      <div style={{ color: "#94a3b8", padding: "2rem", textAlign: "center", border: "1px dashed #334155", borderRadius: "0.5rem" }}>
        Нет данных за выбранный период
      </div>
    );
  }

  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const width = 640;
  const height = 260;
  const chartW = width - margin.left - margin.right;
  const chartH = height - margin.top - margin.bottom;

  const maxValue = Math.max(...snapshots.map((s) => Math.max(s.input_tokens, s.output_tokens, s.total_tokens)), 1);

  const xScale = (i: number) => (chartW / (snapshots.length - 1 || 1)) * i;
  const yScale = (v: number) => chartH - (v / maxValue) * chartH;

  const linePath = (key: keyof TokenUsageSnapshotDTO) =>
    snapshots
      .map((s, i) => {
        const v = s[key] as number;
        const x = margin.left + xScale(i);
        const y = margin.top + yScale(v);
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
    const y = margin.top + chartH - ratio * chartH;
    const val = Math.round(maxValue * ratio);
    return { y, val, key: i };
  });

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="admin-svg-chart" style={{ width: "100%", height: "auto" }}>
      {gridLines.map((g) => (
        <g key={g.key}>
          <line x1={margin.left} y1={g.y} x2={width - margin.right} y2={g.y} stroke="#334155" strokeWidth={1} strokeDasharray="4 4" />
          <text x={margin.left - 8} y={g.y + 4} fill="#94a3b8" fontSize="10" textAnchor="end">
            {g.val > 999 ? `${(g.val / 1000).toFixed(1)}K` : g.val}
          </text>
        </g>
      ))}

      {snapshots.map((s, i) => {
        const x = margin.left + xScale(i);
        const y = margin.top + chartH;
        return (
          <text key={s.snapshot_date} x={x} y={y + 18} fill="#94a3b8" fontSize="10" textAnchor="middle" transform={`rotate(-35 ${x} ${y + 18})`}>
            {s.snapshot_date.slice(5)}
          </text>
        );
      })}

      <path d={linePath("total_tokens")} fill="none" stroke="#f59e0b" strokeWidth={2} strokeLinecap="round" />
      <path d={linePath("input_tokens")} fill="none" stroke="#3b82f6" strokeWidth={2} strokeLinecap="round" />
      <path d={linePath("output_tokens")} fill="none" stroke="#10b981" strokeWidth={2} strokeLinecap="round" />

      {snapshots.map((s, i) => {
        const x = margin.left + xScale(i);
        const makeDot = (val: number, color: string) => {
          const y = margin.top + yScale(val);
          return <circle key={color} cx={x} cy={y} r={3} fill={color} stroke="#0f172a" strokeWidth={1} />;
        };
        return (
          <g key={s.snapshot_date}>
            {makeDot(s.total_tokens, "#f59e0b")}
            {makeDot(s.input_tokens, "#3b82f6")}
            {makeDot(s.output_tokens, "#10b981")}
          </g>
        );
      })}

      <text x={width / 2} y={height - 4} fill="#64748b" fontSize="10" textAnchor="middle">
        Дата
      </text>
      <text x={12} y={height / 2} fill="#64748b" fontSize="10" textAnchor="middle" transform={`rotate(-90 12 ${height / 2})`}>
        Токены
      </text>
    </svg>
  );
}

export function TokenUsageLegend() {
  const items = [
    { label: "Всего", color: "#f59e0b" },
    { label: "Input", color: "#3b82f6" },
    { label: "Output", color: "#10b981" },
  ];
  return (
    <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
      {items.map((item) => (
        <div key={item.label} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem", color: "#cbd5e1" }}>
          <span style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: item.color, display: "inline-block" }} />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
