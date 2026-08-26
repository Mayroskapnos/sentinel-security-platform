import { FilterX, Radio, Search, ShieldCheck } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { IncidentStatusBadge, SeverityBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { Pagination } from "../components/data/Pagination";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useIncidents } from "../hooks/useCoreData";
import { formatDateTime } from "../lib/format";
import { incidentFiltersFromSearchParams } from "../lib/incidents";
import { useTelemetry } from "../realtime/TelemetryContext";
import type { IncidentFilters } from "../types/core";

const inputClass =
  "h-9 rounded-md border border-line bg-[#0b111a] px-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent/50";

export function IncidentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const telemetry = useTelemetry();
  const filters = useMemo<IncidentFilters>(
    () => incidentFiltersFromSearchParams(searchParams),
    [searchParams],
  );
  const incidents = useIncidents(filters);

  function updateParameters(updates: Record<string, string>) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    next.delete("page");
    setSearchParams(next);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    updateParameters({ search: search.trim() });
  }

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeading
        actions={
          <div className="flex flex-col items-end gap-2">
            <span className="rounded-md border border-line bg-panel px-3 py-2 font-mono text-xs text-muted">
              {incidents.data?.total ?? 0} matching incidents
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-muted">
              <Radio className="size-3 text-accent" />
              {telemetry.connectionState === "connected"
                ? "Live correlation updates active"
                : "Showing persistent history"}
            </span>
          </div>
        }
        description="Prioritize persistent, explainable clusters of related security alerts."
        eyebrow="Correlation operations"
        title="Incidents"
      />

      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <form className="border-b border-line p-4" onSubmit={submit}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="relative xl:col-span-2">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-600" />
              <input
                aria-label="Search incidents"
                className={`${inputClass} w-full pl-9`}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Incident number, title, or asset"
                value={search}
              />
            </div>
            <select
              aria-label="Severity"
              className={inputClass}
              onChange={(event) =>
                updateParameters({ severity: event.target.value })
              }
              value={filters.severity ?? ""}
            >
              <option value="">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="informational">Informational</option>
            </select>
            <select
              aria-label="Status"
              className={inputClass}
              onChange={(event) =>
                updateParameters({ status: event.target.value })
              }
              value={filters.status ?? ""}
            >
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="contained">Contained</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False positive</option>
            </select>
            <div className="flex gap-2">
              <select
                aria-label="Minimum confidence"
                className={`${inputClass} min-w-0 flex-1`}
                onChange={(event) =>
                  updateParameters({ confidence_min: event.target.value })
                }
                value={filters.confidence_min ?? ""}
              >
                <option value="">Any confidence</option>
                <option value="50">Moderate (50+)</option>
                <option value="80">High (80+)</option>
              </select>
              <button
                className="rounded-md border border-accent/30 bg-accent/10 px-4 text-xs text-accent"
                type="submit"
              >
                Apply
              </button>
            </div>
          </div>
          {searchParams.size > 0 ? (
            <button
              className="mt-3 inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-xs text-muted hover:text-white"
              onClick={() => {
                setSearch("");
                setSearchParams({});
              }}
              type="button"
            >
              <FilterX className="size-3.5" /> Clear filters
            </button>
          ) : null}
        </form>

        {incidents.isLoading ? (
          <LoadingState label="Loading incident queue" />
        ) : incidents.isError ? (
          <ErrorState error={incidents.error} />
        ) : !incidents.data?.items.length ? (
          <div className="py-16 text-center">
            <ShieldCheck className="mx-auto size-8 text-slate-600" />
            <p className="mt-4 text-sm text-slate-300">
              No correlated incidents yet.
            </p>
            <p className="mx-auto mt-2 max-w-lg text-xs leading-5 text-muted">
              Incidents are created when SENTINEL determines that related
              security Alerts belong to the same activity cluster.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] text-left">
              <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Incident</th>
                  <th className="px-4 py-3">Affected assets</th>
                  <th className="px-4 py-3">Alerts</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">First seen</th>
                  <th className="px-4 py-3">Last activity</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {incidents.data.items.map((incident) => (
                  <tr className="hover:bg-white/[0.025]" key={incident.id}>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={incident.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        className="text-xs font-medium text-slate-100 hover:text-accent"
                        to={`/incidents/${incident.id}`}
                      >
                        {incident.title}
                      </Link>
                      <p className="mt-1 font-mono text-[10px] text-accent">
                        {incident.incident_number}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {incident.asset_count} ·{" "}
                      {incident.affected_assets.slice(0, 2).join(", ") ||
                        "Unresolved"}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-300">
                      {incident.alert_count}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-accent">
                        {incident.confidence_score} / 100
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-muted">
                      {formatDateTime(incident.first_activity_at)}
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
        )}
        {incidents.data && incidents.data.pages > 1 ? (
          <Pagination
            onPageChange={(page) => {
              const next = new URLSearchParams(searchParams);
              next.set("page", String(page));
              setSearchParams(next);
            }}
            page={incidents.data.page}
            pages={incidents.data.pages}
            total={incidents.data.total}
          />
        ) : null}
      </section>
    </div>
  );
}
