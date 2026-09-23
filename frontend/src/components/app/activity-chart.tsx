import type { ActivityPoint } from "@/lib/types";

/** 24 hourly bars of messages, join ticks underneath, and event markers on top. Plain SVG. */
export function ActivityChart({ points }: { points: ActivityPoint[] }) {
  const width = 720;
  const height = 180;
  const barArea = 130;
  const maxMessages = Math.max(1, ...points.map((p) => p.messages));
  const maxJoins = Math.max(1, ...points.map((p) => p.joins));
  const step = width / Math.max(points.length, 1);
  const totals = points.reduce((acc, p) => ({ messages: acc.messages + p.messages, joins: acc.joins + p.joins, events: acc.events + p.events }), { messages: 0, joins: 0, events: 0 });

  return (
    <figure>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-44 w-full" role="img" aria-label={`Last 24 hours: ${totals.messages} messages, ${totals.joins} joins, ${totals.events} security events`}>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1="0" x2={width} y1={barArea * (1 - f) + 12} y2={barArea * (1 - f) + 12} stroke="var(--border)" strokeDasharray="2 4" />
        ))}
        {points.map((p, i) => {
          const h = (p.messages / maxMessages) * (barArea - 8);
          const x = i * step + step * 0.18;
          const w = step * 0.64;
          const jh = p.joins ? Math.max((p.joins / maxJoins) * 14, 2) : 0;
          return (
            <g key={p.hour}>
              <title>{`${new Date(p.hour).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} — ${p.messages} messages, ${p.joins} joins, ${p.events} events`}</title>
              <rect x={x} y={barArea + 12 - h} width={w} height={Math.max(h, 1)} rx="1.5" fill="var(--chart-2)" opacity={0.55} />
              <rect x={x} y={height - 6 - jh} width={w} height={jh} rx="1" fill="var(--signal)" opacity={0.8} />
              {p.events ? <circle cx={x + w / 2} cy={Math.max(barArea + 12 - h - 7, 7)} r={Math.min(2.5 + p.events * 0.6, 6)} fill="var(--sev-high)" /> : null}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 font-mono text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-chart-2/60" />Messages · {totals.messages.toLocaleString("en")}</span>
        <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-signal" />Joins · {totals.joins}</span>
        <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-sev-high" />Security events · {totals.events}</span>
        <span className="ml-auto">24 h · hourly</span>
      </figcaption>
    </figure>
  );
}
