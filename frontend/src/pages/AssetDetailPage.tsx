import {
  ArrowLeft,
  BellRing,
  Box,
  Clock3,
  Fingerprint,
  Network,
  Shield,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import {
  AssetStatusBadge,
  AlertStatusBadge,
  EventStatusBadge,
  SeverityBadge,
} from "../components/data/Badge";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/data/QueryState";
import { RiskIndicator } from "../components/data/RiskIndicator";
import { useAlerts, useAsset, useEvents } from "../hooks/useCoreData";
import { endpoint, formatDateTime, humanize } from "../lib/format";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line/80 bg-[#0b111a] p-3.5">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-600">
        {label}
      </dt>
      <dd className="mt-2 break-words text-xs text-slate-200">{value}</dd>
    </div>
  );
}

export function AssetDetailPage() {
  const { assetId } = useParams();
  const asset = useAsset(assetId);
  const events = useEvents({ asset_id: assetId, page: 1, page_size: 10 });
  const alerts = useAlerts({ asset_id: assetId, page: 1, page_size: 5 });
  const activeAlerts = useAlerts({
    asset_id: assetId,
    active_only: true,
    page: 1,
    page_size: 1,
  });

  if (asset.isLoading) return <LoadingState label="Loading asset profile" />;
  if (asset.isError || !asset.data) return <ErrorState error={asset.error} />;

  return (
    <div className="mx-auto max-w-[1500px]">
      <Link
        className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-accent"
        to="/assets"
      >
        <ArrowLeft className="size-3.5" />
        Back to asset inventory
      </Link>

      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div className="flex items-start gap-4">
          <div className="grid size-12 shrink-0 place-items-center rounded-xl border border-accent/20 bg-accent/10 text-accent">
            <Box className="size-6" strokeWidth={1.7} />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                {asset.data.hostname}
              </h1>
              <AssetStatusBadge status={asset.data.status} />
            </div>
            <p className="mt-2 text-sm text-muted">{asset.data.display_name}</p>
            <p className="mt-2 font-mono text-xs text-slate-500">
              Asset {asset.data.id}
            </p>
          </div>
        </div>
        <div className="w-full rounded-xl border border-line bg-panel p-4 sm:w-56">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Shield className="size-4 text-accent" />
            Current risk score
          </div>
          <div className="mt-4">
            <RiskIndicator detailed score={asset.data.risk_score} />
          </div>
          <p className="mt-3 text-[10px] leading-4 text-muted">
            Experimental prioritization value; not a scientific probability.
          </p>
        </div>
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <Fingerprint className="size-4 text-accent" />
            <h2 className="text-sm font-semibold text-slate-100">
              Identity and posture
            </h2>
          </div>
          <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Detail label="Hostname" value={asset.data.hostname} />
            <Detail label="IP address" value={asset.data.ip_address} />
            <Detail
              label="MAC address"
              value={asset.data.mac_address ?? "Not reported"}
            />
            <Detail
              label="Asset type"
              value={humanize(asset.data.asset_type)}
            />
            <Detail
              label="Operating system"
              value={asset.data.operating_system}
            />
            <Detail
              label="Environment"
              value={humanize(asset.data.environment)}
            />
            <Detail
              label="Network zone"
              value={asset.data.network_zone.toUpperCase()}
            />
            <Detail
              label="Criticality"
              value={humanize(asset.data.criticality)}
            />
            <Detail label="Status" value={humanize(asset.data.status)} />
          </dl>
        </article>

        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <Clock3 className="size-4 text-accent" />
            <h2 className="text-sm font-semibold text-slate-100">
              Observation timeline
            </h2>
          </div>
          <dl className="mt-5 space-y-3">
            <Detail
              label="First seen"
              value={formatDateTime(asset.data.first_seen)}
            />
            <Detail
              label="Last seen"
              value={formatDateTime(asset.data.last_seen)}
            />
            <Detail
              label="Record updated"
              value={formatDateTime(asset.data.updated_at)}
            />
          </dl>
        </article>
      </section>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <BellRing className="size-4 text-accent" />
              <h2 className="text-sm font-semibold text-slate-100">
                Active and recent alerts
              </h2>
            </div>
            <p className="mt-1 text-xs text-muted">
              {activeAlerts.data?.total ?? 0} active alert
              {activeAlerts.data?.total === 1 ? "" : "s"} currently influence
              this asset&apos;s experimental risk score
            </p>
          </div>
          <Link
            className="text-xs text-accent hover:text-emerald-300"
            to={`/alerts?asset_id=${asset.data.id}`}
          >
            View all
          </Link>
        </div>
        {alerts.isLoading ? (
          <LoadingState label="Loading asset alerts" />
        ) : alerts.isError ? (
          <ErrorState error={alerts.error} />
        ) : !alerts.data?.items.length ? (
          <EmptyState message="No detection alerts are associated with this asset." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left">
              <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Alert</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {alerts.data.items.map((alert) => (
                  <tr className="hover:bg-white/[0.025]" key={alert.id}>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={alert.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        className="text-xs font-medium text-slate-200 hover:text-accent"
                        to={`/alerts/${alert.id}`}
                      >
                        {alert.title}
                      </Link>
                      <p className="mt-1 font-mono text-[10px] text-muted">
                        {alert.detection_rule.rule_id}
                      </p>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                      {alert.source_ip ?? "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-muted">
                      {formatDateTime(alert.timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <AlertStatusBadge status={alert.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <Network className="size-4 text-accent" />
              <h2 className="text-sm font-semibold text-slate-100">
                Recent security events
              </h2>
            </div>
            <p className="mt-1 text-xs text-muted">
              Latest normalized activity resolved to this asset
            </p>
          </div>
          <Link
            className="text-xs text-accent hover:text-emerald-300"
            to={`/events?asset_id=${asset.data.id}`}
          >
            View all
          </Link>
        </div>
        {events.isLoading ? (
          <LoadingState label="Loading recent activity" />
        ) : events.isError ? (
          <ErrorState error={events.error} />
        ) : !events.data?.items.length ? (
          <EmptyState message="No security events are associated with this asset." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left">
              <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                  <th className="px-4 py-3 font-medium">Event</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium">Destination</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Severity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {events.data.items.map((event) => (
                  <tr className="hover:bg-white/[0.025]" key={event.id}>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
                      {formatDateTime(event.timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        className="text-xs font-medium text-slate-200 hover:text-accent"
                        to={`/events?event=${event.id}`}
                      >
                        {humanize(event.event_type)}
                      </Link>
                      <p className="mt-1 text-[11px] text-muted">
                        {humanize(event.action)}
                      </p>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                      {endpoint(event.source_ip, event.source_port)}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                      {endpoint(event.destination_ip, event.destination_port)}
                    </td>
                    <td className="px-4 py-3">
                      <EventStatusBadge status={event.status} />
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={event.severity} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Object.keys(asset.data.metadata_json).length > 0 && (
        <section className="mt-6 rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold text-slate-100">
            Asset metadata
          </h2>
          <pre className="mt-4 overflow-x-auto rounded-lg border border-line bg-[#080d14] p-4 font-mono text-xs leading-6 text-slate-400">
            {JSON.stringify(asset.data.metadata_json, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
