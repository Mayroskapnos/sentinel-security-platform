import { FilterX, Radio, Search } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AlertStatusBadge, SeverityBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { Pagination } from "../components/data/Pagination";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/data/QueryState";
import { useAlerts } from "../hooks/useCoreData";
import { formatDateTime } from "../lib/format";
import { useTelemetry } from "../realtime/TelemetryContext";
import type { AlertFilters } from "../types/core";

const inputClass =
  "h-9 rounded-md border border-line bg-[#0b111a] px-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent/50";

function positiveInteger(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const telemetry = useTelemetry();
  const [sourceIp, setSourceIp] = useState(searchParams.get("source_ip") ?? "");
  const [destinationIp, setDestinationIp] = useState(
    searchParams.get("destination_ip") ?? "",
  );
  const [ruleId, setRuleId] = useState(searchParams.get("rule_id") ?? "");
  const filters = useMemo<AlertFilters>(
    () => ({
      severity:
        (searchParams.get("severity") as AlertFilters["severity"]) || undefined,
      status:
        (searchParams.get("status") as AlertFilters["status"]) || undefined,
      rule_id: searchParams.get("rule_id") || undefined,
      asset_id: searchParams.get("asset_id") || undefined,
      source_ip: searchParams.get("source_ip") || undefined,
      destination_ip: searchParams.get("destination_ip") || undefined,
      page: positiveInteger(searchParams.get("page")),
      page_size: 20,
    }),
    [searchParams],
  );
  const alerts = useAlerts(filters);

  function updateParameters(updates: Record<string, string>) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    next.delete("page");
    setSearchParams(next);
  }

  function submitFilters(event: FormEvent) {
    event.preventDefault();
    updateParameters({
      source_ip: sourceIp.trim(),
      destination_ip: destinationIp.trim(),
      rule_id: ruleId.trim(),
    });
  }

  function setPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(page));
    setSearchParams(next);
  }

  function clearFilters() {
    setSourceIp("");
    setDestinationIp("");
    setRuleId("");
    setSearchParams({});
  }

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeading
        actions={
          <div className="flex flex-col items-end gap-2">
            <span className="rounded-md border border-line bg-panel px-3 py-2 font-mono text-xs text-muted">
              {alerts.data?.total ?? 0} matching alerts
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-muted">
              <Radio
                className={`size-3 ${telemetry.connectionState === "connected" ? "text-accent" : "text-slate-600"}`}
              />
              {telemetry.connectionState === "connected"
                ? "Live alert delivery active"
                : "Showing persistent history"}
            </span>
          </div>
        }
        description="Prioritize explainable, evidence-backed detections and manage analyst workflow state."
        eyebrow="Detection operations"
        title="Alerts"
      />

      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <form className="border-b border-line p-4" onSubmit={submitFilters}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-600" />
              <input
                aria-label="Rule ID"
                className={`${inputClass} w-full pl-9`}
                onChange={(event) => setRuleId(event.target.value)}
                placeholder="Rule ID"
                value={ruleId}
              />
            </div>
            <input
              aria-label="Source IP"
              className={inputClass}
              onChange={(event) => setSourceIp(event.target.value)}
              placeholder="Source IP"
              value={sourceIp}
            />
            <input
              aria-label="Destination IP"
              className={inputClass}
              onChange={(event) => setDestinationIp(event.target.value)}
              placeholder="Destination IP"
              value={destinationIp}
            />
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
            <div className="flex gap-2">
              <select
                aria-label="Status"
                className={`${inputClass} min-w-0 flex-1`}
                onChange={(event) =>
                  updateParameters({ status: event.target.value })
                }
                value={filters.status ?? ""}
              >
                <option value="">All statuses</option>
                <option value="new">New</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
                <option value="false_positive">False positive</option>
              </select>
              <button
                className="rounded-md border border-accent/30 bg-accent/10 px-4 text-xs font-medium text-accent hover:bg-accent/15"
                type="submit"
              >
                Apply
              </button>
            </div>
          </div>
          {searchParams.size > 0 && (
            <button
              className="mt-3 inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-xs text-muted hover:bg-white/[0.04] hover:text-white"
              onClick={clearFilters}
              type="button"
            >
              <FilterX className="size-3.5" />
              Clear filters
            </button>
          )}
        </form>

        {alerts.isLoading ? (
          <LoadingState label="Loading detection alerts" />
        ) : alerts.isError ? (
          <ErrorState error={alerts.error} />
        ) : !alerts.data?.items.length ? (
          <EmptyState message="No alerts match the current filters." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1100px] text-left">
                <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Severity</th>
                    <th className="px-4 py-3 font-medium">Title</th>
                    <th className="px-4 py-3 font-medium">Asset</th>
                    <th className="px-4 py-3 font-medium">Source</th>
                    <th className="px-4 py-3 font-medium">Technique</th>
                    <th className="px-4 py-3 font-medium">Timestamp</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {alerts.data.items.map((alert) => (
                    <tr
                      className={`transition-colors hover:bg-white/[0.025] ${
                        telemetry.liveAlertIds.has(alert.id)
                          ? "bg-accent/[0.07]"
                          : ""
                      }`}
                      key={alert.id}
                    >
                      <td className="px-4 py-3">
                        <SeverityBadge severity={alert.severity} />
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          className="text-xs font-medium text-slate-100 hover:text-accent"
                          to={`/alerts/${alert.id}`}
                        >
                          {alert.title}
                        </Link>
                        <p className="mt-1 font-mono text-[10px] text-muted">
                          {alert.detection_rule.rule_id} ·{" "}
                          {alert.evidence_count} evidence event
                          {alert.evidence_count === 1 ? "" : "s"}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {alert.asset ? (
                          <Link
                            className="hover:text-accent"
                            to={`/assets/${alert.asset.id}`}
                          >
                            {alert.asset.hostname}
                          </Link>
                        ) : (
                          "Unresolved"
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                        {alert.source_ip ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {alert.mitre_technique_id
                          ? `${alert.mitre_technique_id} · ${alert.mitre_technique_name}`
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
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
            <Pagination
              onPageChange={setPage}
              page={alerts.data.page}
              pages={alerts.data.pages}
              total={alerts.data.total}
            />
          </>
        )}
      </section>
    </div>
  );
}
