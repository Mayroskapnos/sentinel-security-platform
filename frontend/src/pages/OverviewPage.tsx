import {
  Activity,
  BellRing,
  Boxes,
  Clock3,
  Flame,
  Radio,
  ShieldAlert,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { MetricCard } from "../components/data/MetricCard";
import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import {
  useDashboardActivity,
  useDashboardSummary,
} from "../hooks/useCoreData";
import { formatShortTime, humanize } from "../lib/format";

const tooltipStyle = {
  backgroundColor: "#0b111a",
  border: "1px solid #202c3c",
  borderRadius: "8px",
  color: "#cbd5e1",
  fontSize: "12px",
};

const severityColors: Record<string, string> = {
  informational: "#64748b",
  low: "#38bdf8",
  medium: "#fbbf24",
  high: "#fb923c",
  critical: "#f87171",
};

export function OverviewPage() {
  const summary = useDashboardSummary();
  const activity = useDashboardActivity(72);

  if (summary.isLoading || activity.isLoading) {
    return <LoadingState label="Loading security operations data" />;
  }
  if (summary.isError || activity.isError || !summary.data || !activity.data) {
    return <ErrorState error={summary.error ?? activity.error} />;
  }

  const timeline = activity.data.events_over_time.map((bucket) => ({
    ...bucket,
    label: formatShortTime(bucket.timestamp),
  }));

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeading
        actions={
          <div className="flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5 text-xs text-slate-300">
            <Radio className="size-3.5 text-accent" />
            PostgreSQL-backed
          </div>
        }
        description="Database-backed asset posture and normalized security activity across the SENTINEL environment."
        eyebrow="Operational intelligence"
        title="Security Operations Overview"
      />

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          detail="New or under investigation"
          icon={BellRing}
          label="Open alerts"
          value={summary.data.open_alerts}
        />
        <MetricCard
          detail="Open critical-priority detections"
          icon={ShieldAlert}
          label="Critical alerts"
          value={summary.data.critical_alerts}
        />
        <MetricCard
          detail="Open high-priority detections"
          icon={Flame}
          label="High alerts"
          value={summary.data.high_alerts}
        />
        <MetricCard
          detail="Registered lab inventory"
          icon={Boxes}
          label="Total assets"
          value={summary.data.total_assets}
        />
        <MetricCard
          detail="Currently reporting online"
          icon={Radio}
          label="Online assets"
          value={summary.data.online_assets}
        />
        <MetricCard
          detail="Experimental risk score ≥ 61"
          icon={ShieldAlert}
          label="High-risk assets"
          value={summary.data.high_risk_assets}
        />
        <MetricCard
          detail="Since 00:00 UTC"
          icon={Activity}
          label="Events today"
          value={summary.data.events_today}
        />
        <MetricCard
          detail="Most recent 60 minutes"
          icon={Clock3}
          label="Events last hour"
          value={summary.data.events_last_hour}
        />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.65fr_1fr]">
        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-slate-100">
              Security events over time
            </h2>
            <p className="mt-1 text-xs text-muted">
              Hourly normalized event volume · last 72 hours
            </p>
          </div>
          <div className="h-72">
            <ResponsiveContainer height="100%" width="100%">
              <AreaChart
                data={timeline}
                margin={{ left: -20, right: 8, top: 8 }}
              >
                <defs>
                  <linearGradient id="eventFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#39c6a3" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#39c6a3" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="#202c3c"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  interval="preserveStartEnd"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Area
                  dataKey="count"
                  fill="url(#eventFill)"
                  stroke="#39c6a3"
                  strokeWidth={2}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold text-slate-100">
            Events by severity
          </h2>
          <p className="mt-1 text-xs text-muted">
            Distribution in the selected 72-hour window
          </p>
          <div className="mt-5 h-72">
            <ResponsiveContainer height="100%" width="100%">
              <BarChart
                data={activity.data.events_by_severity}
                layout="vertical"
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="#202c3c"
                  strokeDasharray="3 3"
                />
                <XAxis
                  allowDecimals={false}
                  axisLine={false}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  type="number"
                />
                <YAxis
                  axisLine={false}
                  dataKey="name"
                  tick={{ fill: "#94a3b8", fontSize: 10 }}
                  tickFormatter={humanize}
                  tickLine={false}
                  type="category"
                  width={86}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {activity.data.events_by_severity.map((entry) => (
                    <Cell
                      fill={severityColors[entry.name] ?? "#64748b"}
                      key={entry.name}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold text-slate-100">
            Events by type
          </h2>
          <p className="mt-1 text-xs text-muted">
            Most frequent normalized activity categories
          </p>
          <div className="mt-5 h-64">
            <ResponsiveContainer height="100%" width="100%">
              <BarChart
                data={activity.data.events_by_type}
                margin={{ bottom: 45 }}
              >
                <CartesianGrid
                  stroke="#202c3c"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  angle={-28}
                  axisLine={false}
                  dataKey="name"
                  height={72}
                  textAnchor="end"
                  tick={{ fill: "#94a3b8", fontSize: 10 }}
                  tickFormatter={humanize}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="#39c6a3" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold text-slate-100">
            Most active assets
          </h2>
          <p className="mt-1 text-xs text-muted">
            Event-producing assets in the last 72 hours
          </p>
          <div className="mt-5 space-y-3">
            {activity.data.most_active_assets.map((asset, index) => (
              <div
                className="flex items-center gap-3 rounded-lg border border-line/80 bg-[#0b111a] p-3"
                key={`${asset.asset_id}-${asset.hostname}`}
              >
                <span className="grid size-7 shrink-0 place-items-center rounded-md bg-white/[0.04] font-mono text-[10px] text-muted">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0 flex-1">
                  {asset.asset_id ? (
                    <Link
                      className="truncate text-xs font-medium text-slate-200 hover:text-accent"
                      to={`/assets/${asset.asset_id}`}
                    >
                      {asset.hostname}
                    </Link>
                  ) : (
                    <p className="truncate text-xs text-slate-300">
                      {asset.hostname}
                    </p>
                  )}
                  <p className="mt-1 text-[10px] uppercase tracking-wider text-slate-600">
                    Normalized telemetry
                  </p>
                </div>
                <span className="font-mono text-sm font-semibold text-accent">
                  {asset.count}
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
