import { FilterX, Search, SlidersHorizontal, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EventStatusBadge, SeverityBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { Pagination } from "../components/data/Pagination";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/data/QueryState";
import { queryKeys, useEvent, useEvents } from "../hooks/useCoreData";
import {
  endpoint,
  formatDateTime,
  humanize,
  toApiTimestamp,
} from "../lib/format";
import type { EventFilters } from "../types/core";
import { useTelemetry } from "../realtime/TelemetryContext";
import { canInsertLiveEvent, eventMatchesFilters } from "../realtime/telemetry";

const inputClass =
  "h-9 rounded-md border border-line bg-[#0b111a] px-3 text-xs text-slate-200 outline-none transition focus:border-accent/50 focus:ring-1 focus:ring-accent/20";

function positiveInteger(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function toLocalInput(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function JsonEvidence({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown>;
}) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </h3>
      <pre className="mt-3 max-h-72 overflow-auto rounded-lg border border-line bg-[#080d14] p-4 font-mono text-[11px] leading-5 text-slate-400">
        {JSON.stringify(value, null, 2)}
      </pre>
    </section>
  );
}

function EventDetailDrawer({
  eventId,
  onClose,
}: {
  eventId: string;
  onClose: () => void;
}) {
  const event = useEvent(eventId);
  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-black/55 backdrop-blur-sm"
      role="dialog"
    >
      <button
        aria-label="Close event detail"
        className="flex-1"
        onClick={onClose}
        type="button"
      />
      <aside className="h-full w-full max-w-2xl overflow-y-auto border-l border-line bg-[#0c121b] shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between border-b border-line bg-[#0c121b]/95 p-5 backdrop-blur">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">
              Event evidence
            </p>
            <h2 className="mt-2 text-lg font-semibold text-white">
              {event.data ? humanize(event.data.event_type) : "Security event"}
            </h2>
            <p className="mt-1 font-mono text-[10px] text-slate-600">
              {eventId}
            </p>
          </div>
          <button
            aria-label="Close"
            className="grid size-8 place-items-center rounded-md border border-line text-muted hover:bg-white/[0.04] hover:text-white"
            onClick={onClose}
            type="button"
          >
            <X className="size-4" />
          </button>
        </div>
        {event.isLoading ? (
          <LoadingState label="Loading event evidence" />
        ) : event.isError || !event.data ? (
          <ErrorState error={event.error} />
        ) : (
          <div className="space-y-7 p-5">
            <div className="flex flex-wrap gap-2">
              <SeverityBadge severity={event.data.severity} />
              <EventStatusBadge status={event.data.status} />
            </div>
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                ["Timestamp", formatDateTime(event.data.timestamp)],
                ["Telemetry source", humanize(event.data.source)],
                ["Hostname", event.data.hostname ?? "Unresolved"],
                ["Asset", event.data.asset?.display_name ?? "Unresolved"],
                [
                  "Source endpoint",
                  endpoint(event.data.source_ip, event.data.source_port),
                ],
                [
                  "Destination endpoint",
                  endpoint(
                    event.data.destination_ip,
                    event.data.destination_port,
                  ),
                ],
                ["Username", event.data.username ?? "Not reported"],
                ["Process", event.data.process_name ?? "Not reported"],
                ["Action", humanize(event.data.action)],
                ["Status", humanize(event.data.status)],
              ].map(([label, value]) => (
                <div
                  className="rounded-lg border border-line/80 bg-[#0b111a] p-3"
                  key={label}
                >
                  <dt className="text-[10px] uppercase tracking-[0.12em] text-slate-600">
                    {label}
                  </dt>
                  <dd className="mt-2 break-words text-xs text-slate-200">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <JsonEvidence
              label="Normalized data"
              value={event.data.normalized_data}
            />
            <JsonEvidence label="Raw event" value={event.data.raw_event} />
          </div>
        )}
      </aside>
    </div>
  );
}

export function EventsPage() {
  const queryClient = useQueryClient();
  const telemetry = useTelemetry();
  const [searchParams, setSearchParams] = useSearchParams();
  const [hostname, setHostname] = useState(searchParams.get("hostname") ?? "");
  const [username, setUsername] = useState(searchParams.get("username") ?? "");
  const [sourceIp, setSourceIp] = useState(searchParams.get("source_ip") ?? "");
  const [destinationIp, setDestinationIp] = useState(
    searchParams.get("destination_ip") ?? "",
  );

  const filters = useMemo<EventFilters>(
    () => ({
      hostname: searchParams.get("hostname") || undefined,
      asset_id: searchParams.get("asset_id") || undefined,
      event_type: searchParams.get("event_type") || undefined,
      severity:
        (searchParams.get("severity") as EventFilters["severity"]) || undefined,
      source_ip: searchParams.get("source_ip") || undefined,
      destination_ip: searchParams.get("destination_ip") || undefined,
      username: searchParams.get("username") || undefined,
      status: searchParams.get("status") || undefined,
      start_time: searchParams.get("start_time") || undefined,
      end_time: searchParams.get("end_time") || undefined,
      page: positiveInteger(searchParams.get("page"), 1),
      page_size: 20,
    }),
    [searchParams],
  );
  const events = useEvents(filters);
  const selectedEvent = searchParams.get("event") ?? undefined;
  const [acknowledgedEventIds, setAcknowledgedEventIds] = useState<
    ReadonlySet<string>
  >(() => new Set());
  const pendingEvents = canInsertLiveEvent(filters)
    ? []
    : telemetry.receivedEvents.filter(
        (event) =>
          !acknowledgedEventIds.has(event.id) &&
          eventMatchesFilters(event, filters),
      );

  function updateParameters(updates: Record<string, string>) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    next.delete("page");
    next.delete("event");
    setSearchParams(next);
  }

  function submitTextFilters(event: FormEvent) {
    event.preventDefault();
    updateParameters({
      hostname: hostname.trim(),
      username: username.trim(),
      source_ip: sourceIp.trim(),
      destination_ip: destinationIp.trim(),
    });
  }

  function setSingleFilter(key: string, value: string) {
    updateParameters({ [key]: value });
  }

  function setPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(page));
    next.delete("event");
    setSearchParams(next);
  }

  function openEvent(eventId: string) {
    const next = new URLSearchParams(searchParams);
    next.set("event", eventId);
    setSearchParams(next);
  }

  function closeEvent() {
    const next = new URLSearchParams(searchParams);
    next.delete("event");
    setSearchParams(next);
  }

  function clearFilters() {
    setHostname("");
    setUsername("");
    setSourceIp("");
    setDestinationIp("");
    setSearchParams({});
    setAcknowledgedEventIds(
      new Set(telemetry.receivedEvents.map((event) => event.id)),
    );
  }

  function showNewestEvents() {
    const next = new URLSearchParams(searchParams);
    next.delete("page");
    next.delete("start_time");
    next.delete("end_time");
    next.delete("event");
    setAcknowledgedEventIds(
      new Set(telemetry.receivedEvents.map((event) => event.id)),
    );
    setSearchParams(next);
    void queryClient.invalidateQueries({ queryKey: queryKeys.events.lists });
  }

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeading
        actions={
          <div className="flex flex-col items-end gap-2">
            <span className="rounded-md border border-line bg-panel px-3 py-2 font-mono text-xs text-muted">
              {events.data?.total ?? 0} matching events
            </span>
            {telemetry.connectionState !== "connected" && (
              <span className="text-[11px] text-amber-300/80">
                Live telemetry unavailable. Historical events remain available.
              </span>
            )}
          </div>
        }
        description="Investigate normalized telemetry with server-side filtering, bounded queries, and preserved raw evidence."
        eyebrow="Security telemetry"
        title="Events"
      />

      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <form className="border-b border-line p-4" onSubmit={submitTextFilters}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-600" />
              <input
                aria-label="Filter by hostname"
                className={`${inputClass} w-full pl-9`}
                onChange={(event) => setHostname(event.target.value)}
                placeholder="Hostname"
                value={hostname}
              />
            </div>
            <input
              aria-label="Filter by username"
              className={inputClass}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Username"
              value={username}
            />
            <input
              aria-label="Filter by source IP"
              className={inputClass}
              onChange={(event) => setSourceIp(event.target.value)}
              placeholder="Source IP"
              value={sourceIp}
            />
            <div className="flex gap-2">
              <input
                aria-label="Filter by destination IP"
                className={`${inputClass} min-w-0 flex-1`}
                onChange={(event) => setDestinationIp(event.target.value)}
                placeholder="Destination IP"
                value={destinationIp}
              />
              <button
                className="rounded-md border border-accent/30 bg-accent/10 px-4 text-xs font-medium text-accent hover:bg-accent/15"
                type="submit"
              >
                Apply
              </button>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SlidersHorizontal className="size-4 text-slate-600" />
            <select
              aria-label="Event type"
              className={inputClass}
              onChange={(event) =>
                setSingleFilter("event_type", event.target.value)
              }
              value={filters.event_type ?? ""}
            >
              <option value="">All event types</option>
              <option value="authentication">Authentication</option>
              <option value="http_request">HTTP request</option>
              <option value="network_connection">Network connection</option>
              <option value="process_execution">Process execution</option>
              <option value="privilege">Privilege</option>
              <option value="database_connection">Database connection</option>
              <option value="session">Session</option>
            </select>
            <select
              aria-label="Severity"
              className={inputClass}
              onChange={(event) =>
                setSingleFilter("severity", event.target.value)
              }
              value={filters.severity ?? ""}
            >
              <option value="">All severities</option>
              <option value="informational">Informational</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <select
              aria-label="Event status"
              className={inputClass}
              onChange={(event) =>
                setSingleFilter("status", event.target.value)
              }
              value={filters.status ?? ""}
            >
              <option value="">All statuses</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
            </select>
            <input
              aria-label="Start time"
              className={inputClass}
              onChange={(event) =>
                setSingleFilter(
                  "start_time",
                  toApiTimestamp(event.target.value) ?? "",
                )
              }
              type="datetime-local"
              value={toLocalInput(filters.start_time ?? null)}
            />
            <input
              aria-label="End time"
              className={inputClass}
              onChange={(event) =>
                setSingleFilter(
                  "end_time",
                  toApiTimestamp(event.target.value) ?? "",
                )
              }
              type="datetime-local"
              value={toLocalInput(filters.end_time ?? null)}
            />
            {(searchParams.size > 0 || filters.asset_id) && (
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-xs text-muted hover:bg-white/[0.04] hover:text-white"
                onClick={clearFilters}
                type="button"
              >
                <FilterX className="size-3.5" />
                Clear
              </button>
            )}
            {filters.asset_id && (
              <span className="rounded-md border border-accent/20 bg-accent/10 px-2.5 py-2 text-[10px] uppercase tracking-wider text-accent">
                Scoped to asset
              </span>
            )}
          </div>
        </form>

        {pendingEvents.length > 0 && (
          <div className="flex items-center justify-between gap-3 border-b border-accent/15 bg-accent/[0.06] px-4 py-3 text-xs text-slate-300">
            <span>
              {pendingEvents.length} new event
              {pendingEvents.length === 1 ? " is" : "s are"} available outside
              this historical page.
            </span>
            <button
              className="shrink-0 rounded-md border border-accent/30 bg-accent/10 px-3 py-1.5 font-medium text-accent hover:bg-accent/15"
              onClick={showNewestEvents}
              type="button"
            >
              Show newest
            </button>
          </div>
        )}

        {events.isLoading ? (
          <LoadingState label="Loading normalized events" />
        ) : events.isError ? (
          <ErrorState error={events.error} />
        ) : !events.data?.items.length ? (
          <EmptyState message="No security events match the current filters." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1300px] text-left">
                <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Timestamp</th>
                    <th className="px-4 py-3 font-medium">Host</th>
                    <th className="px-4 py-3 font-medium">Event</th>
                    <th className="px-4 py-3 font-medium">Source IP</th>
                    <th className="px-4 py-3 font-medium">Destination</th>
                    <th className="px-4 py-3 font-medium">User</th>
                    <th className="px-4 py-3 font-medium">Action</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Severity</th>
                    <th className="px-4 py-3 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {events.data.items.map((event) => (
                    <tr
                      className={`transition-colors hover:bg-white/[0.025] ${
                        telemetry.liveEventIds.has(event.id)
                          ? "bg-accent/[0.07]"
                          : ""
                      }`}
                      key={event.id}
                    >
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
                        {formatDateTime(event.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {event.hostname ?? "Unresolved"}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          className="text-left text-xs font-medium text-slate-100 hover:text-accent"
                          onClick={() => openEvent(event.id)}
                          type="button"
                        >
                          {humanize(event.event_type)}
                        </button>
                        {telemetry.liveEventIds.has(event.id) && (
                          <span className="ml-2 rounded border border-accent/25 bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold tracking-wider text-accent">
                            LIVE
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                        {endpoint(event.source_ip, event.source_port)}
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                        {endpoint(event.destination_ip, event.destination_port)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">
                        {event.username ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {humanize(event.action)}
                      </td>
                      <td className="px-4 py-3">
                        <EventStatusBadge status={event.status} />
                      </td>
                      <td className="px-4 py-3">
                        <SeverityBadge severity={event.severity} />
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-muted">
                        {event.source}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              onPageChange={setPage}
              page={events.data.page}
              pages={events.data.pages}
              total={events.data.total}
            />
          </>
        )}
      </section>

      {selectedEvent && (
        <EventDetailDrawer eventId={selectedEvent} onClose={closeEvent} />
      )}
    </div>
  );
}
