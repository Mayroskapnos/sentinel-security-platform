import "@xyflow/react/dist/style.css";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Clock3,
  Crosshair,
  Database,
  ExternalLink,
  Radio,
  ShieldAlert,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AttackTopology } from "../components/network/AttackTopology";
import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useLabStatus, useNetworkTopology } from "../hooks/useCoreData";
import { formatDateTime, humanize } from "../lib/format";
import {
  activityFocus,
  initialTopologyView,
  isUuid,
  topologyLiveLabel,
  type TopologyView,
} from "../lib/network";
import { useTelemetry } from "../realtime/TelemetryContext";
import type { TopologyEdge, TopologyNode, TopologyWindow } from "../types/core";

const windows: { label: string; value: TopologyWindow }[] = [
  { label: "5 min", value: "5m" },
  { label: "15 min", value: "15m" },
  { label: "1 hour", value: "1h" },
  { label: "24 hours", value: "24h" },
  { label: "All", value: "all" },
];
const views: { label: string; value: TopologyView }[] = [
  { label: "All assets", value: "all" },
  { label: "Alert context", value: "alerts" },
  { label: "High risk", value: "high-risk" },
  { label: "Scenario activity", value: "scenario" },
  { label: "Incident evidence", value: "incident" },
];

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line/80 bg-[#0b111a] px-4 py-3">
      <p className="text-[9px] uppercase tracking-[0.14em] text-slate-600">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

export function SelectionPanel({
  node,
  edge,
  onClose,
}: {
  node: TopologyNode | null;
  edge: TopologyEdge | null;
  onClose: () => void;
}) {
  const item = node ?? edge;
  if (!item) return null;
  return (
    <aside className="absolute inset-y-3 right-3 z-10 w-[min(360px,calc(100%-1.5rem))] overflow-y-auto rounded-xl border border-line bg-[#0d1520]/[0.97] p-5 shadow-2xl backdrop-blur">
      <button
        aria-label="Close topology details"
        className="absolute right-3 top-3 rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-white"
        onClick={onClose}
        type="button"
      >
        <X className="size-4" />
      </button>
      {node ? (
        <>
          <p className="text-[10px] uppercase tracking-[0.16em] text-accent">
            Asset
          </p>
          <h2 className="mt-2 pr-8 text-lg font-semibold text-white">
            {node.hostname}
          </h2>
          <p className="mt-1 text-xs text-muted">{node.display_name}</p>
          <dl className="mt-5 grid grid-cols-2 gap-3 text-xs">
            {[
              ["IP address", node.ip_address],
              ["Zone", node.network_zone.toUpperCase()],
              ["Type", humanize(node.asset_type)],
              ["Status", humanize(node.status)],
              ["Criticality", humanize(node.criticality)],
              ["Risk", `${Math.round(node.risk_score)} / 100`],
              ["Open alerts", String(node.open_alert_count)],
              ["Recent events", String(node.recent_event_count)],
              ["Connections", String(node.recent_connection_count)],
              ["Last seen", formatDateTime(node.last_seen)],
            ].map(([label, value]) => (
              <div className="rounded-lg border border-line/70 p-3" key={label}>
                <dt className="text-[9px] uppercase tracking-wider text-slate-600">
                  {label}
                </dt>
                <dd className="mt-1 break-words text-slate-300">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-[10px] text-muted">{node.operating_system}</p>
          <Link
            className="mt-5 inline-flex items-center gap-2 text-xs text-accent hover:text-emerald-300"
            to={`/assets/${node.id}`}
          >
            Open asset profile <ExternalLink className="size-3" />
          </Link>
        </>
      ) : edge ? (
        <>
          <p className="text-[10px] uppercase tracking-[0.16em] text-accent">
            Observed relationship
          </p>
          <h2 className="mt-2 pr-8 text-lg font-semibold text-white">
            {humanize(edge.connection_type)}
            {edge.destination_port ? ` · ${edge.destination_port}` : ""}
          </h2>
          <p className="mt-2 font-mono text-[10px] leading-5 text-muted">
            {edge.source_ip} <ArrowRight className="mx-1 inline size-3" />{" "}
            {edge.destination_ip}
          </p>
          <dl className="mt-5 space-y-3 text-xs">
            {[
              ["Protocol", edge.protocol.toUpperCase()],
              ["Last status", humanize(edge.last_status)],
              ["First seen", formatDateTime(edge.first_seen)],
              ["Last seen", formatDateTime(edge.last_seen)],
              ["Lifetime observations", String(edge.connection_count)],
              ["Window observations", String(edge.recent_event_count)],
              ["Associated alerts", String(edge.alert_ids.length)],
              ["Scenario runs", String(edge.scenario_run_ids.length)],
            ].map(([label, value]) => (
              <div
                className="flex items-center justify-between gap-4 border-b border-line/60 pb-2"
                key={label}
              >
                <dt className="text-muted">{label}</dt>
                <dd className="text-right text-slate-200">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-5 flex flex-wrap gap-3 text-xs">
            <Link
              className="text-accent hover:text-emerald-300"
              to={`/events?source_ip=${encodeURIComponent(edge.source_ip)}&destination_ip=${encodeURIComponent(edge.destination_ip)}`}
            >
              View events
            </Link>
            {edge.alert_ids[0] ? (
              <Link
                className="text-accent hover:text-emerald-300"
                to={`/alerts/${edge.alert_ids[0]}`}
              >
                View alert
              </Link>
            ) : null}
          </div>
        </>
      ) : null}
    </aside>
  );
}

export function AttackMapPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedRun = searchParams.get("run");
  const requestedAsset = searchParams.get("asset");
  const requestedAlert = searchParams.get("alert");
  const requestedIncident = searchParams.get("incident");
  const requestedWindow = searchParams.get("window");
  const window = windows.some((item) => item.value === requestedWindow)
    ? (requestedWindow as TopologyWindow)
    : "15m";
  const scenarioRunId = isUuid(requestedRun) ? requestedRun : undefined;
  const assetId = isUuid(requestedAsset) ? requestedAsset : undefined;
  const alertId = isUuid(requestedAlert) ? requestedAlert : undefined;
  const incidentId = isUuid(requestedIncident) ? requestedIncident : undefined;
  const invalidDeepLink = Boolean(
    (requestedRun && !scenarioRunId) ||
    (requestedAsset && !assetId) ||
    (requestedAlert && !alertId) ||
    (requestedIncident && !incidentId),
  );
  const [view, setView] = useState<TopologyView>(
    initialTopologyView(scenarioRunId, incidentId),
  );
  const [hiddenZones, setHiddenZones] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const topology = useNetworkTopology({
    window,
    scenario_run_id: scenarioRunId,
    incident_id: incidentId,
    asset_id: assetId,
    alert_id: alertId,
  });
  const lab = useLabStatus();
  const telemetry = useTelemetry();
  const zones = useMemo(
    () =>
      [
        ...new Set(topology.data?.nodes.map((node) => node.network_zone) ?? []),
      ].sort(),
    [topology.data],
  );
  const visibleZones = useMemo(
    () => new Set(zones.filter((zone) => !hiddenZones.has(zone))),
    [zones, hiddenZones],
  );

  function updateParameter(key: string, value?: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  }

  if (topology.isLoading)
    return <LoadingState label="Building attack topology" />;
  if (topology.isError || !topology.data)
    return <ErrorState error={topology.error} />;
  const data = topology.data;
  const labOffline = lab.data?.status === "offline";
  const deepLinkedEdge = alertId
    ? data.edges.find((edge) => edge.alert_ids.includes(alertId))
    : undefined;
  const selectedEdge =
    data.edges.find((edge) => edge.id === selectedEdgeId) ??
    deepLinkedEdge ??
    null;
  const selectedNode = selectedEdge
    ? null
    : (data.nodes.find((node) => node.id === (selectedNodeId ?? assetId)) ??
      (alertId
        ? data.nodes.find((node) => node.alert_ids.includes(alertId))
        : null) ??
      null);

  return (
    <div className="mx-auto max-w-[1800px]">
      <PageHeading
        actions={
          <div className="flex items-center gap-2 rounded-lg border border-line bg-panel px-3 py-2 text-[10px] uppercase tracking-wider">
            <span
              className={`size-2 rounded-full ${
                telemetry.connectionState === "connected" && !labOffline
                  ? "bg-accent shadow-[0_0_12px_rgba(57,198,163,0.8)]"
                  : "bg-slate-600"
              }`}
            />
            <span className="text-slate-300">
              {topologyLiveLabel(Boolean(labOffline))}
            </span>
          </div>
        }
        description="Observed Corporate Lab assets, communication paths, alert context, and scenario progression. No unobserved path is inferred."
        eyebrow={
          data.incident
            ? "Incident topology"
            : data.scenario
              ? "Scenario topology"
              : "Network intelligence"
        }
        title="Attack Map"
      />

      {invalidDeepLink ? (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-amber-400/20 bg-amber-400/[0.05] p-3 text-xs text-amber-200">
          <AlertTriangle className="size-4" /> Invalid deep-link identifiers
          were ignored safely.
        </div>
      ) : null}

      {data.scenario ? (
        <section className="mt-5 flex flex-col justify-between gap-3 rounded-xl border border-accent/20 bg-accent/[0.04] p-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-accent">
              {data.scenario.scenario_id} · {humanize(data.scenario.status)}
            </p>
            <p className="mt-1 text-sm font-medium text-slate-100">
              {data.scenario.scenario_name}
            </p>
            <p className="mt-1 text-xs text-muted">
              {data.scenario.event_count} events · {data.scenario.alert_count}{" "}
              alerts. Only telemetry explicitly attributed to this persisted run
              is shown.
            </p>
          </div>
          <div className="flex gap-3 text-xs">
            <Link
              className="text-accent hover:text-emerald-300"
              to={`/simulator/runs/${data.scenario.run_id}`}
            >
              Run detail
            </Link>
            <button
              className="text-slate-400 hover:text-white"
              onClick={() => {
                updateParameter("run");
                setView("all");
              }}
              type="button"
            >
              Return to live
            </button>
          </div>
        </section>
      ) : null}

      {data.incident ? (
        <section className="mt-5 flex flex-col justify-between gap-3 rounded-xl border border-accent/20 bg-accent/[0.04] p-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-accent">
              {data.incident.incident_number} · {humanize(data.incident.status)}
            </p>
            <p className="mt-1 text-sm font-medium text-slate-100">
              {data.incident.title}
            </p>
            <p className="mt-1 text-xs text-muted">
              {data.incident.event_count} evidence events ·{" "}
              {data.incident.alert_count} alerts. Only persisted alert evidence
              relationships are shown.
            </p>
          </div>
          <div className="flex gap-3 text-xs">
            <Link
              className="text-accent hover:text-emerald-300"
              to={`/incidents/${data.incident.id}`}
            >
              Incident detail
            </Link>
            <button
              className="text-slate-400 hover:text-white"
              onClick={() => {
                updateParameter("incident");
                setView("all");
              }}
              type="button"
            >
              Return to live
            </button>
          </div>
        </section>
      ) : null}

      <section className="mt-5 rounded-xl border border-line bg-panel p-4 shadow-panel">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted">
            Window
            <select
              className="rounded-md border border-line bg-[#0b111a] px-2.5 py-2 text-xs normal-case tracking-normal text-slate-200 outline-none focus:border-accent/40"
              onChange={(event) =>
                updateParameter("window", event.target.value)
              }
              value={window}
            >
              {windows.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-[#0b111a] p-1">
            {views.map((item) => (
              <button
                className={`rounded-md px-2.5 py-1.5 text-[10px] transition-colors ${
                  view === item.value
                    ? "bg-accent/10 text-accent"
                    : "text-muted hover:text-slate-200"
                }`}
                disabled={
                  (item.value === "scenario" && !data.scenario) ||
                  (item.value === "incident" && !data.incident)
                }
                key={item.value}
                onClick={() => setView(item.value)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            {zones.map((zone) => (
              <label
                className="flex cursor-pointer items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-400"
                key={zone}
              >
                <input
                  checked={!hiddenZones.has(zone)}
                  className="accent-[#39c6a3]"
                  onChange={() =>
                    setHiddenZones((current) => {
                      const next = new Set(current);
                      if (next.has(zone)) next.delete(zone);
                      else next.add(zone);
                      return next;
                    })
                  }
                  type="checkbox"
                />
                {zone}
              </label>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <Metric label="Assets" value={data.summary.asset_count} />
        <Metric label="Relationships" value={data.summary.connection_count} />
        <Metric
          label="Active paths"
          value={data.summary.active_connection_count}
        />
        <Metric label="Open alerts" value={data.summary.open_alert_count} />
        <Metric label="High risk" value={data.summary.high_risk_asset_count} />
        <Metric label="Activities" value={data.summary.activity_count} />
      </section>

      <section className="relative mt-4 overflow-hidden rounded-xl border border-line bg-[#080d14] shadow-panel">
        {!data.edges.length ? (
          <div className="pointer-events-none absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-lg border border-line bg-panel/95 px-4 py-2 text-center text-xs text-muted shadow-lg">
            No observed relationships in this view. Known assets remain
            available by zone.
          </div>
        ) : null}
        <AttackTopology
          focusedAlertId={alertId}
          focusedAssetId={assetId}
          onSelectAsset={(node) => {
            setSelectedNodeId(node.id);
            setSelectedEdgeId(null);
            updateParameter("asset", node.id);
          }}
          onSelectEdge={(edge) => {
            setSelectedEdgeId(edge.id);
            setSelectedNodeId(null);
            updateParameter("asset");
          }}
          topology={data}
          view={view}
          visibleZones={visibleZones}
        />
        <SelectionPanel
          edge={selectedEdge}
          node={selectedNode}
          onClose={() => {
            setSelectedNodeId(null);
            setSelectedEdgeId(null);
            const next = new URLSearchParams(searchParams);
            next.delete("asset");
            next.delete("alert");
            setSearchParams(next, { replace: true });
          }}
        />
      </section>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-accent" />
              <h2 className="text-sm font-semibold text-slate-100">
                Activity timeline
              </h2>
            </div>
            {data.summary.activity_truncated ? (
              <span className="text-[10px] text-amber-300">Bounded result</span>
            ) : null}
          </div>
          {!data.activities.length ? (
            <p className="mt-5 text-xs text-muted">
              No qualifying activity was observed in this scope.
            </p>
          ) : (
            <div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
              {[...data.activities].reverse().map((activity) => (
                <div
                  className="flex items-stretch rounded-lg border border-line/70 bg-[#0b111a] hover:border-accent/25"
                  key={activity.id}
                >
                  <button
                    className="flex min-w-0 flex-1 items-start gap-3 p-3 text-left"
                    onClick={() => {
                      const focus = activityFocus(data, activity);
                      setSelectedEdgeId(focus.edgeId);
                      setSelectedNodeId(focus.nodeId);
                    }}
                    type="button"
                  >
                    <Clock3 className="mt-0.5 size-3.5 shrink-0 text-slate-500" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-slate-200">
                        {humanize(activity.action)}
                      </p>
                      <p className="mt-1 truncate font-mono text-[10px] text-muted">
                        {activity.source_ip ?? "unresolved"} →{" "}
                        {activity.destination_ip ?? "local asset"}
                        {activity.destination_port
                          ? `:${activity.destination_port}`
                          : ""}
                      </p>
                    </div>
                    <span className="text-[9px] text-slate-600">
                      {formatDateTime(activity.timestamp)}
                    </span>
                  </button>
                  <Link
                    aria-label="Open source event"
                    className="grid w-9 place-items-center border-l border-line/60 text-slate-600 hover:text-accent"
                    to={`/events?event=${activity.id}`}
                  >
                    <ExternalLink className="size-3" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-4 text-accent" />
            <h2 className="text-sm font-semibold text-slate-100">
              Observed ATT&amp;CK
            </h2>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted">
            Technique badges appear only when an observed alert carries a
            justified rule mapping.
          </p>
          <div className="mt-4 space-y-2">
            {data.observed_techniques.length ? (
              data.observed_techniques.map((technique) => (
                <div
                  className="rounded-lg border border-line/70 bg-[#0b111a] p-3"
                  key={technique.technique_id}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-accent">
                      {technique.technique_id}
                    </span>
                    <span className="text-[9px] uppercase tracking-wider text-slate-600">
                      {technique.tactic}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-300">
                    {technique.technique_name}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-line p-4 text-xs text-muted">
                No mapped alert techniques observed in this scope.
              </div>
            )}
          </div>
          <div className="mt-5 border-t border-line pt-4 text-[10px] leading-5 text-slate-500">
            <div className="flex items-center gap-2">
              <Radio className="size-3.5 text-accent" /> Animated = active
              within 60 seconds
            </div>
            <div className="mt-1 flex items-center gap-2">
              <Crosshair className="size-3.5 text-sky-400" /> Blue = recent;
              grey = historical; rose = alert evidence
            </div>
            <div className="mt-1 flex items-center gap-2">
              <Database className="size-3.5 text-slate-500" /> Counts are
              observed aggregates, not inferred sessions
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
