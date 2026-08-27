import {
  Activity,
  BellRing,
  Boxes,
  Clock3,
  Radio,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
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

import { IncidentStatusBadge, SeverityBadge } from "../components/data/Badge";
import { MetricCard } from "../components/data/MetricCard";
import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import {
  useAssets,
  useDashboardActivity,
  useDashboardSummary,
  useIncidents,
} from "../hooks/useCoreData";
import { activityRangeLabel, activityRanges } from "../lib/dashboard";
import { formatDateTime, formatShortTime, humanize } from "../lib/format";

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
  const [hours, setHours] = useState<number>(72);
  const summary = useDashboardSummary();
  const activity = useDashboardActivity(hours);
  const recentIncidents = useIncidents({ page: 1, page_size: 5 });
  const highestRiskAssets = useAssets({ page: 1, page_size: 1 });

  if (
    summary.isLoading ||
    activity.isLoading ||
    recentIncidents.isLoading ||
    highestRiskAssets.isLoading
  ) {
    return <LoadingState label="Loading security operations data" />;
  }
  if (
    summary.isError ||
    activity.isError ||
    recentIncidents.isError ||
    highestRiskAssets.isError ||
    !summary.data ||
    !activity.data ||
    !recentIncidents.data ||
    !highestRiskAssets.data
  ) {
    return (
      <ErrorState
        error={
          summary.error ??
          activity.error ??
          recentIncidents.error ??
          highestRiskAssets.error
        }
      />
    );
  }

  const timeline = activity.data.events_over_time.map((bucket) => ({
    ...bucket,
    label: formatShortTime(bucket.timestamp),
  }));
  const highestRiskAsset = highestRiskAssets.data.items[0];
  const rangeLabel = activityRangeLabel(hours);

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeading
        actions={
          <div
            aria-label="Dashboard activity range"
            className="flex flex-wrap items-center gap-1 rounded-lg border border-line bg-panel p-1"
          >
            {activityRanges.map((range) => (
              <button
                aria-pressed={range === hours}
                className={`rounded-md px-2.5 py-1.5 font-mono text-[10px] transition-colors ${
                  range === hours
                    ? "bg-accent/15 text-accent"
                    : "text-muted hover:text-slate-200"
                }`}
                key={range}
                onClick={() => setHours(range)}
                type="button"
              >
                {range === 168 ? "7d" : `${range}h`}
              </button>
            ))}
          </div>
        }
        description="Database-backed asset posture and normalized security activity across the SENTINEL environment."
        eyebrow="Operational intelligence"
        title="Security Operations Overview"
      />

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          detail="Open or under investigation"
          icon={ShieldCheck}
          label="Open incidents"
          value={summary.data.open_incidents}
        />
        <MetricCard
          detail="Critical correlated activity"
          icon={ShieldAlert}
          label="Critical incidents"
          value={summary.data.critical_incidents}
        />
        <MetricCard
          detail="New or under investigation"
          icon={BellRing}
          label="Open alerts"
          value={summary.data.open_alerts}
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
        <MetricCard
          detail={highestRiskAsset?.hostname ?? "No registered assets"}
          icon={Boxes}
          label="Highest asset risk"
          value={highestRiskAsset?.risk_score ?? 0}
        />
      </section>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Recent incidents
            </h2>
            <p className="mt-1 text-xs text-muted">
              Highest-priority investigations ordered by recent activity
            </p>
          </div>
          <Link
            className="text-xs text-accent hover:text-emerald-300"
            to="/incidents"
          >
            Open incident queue
          </Link>
        </div>
        {recentIncidents.data.items.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left">
              <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Incident</th>
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Assets</th>
                  <th className="px-4 py-3 font-medium">Alerts</th>
                  <th className="px-4 py-3 font-medium">Last activity</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {recentIncidents.data.items.map((incident) => (
                  <tr className="hover:bg-white/[0.025]" key={incident.id}>
                    <td className="px-4 py-3">
                      <Link
                        className="text-xs text-slate-200 hover:text-accent"
                        to={`/incidents/${incident.id}`}
                      >
                        {incident.incident_number}
                      </Link>
                      <p className="mt-1 max-w-sm truncate text-[10px] text-muted">
                        {incident.title}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={incident.severity} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-300">
                      {incident.confidence_score} / 100
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {incident.asset_count}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {incident.alert_count}
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-muted">
                      {formatDateTime(incident.last_activity_at)}
                    </td>
                    <td className="px-4 py-3">
                      <IncidentStatusBadge status={incident.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-300">
              No incidents have been correlated yet.
            </p>
            <Link
              className="mt-2 inline-block text-xs text-accent hover:text-emerald-300"
              to="/simulator"
            >
              Run a controlled lab scenario
            </Link>
          </div>
        )}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.65fr_1fr]">
        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-slate-100">
              Security events over time
            </h2>
            <p className="mt-1 text-xs text-muted">
              Hourly normalized event volume · {rangeLabel}
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
            Distribution in the selected {rangeLabel}
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
            Event-producing assets in the {rangeLabel}
          </p>
          <div className="mt-5 space-y-3">
            {activity.data.most_active_assets.length ? (
              activity.data.most_active_assets.map((asset, index) => (
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
              ))
            ) : (
              <p className="rounded-lg border border-dashed border-line p-5 text-center text-xs text-muted">
                No event-producing assets in this range.
              </p>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
