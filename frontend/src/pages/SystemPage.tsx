import { Activity, Database, Radio, Server, Wifi } from "lucide-react";

import { AssetStatusBadge, EventStatusBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useHealth } from "../hooks/useHealth";
import { useLabStatus } from "../hooks/useCoreData";
import { formatDateTime, humanize } from "../lib/format";
import { useTelemetry } from "../realtime/TelemetryContext";

export function SystemPage() {
  const health = useHealth();
  const lab = useLabStatus();
  const telemetry = useTelemetry();

  if (health.isLoading || lab.isLoading) {
    return <LoadingState label="Loading platform and corporate lab status" />;
  }
  if (health.isError || lab.isError || !health.data || !lab.data) {
    return <ErrorState error={health.error ?? lab.error} />;
  }

  const platformRows = [
    {
      label: "API and database",
      detail: `SENTINEL ${health.data.version}`,
      state: health.data.status,
      icon: Database,
    },
    {
      label: "WebSocket telemetry",
      detail: "Live browser delivery",
      state: telemetry.connectionState,
      icon: Wifi,
    },
    {
      label: "Corporate lab collector",
      detail: "Read-only log forwarding",
      state: lab.data.collector_status,
      icon: Radio,
    },
  ];

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeading
        actions={
          <span className="rounded-md border border-line bg-panel px-3 py-2 text-xs text-slate-300">
            Corporate Lab v{lab.data.version}
          </span>
        }
        description="Observed service and telemetry state inferred without Docker socket access. Online means recently reporting, not secure."
        eyebrow="Runtime visibility"
        title="System"
      />

      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        {platformRows.map(({ detail, icon: Icon, label, state }) => (
          <article
            className="rounded-xl border border-line bg-panel p-5 shadow-panel"
            key={label}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-100">{label}</p>
                <p className="mt-1 text-xs text-muted">{detail}</p>
              </div>
              <Icon className="size-5 text-accent" />
            </div>
            <div className="mt-5">
              <EventStatusBadge
                status={
                  state === "healthy" ||
                  state === "connected" ||
                  state === "active"
                    ? "success"
                    : state
                }
              />
            </div>
          </article>
        ))}
      </section>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex items-center justify-between border-b border-line p-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Corporate lab assets
            </h2>
            <p className="mt-1 text-xs text-muted">
              Recent genuine telemetry by canonical asset identity
            </p>
          </div>
          <span className="text-xs text-muted">
            {lab.data.active_assets} / {lab.data.total_assets} online
          </span>
        </div>
        <div className="grid gap-px bg-line md:grid-cols-2 xl:grid-cols-5">
          {lab.data.assets.map((asset) => (
            <article className="bg-panel p-5" key={asset.hostname}>
              <div className="flex items-center justify-between gap-2">
                <Server className="size-4 text-accent" />
                <AssetStatusBadge status={asset.status} />
              </div>
              <p className="mt-4 text-sm font-medium text-slate-100">
                {asset.hostname}
              </p>
              <p className="mt-1 text-[11px] uppercase tracking-wider text-muted">
                {asset.network_zone}
              </p>
              <p className="mt-4 text-[11px] text-slate-500">
                Last telemetry: {formatDateTime(asset.last_telemetry)}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-xl border border-line bg-panel p-5 shadow-panel">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-accent" />
          <h2 className="text-sm font-semibold text-slate-100">
            Telemetry sources
          </h2>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {lab.data.sources.map((source) => (
            <div
              className="rounded-lg border border-line/80 bg-[#0b111a] p-3"
              key={source.source}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-slate-300">
                  {humanize(source.source)}
                </span>
                <EventStatusBadge
                  status={source.status === "active" ? "success" : "stale"}
                />
              </div>
              <p className="mt-2 text-[10px] text-slate-600">
                {formatDateTime(source.last_telemetry)}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
