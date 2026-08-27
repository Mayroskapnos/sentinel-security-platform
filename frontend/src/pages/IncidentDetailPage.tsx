import {
  ArrowDown,
  ArrowLeft,
  Boxes,
  Clock3,
  ExternalLink,
  Network,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import {
  AlertStatusBadge,
  IncidentStatusBadge,
  SeverityBadge,
} from "../components/data/Badge";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { InvestigationAssistant } from "../components/investigation/InvestigationAssistant";
import { IncidentReportActions } from "../components/reports/IncidentReportActions";
import { useIncident, useUpdateIncident } from "../hooks/useCoreData";
import { formatDateTime, humanize } from "../lib/format";
import { incidentConfidenceLabel } from "../lib/incidents";
import type { IncidentStatus, IncidentStoryItem } from "../types/core";

const transitions: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["investigating", "resolved", "false_positive"],
  investigating: ["contained", "resolved", "false_positive"],
  contained: ["investigating", "resolved"],
  resolved: ["investigating"],
  false_positive: ["investigating"],
};

export function IncidentStory({ items }: { items: IncidentStoryItem[] }) {
  return (
    <div className="mt-5 space-y-2">
      {items.map((item, index) => (
        <div key={`${item.alert_id}-${item.stage}`}>
          <article className="rounded-lg border border-line/80 bg-[#0b111a] p-4">
            <div className="flex gap-3">
              <span className="grid size-7 shrink-0 place-items-center rounded-full border border-accent/30 bg-accent/10 font-mono text-[10px] text-accent">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-100">
                    {item.title}
                  </p>
                  <span className="font-mono text-[10px] text-muted">
                    {formatDateTime(item.timestamp)}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">
                  {item.description}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-[10px]">
                  <Link
                    className="text-accent hover:text-emerald-300"
                    to={`/alerts/${item.alert_id}`}
                  >
                    {item.rule_id}{" "}
                    <ExternalLink className="ml-1 inline size-3" />
                  </Link>
                  {item.asset_ids.map((assetId) => (
                    <Link
                      className="text-slate-400 hover:text-accent"
                      key={assetId}
                      to={`/assets/${assetId}`}
                    >
                      Asset {assetId.slice(0, 8)}
                    </Link>
                  ))}
                  {item.event_ids.slice(0, 3).map((eventId) => (
                    <Link
                      className="text-slate-500 hover:text-accent"
                      key={eventId}
                      to={`/events?event=${eventId}`}
                    >
                      Evidence {eventId.slice(0, 8)}
                    </Link>
                  ))}
                </div>
                <p className="mt-3 text-[10px] text-slate-500">
                  {item.mitre_technique_id
                    ? `${item.mitre_technique_id} · ${item.mitre_technique_name}`
                    : "No precise ATT&CK mapping asserted"}
                </p>
              </div>
            </div>
          </article>
          {index < items.length - 1 ? (
            <ArrowDown className="mx-auto my-2 size-4 text-slate-600" />
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const query = useIncident(incidentId);
  const update = useUpdateIncident();
  if (query.isLoading) return <LoadingState label="Reconstructing incident" />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  const incident = query.data;

  return (
    <div className="mx-auto max-w-[1500px]">
      <Link
        className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-accent"
        to="/incidents"
      >
        <ArrowLeft className="size-3.5" /> Back to incident queue
      </Link>

      <section className="rounded-xl border border-line bg-panel p-6 shadow-panel">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="font-mono text-xs text-accent">
              {incident.incident_number}
            </p>
            <h1 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">
              {incident.title}
            </h1>
            <p className="mt-3 max-w-4xl text-sm leading-6 text-muted">
              {incident.summary}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <SeverityBadge severity={incident.severity} />
              <IncidentStatusBadge status={incident.status} />
              <span className="rounded-md border border-accent/25 bg-accent/[0.06] px-2 py-1 font-mono text-[10px] text-accent">
                Correlation confidence {incident.confidence_score} / 100 ·{" "}
                {incidentConfidenceLabel(incident.confidence_score)}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              className="inline-flex items-center gap-2 rounded-md border border-accent/25 bg-accent/[0.06] px-3 py-2 text-xs text-accent hover:bg-accent/10"
              to={`/attack-map?incident=${incident.id}`}
            >
              <Network className="size-3.5" /> View Incident on Attack Map
            </Link>
            {transitions[incident.status].map((status) => (
              <button
                className="rounded-md border border-line bg-white/[0.025] px-3 py-2 text-xs text-slate-300 hover:text-white disabled:opacity-50"
                disabled={update.isPending}
                key={status}
                onClick={() =>
                  update.mutate({ incidentId: incident.id, status })
                }
                type="button"
              >
                Mark {humanize(status)}
              </button>
            ))}
            <div className="basis-full lg:max-w-md">
              <IncidentReportActions incidentId={incident.id} />
            </div>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Affected assets", incident.asset_count],
            ["Alerts", incident.alert_count],
            ["Security events", incident.event_count],
            ["ATT&CK techniques", incident.observed_techniques.length],
            ["Risk score", `${incident.risk_score} / 100`],
          ].map(([label, value]) => (
            <div
              className="rounded-lg border border-line bg-[#0b111a] p-4"
              key={label}
            >
              <p className="text-[10px] uppercase tracking-wider text-muted">
                {label}
              </p>
              <p className="mt-2 text-lg font-semibold text-slate-100">
                {value}
              </p>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">
            SENTINEL Deterministic Analysis
          </p>
          <h2 className="text-sm font-semibold text-slate-100">Attack Story</h2>
          <p className="mt-2 text-xs leading-5 text-muted">
            Chronological stages reconstructed only from alerts and their
            persisted evidence.
          </p>
          <IncidentStory items={incident.story} />
        </section>

        <div className="space-y-6">
          <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
            <h2 className="text-sm font-semibold text-slate-100">
              Correlation Evidence
            </h2>
            <p className="mt-2 text-[10px] text-muted">
              Experimental deterministic score, not a probability.
            </p>
            <div className="mt-4 space-y-2">
              {incident.correlation_signals.length ? (
                incident.correlation_signals.map((signal, index) => (
                  <div
                    className="rounded-lg border border-line/70 bg-[#0b111a] p-3"
                    key={`${signal.type}-${index}`}
                  >
                    <div className="flex justify-between gap-3">
                      <p className="text-xs text-slate-300">
                        {signal.description}
                      </p>
                      <span className="font-mono text-[10px] text-accent">
                        +{signal.weight}
                      </span>
                    </div>
                    <p className="mt-1 text-[9px] uppercase tracking-wider text-slate-600">
                      {signal.strength}
                    </p>
                  </div>
                ))
              ) : (
                <p className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
                  The first alert established this incident; no cross-alert
                  signals exist yet.
                </p>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
            <h2 className="text-sm font-semibold text-slate-100">
              Observed ATT&amp;CK
            </h2>
            <div className="mt-4 space-y-2">
              {incident.observed_techniques.length ? (
                incident.observed_techniques.map((technique) => (
                  <div
                    className="rounded-lg border border-line/70 bg-[#0b111a] p-3"
                    key={technique.technique_id}
                  >
                    <span className="font-mono text-[10px] text-accent">
                      {technique.technique_id}
                    </span>
                    <p className="mt-1 text-xs text-slate-300">
                      {technique.technique_name}
                    </p>
                    <p className="mt-1 text-[9px] uppercase text-slate-600">
                      {technique.tactic}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted">
                  No justified mappings on observed alerts.
                </p>
              )}
            </div>
          </section>
        </div>
      </div>

      <section className="mt-6 rounded-xl border border-line bg-panel p-5 shadow-panel">
        <div className="flex items-center gap-2">
          <Boxes className="size-4 text-accent" />
          <h2 className="text-sm font-semibold text-slate-100">
            Affected Assets
          </h2>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {incident.assets.map((asset) => (
            <Link
              className="rounded-lg border border-line/70 bg-[#0b111a] p-4 hover:border-accent/30"
              key={asset.id}
              to={`/assets/${asset.id}`}
            >
              <p className="text-xs font-medium text-slate-200">
                {asset.hostname}
              </p>
              <p className="mt-1 font-mono text-[10px] text-muted">
                {asset.ip_address}
              </p>
              <p className="mt-2 text-[9px] uppercase text-slate-600">
                {asset.network_zone} · {asset.criticality}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex items-center gap-2 border-b border-line p-5">
          <Clock3 className="size-4 text-accent" />
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Incident Timeline &amp; Alerts
            </h2>
            <p className="mt-1 text-xs text-muted">
              Each alert links to its immutable event evidence.
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[950px] text-left">
            <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Alert</th>
                <th className="px-4 py-3">Asset</th>
                <th className="px-4 py-3">Evidence</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/70">
              {incident.alerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="px-4 py-3 font-mono text-[10px] text-muted">
                    {formatDateTime(alert.first_event_at)}
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={alert.severity} />
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      className="text-xs text-slate-200 hover:text-accent"
                      to={`/alerts/${alert.id}`}
                    >
                      {alert.title}
                    </Link>
                    <p className="mt-1 font-mono text-[10px] text-accent">
                      {alert.rule_id}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {alert.asset_hostname ?? "Unresolved"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">
                    {alert.evidence_count}
                  </td>
                  <td className="px-4 py-3">
                    <AlertStatusBadge status={alert.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <InvestigationAssistant incidentId={incident.id} />

      {incident.scenario ? (
        <section className="mt-6 rounded-xl border border-accent/20 bg-accent/[0.04] p-5">
          <p className="text-[10px] uppercase tracking-wider text-accent">
            Correlated ScenarioRun
          </p>
          <Link
            className="mt-2 inline-block text-sm text-slate-100 hover:text-accent"
            to={`/simulator/runs/${incident.scenario.id}`}
          >
            {incident.scenario.scenario_id} · {incident.scenario.scenario_name}
          </Link>
          <p className="mt-2 text-xs text-muted">
            The ScenarioRun records what test was executed; this Incident
            records what SENTINEL inferred from observed evidence.
          </p>
        </section>
      ) : null}
    </div>
  );
}
