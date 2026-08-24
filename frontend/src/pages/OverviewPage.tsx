import { Activity, Database, Radio, Server, ShieldCheck } from "lucide-react";

import { ApiError } from "../api/client";
import { StatusCard } from "../components/StatusCard";
import { useHealth } from "../hooks/useHealth";

export function OverviewPage() {
  const health = useHealth();
  const apiStatus = health.data?.checks.api.status;
  const databaseStatus = health.data?.checks.database.status;
  const state = health.isLoading
    ? "loading"
    : health.isError || health.data?.status !== "healthy"
      ? "degraded"
      : "healthy";

  const updatedAt = health.dataUpdatedAt
    ? new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(health.dataUpdatedAt)
    : "Waiting for first check";

  const errorMessage =
    health.error instanceof ApiError
      ? health.error.message
      : "Health data is temporarily unavailable.";

  return (
    <div className="mx-auto max-w-[1500px]">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-accent">
            <Radio className="size-3.5" />
            Live control plane
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Security Operations Overview
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            Service readiness and platform connectivity for the isolated
            SENTINEL environment.
          </p>
        </div>
        <p className="font-mono text-xs text-slate-500">
          Last check: {updatedAt}
        </p>
      </div>

      {health.isError && (
        <div
          className="mt-6 flex items-start gap-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-4 text-sm text-amber-100"
          role="alert"
        >
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-amber-400" />
          <div>
            <p className="font-medium">Control plane connection degraded</p>
            <p className="mt-1 text-xs leading-5 text-amber-100/65">
              {errorMessage}
            </p>
          </div>
        </div>
      )}

      <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatusCard
          detail="FastAPI service response"
          icon={Server}
          state={state}
          title="API service"
          value={
            apiStatus === "healthy"
              ? "Operational"
              : health.isLoading
                ? "Checking"
                : "Unavailable"
          }
        />
        <StatusCard
          detail={
            health.data?.checks.database.latency_ms != null
              ? `${health.data.checks.database.latency_ms.toFixed(2)} ms query latency`
              : "PostgreSQL connectivity"
          }
          icon={Database}
          state={databaseStatus === "healthy" ? "healthy" : state}
          title="Data store"
          value={
            databaseStatus === "healthy"
              ? "Connected"
              : health.isLoading
                ? "Checking"
                : "Unavailable"
          }
        />
        <StatusCard
          detail="Current runtime profile"
          icon={Activity}
          state={state}
          title="Environment"
          value={health.data?.environment ?? "Development"}
        />
        <StatusCard
          detail="Monitoring workspace foundation"
          icon={ShieldCheck}
          state={state}
          title="Platform"
          value={`v${health.data?.version ?? "0.1.0"}`}
        />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <article className="overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Security activity
              </h2>
              <p className="mt-1 text-xs text-muted">
                Normalized events will appear here.
              </p>
            </div>
            <span className="rounded-md border border-line bg-black/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
              Awaiting telemetry
            </span>
          </div>
          <div className="grid min-h-64 place-items-center p-8 text-center">
            <div>
              <div className="mx-auto grid size-12 place-items-center rounded-xl border border-line bg-[#0b111a]">
                <Activity className="size-5 text-slate-500" />
              </div>
              <p className="mt-4 text-sm font-medium text-slate-300">
                No event stream configured
              </p>
              <p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-muted">
                Event ingestion and database-backed activity arrive in SENTINEL
                Core, the next milestone.
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <h2 className="text-sm font-semibold text-slate-100">
            Platform readiness
          </h2>
          <p className="mt-1 text-xs text-muted">
            Milestone 0 service boundary
          </p>
          <div className="mt-5 space-y-3">
            {[
              ["React interface", "Ready"],
              [
                "FastAPI control plane",
                apiStatus === "healthy" ? "Ready" : "Checking",
              ],
              [
                "PostgreSQL data store",
                databaseStatus === "healthy" ? "Ready" : "Checking",
              ],
              ["Isolated lab network", "Planned"],
            ].map(([label, status]) => (
              <div
                className="flex items-center justify-between rounded-lg border border-line/80 bg-[#0b111a] px-3.5 py-3"
                key={label}
              >
                <span className="text-xs text-slate-300">{label}</span>
                <span
                  className={`text-[10px] font-semibold uppercase tracking-wider ${
                    status === "Ready" ? "text-emerald-400" : "text-slate-500"
                  }`}
                >
                  {status}
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
