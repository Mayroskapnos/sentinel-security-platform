import {
  ArrowLeft,
  Clock3,
  FileSearch,
  Network,
  ShieldAlert,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { AlertStatusBadge, SeverityBadge } from "../components/data/Badge";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useAlert, useUpdateAlert } from "../hooks/useCoreData";
import { formatDateTime, humanize } from "../lib/format";
import type { AlertStatus } from "../types/core";

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-[0.14em] text-slate-600">
        {label}
      </dt>
      <dd className="mt-1.5 break-words text-sm text-slate-200">{value}</dd>
    </div>
  );
}

export function AlertDetailPage() {
  const { alertId } = useParams();
  const alert = useAlert(alertId);
  const update = useUpdateAlert();

  if (alert.isLoading) return <LoadingState label="Loading alert evidence" />;
  if (alert.isError || !alert.data) return <ErrorState error={alert.error} />;
  const data = alert.data;
  const threshold = asRecord(data.evidence.threshold);
  const observed = data.evidence.observed_count;
  const explanation = data.evidence.explanation;
  const observedWindow = Math.max(
    0,
    Math.round(
      (Date.parse(data.last_event_at) - Date.parse(data.first_event_at)) / 1000,
    ),
  );
  const availableStatuses: AlertStatus[] =
    data.status === "new"
      ? ["investigating", "resolved", "false_positive"]
      : data.status === "investigating"
        ? ["resolved", "false_positive"]
        : ["investigating"];

  return (
    <div className="mx-auto max-w-[1500px]">
      <Link
        className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-accent"
        to="/alerts"
      >
        <ArrowLeft className="size-3.5" /> Back to alerts
      </Link>
      <section className="rounded-xl border border-line bg-panel p-6 shadow-panel">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="font-mono text-[11px] tracking-wider text-accent">
              {data.detection_rule.rule_id}
            </p>
            <h1 className="mt-2 text-2xl font-semibold text-white">
              {data.title}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
              {data.description}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <SeverityBadge severity={data.severity} />
              <AlertStatusBadge status={data.status} />
              <span className="rounded-md border border-line px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-300">
                Priority {Math.round(data.risk_score)} / 100
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.asset_id || data.source_ip || data.destination_ip ? (
              <Link
                className="inline-flex items-center gap-2 rounded-md border border-accent/25 bg-accent/[0.06] px-3 py-2 text-xs text-accent hover:bg-accent/10"
                to={`/attack-map?alert=${data.id}`}
              >
                <Network className="size-3.5" /> Show topology context
              </Link>
            ) : null}
            {availableStatuses.map((status) => (
              <button
                className="rounded-md border border-line bg-white/[0.025] px-3 py-2 text-xs text-slate-300 hover:border-accent/30 hover:text-accent disabled:opacity-50"
                disabled={update.isPending}
                key={status}
                onClick={() => update.mutate({ alertId: data.id, status })}
                type="button"
              >
                Mark {humanize(status)}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-4 text-accent" />
            <h2 className="text-sm font-semibold">Detection explanation</h2>
          </div>
          <p className="mt-4 rounded-lg border border-accent/15 bg-accent/[0.05] p-4 text-sm leading-6 text-slate-200">
            {typeof explanation === "string"
              ? explanation
              : "This event matched the configured rule criteria."}
          </p>
          <dl className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <Detail
              label="Observed"
              value={`${typeof observed === "number" ? observed : data.evidence_count} qualifying events`}
            />
            <Detail
              label="Observed window"
              value={`${observedWindow} seconds`}
            />
            <Detail
              label="Rule threshold"
              value={
                typeof threshold.count === "number"
                  ? `${threshold.count} / ${String(threshold.timeframe_seconds)} seconds`
                  : "Single event / sequence"
              }
            />
            <Detail
              label="Source IP"
              value={data.source_ip ?? "Not available"}
            />
            <Detail
              label="Destination IP"
              value={data.destination_ip ?? "Not available"}
            />
            <Detail label="Username" value={data.username ?? "Not available"} />
          </dl>
        </section>
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold">Alert context</h2>
          <dl className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-1">
            <Detail label="Timestamp" value={formatDateTime(data.timestamp)} />
            <Detail
              label="Affected asset"
              value={data.asset?.hostname ?? "Unresolved"}
            />
            <Detail
              label="Rule"
              value={`${data.detection_rule.rule_id} · ${data.detection_rule.name}`}
            />
            <Detail
              label="MITRE tactic"
              value={data.mitre_tactic ?? "Not mapped"}
            />
            <Detail
              label="MITRE technique"
              value={
                data.mitre_technique_id
                  ? `${data.mitre_technique_id} · ${data.mitre_technique_name}`
                  : "Not mapped"
              }
            />
          </dl>
        </section>
      </div>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex items-center gap-2 border-b border-line p-5">
          <FileSearch className="size-4 text-accent" />
          <div>
            <h2 className="text-sm font-semibold">Evidence</h2>
            <p className="mt-1 text-xs text-muted">
              {data.evidence_count} immutable SecurityEvent references
              contributed to this alert.
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1000px] text-left">
            <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Event</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Destination</th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/70">
              {data.evidence_events.map((event) => (
                <tr key={event.id}>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
                    <Clock3 className="mr-1.5 inline size-3" />
                    {formatDateTime(event.timestamp)}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      className="text-xs text-slate-200 hover:text-accent"
                      to={`/events?event=${event.id}`}
                    >
                      {humanize(event.event_type)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                    {event.source_ip ?? "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                    {event.destination_ip ?? "—"}
                    {event.destination_port ? `:${event.destination_port}` : ""}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {event.username ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    {humanize(event.action)}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {humanize(event.status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
