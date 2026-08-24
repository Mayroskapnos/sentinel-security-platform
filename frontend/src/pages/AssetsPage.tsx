import { Search, SlidersHorizontal } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AssetStatusBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { Pagination } from "../components/data/Pagination";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/data/QueryState";
import { RiskIndicator } from "../components/data/RiskIndicator";
import { useAssets } from "../hooks/useCoreData";
import { formatDateTime, humanize } from "../lib/format";
import type { AssetFilters } from "../types/core";

const inputClass =
  "h-9 rounded-md border border-line bg-[#0b111a] px-3 text-xs text-slate-200 outline-none transition focus:border-accent/50 focus:ring-1 focus:ring-accent/20";

function positiveInteger(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function AssetsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(
    searchParams.get("search") ?? "",
  );
  const filters: AssetFilters = {
    search: searchParams.get("search") || undefined,
    asset_type:
      (searchParams.get("asset_type") as AssetFilters["asset_type"]) ||
      undefined,
    status: (searchParams.get("status") as AssetFilters["status"]) || undefined,
    network_zone: searchParams.get("network_zone") || undefined,
    criticality:
      (searchParams.get("criticality") as AssetFilters["criticality"]) ||
      undefined,
    min_risk_score: searchParams.get("min_risk_score")
      ? Number(searchParams.get("min_risk_score"))
      : undefined,
    page: positiveInteger(searchParams.get("page"), 1),
    page_size: 25,
  };
  const assets = useAssets(filters);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setFilter("search", searchInput.trim());
  }

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeading
        actions={
          <span className="rounded-md border border-line bg-panel px-3 py-2 font-mono text-xs text-muted">
            {assets.data?.total ?? 0} registered
          </span>
        }
        description="Persistent inventory, operational state, ownership context, and experimental risk prioritization."
        eyebrow="Asset inventory"
        title="Assets"
      />

      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex flex-col gap-3 border-b border-line p-4 xl:flex-row xl:items-center">
          <form className="relative min-w-64 flex-1" onSubmit={submitSearch}>
            <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-600" />
            <input
              aria-label="Search assets"
              className={`${inputClass} w-full pl-9`}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search hostname, display name, or IP"
              value={searchInput}
            />
          </form>
          <div className="flex items-center gap-2 overflow-x-auto">
            <SlidersHorizontal className="size-4 shrink-0 text-slate-600" />
            <select
              aria-label="Asset type"
              className={inputClass}
              onChange={(event) => setFilter("asset_type", event.target.value)}
              value={filters.asset_type ?? ""}
            >
              <option value="">All types</option>
              <option value="workstation">Workstation</option>
              <option value="server">Server</option>
              <option value="web_server">Web server</option>
              <option value="database">Database</option>
              <option value="container">Container</option>
              <option value="network_device">Network device</option>
            </select>
            <select
              aria-label="Asset status"
              className={inputClass}
              onChange={(event) => setFilter("status", event.target.value)}
              value={filters.status ?? ""}
            >
              <option value="">All statuses</option>
              <option value="online">Online</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
              <option value="offline">Offline</option>
              <option value="unknown">Unknown</option>
            </select>
            <select
              aria-label="Network zone"
              className={inputClass}
              onChange={(event) =>
                setFilter("network_zone", event.target.value)
              }
              value={filters.network_zone ?? ""}
            >
              <option value="">All zones</option>
              <option value="dmz">DMZ</option>
              <option value="employee">Employee</option>
              <option value="server">Server</option>
            </select>
            <select
              aria-label="Minimum risk"
              className={inputClass}
              onChange={(event) =>
                setFilter("min_risk_score", event.target.value)
              }
              value={filters.min_risk_score ?? ""}
            >
              <option value="">Any risk</option>
              <option value="21">Guarded+</option>
              <option value="41">Medium+</option>
              <option value="61">High+</option>
              <option value="81">Critical</option>
            </select>
          </div>
        </div>

        {assets.isLoading ? (
          <LoadingState label="Loading asset inventory" />
        ) : assets.isError ? (
          <ErrorState error={assets.error} />
        ) : !assets.data?.items.length ? (
          <EmptyState message="No assets match the current filters." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-left">
                <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Hostname</th>
                    <th className="px-4 py-3 font-medium">IP address</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Operating system</th>
                    <th className="px-4 py-3 font-medium">Zone</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Risk</th>
                    <th className="px-4 py-3 font-medium">Last seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {assets.data.items.map((asset) => (
                    <tr
                      className="transition-colors hover:bg-white/[0.025]"
                      key={asset.id}
                    >
                      <td className="px-4 py-3">
                        <Link
                          className="text-xs font-medium text-slate-100 hover:text-accent"
                          to={`/assets/${asset.id}`}
                        >
                          {asset.hostname}
                        </Link>
                        <p className="mt-1 text-[11px] text-muted">
                          {asset.display_name}
                        </p>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-300">
                        {asset.ip_address}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {humanize(asset.asset_type)}
                      </td>
                      <td className="max-w-64 truncate px-4 py-3 text-xs text-muted">
                        {asset.operating_system}
                      </td>
                      <td className="px-4 py-3 text-xs uppercase text-slate-400">
                        {asset.network_zone}
                      </td>
                      <td className="px-4 py-3">
                        <AssetStatusBadge status={asset.status} />
                      </td>
                      <td className="px-4 py-3">
                        <RiskIndicator score={asset.risk_score} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-muted">
                        {formatDateTime(asset.last_seen)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              onPageChange={(page: number) => setFilter("page", String(page))}
              page={assets.data.page}
              pages={assets.data.pages}
              total={assets.data.total}
            />
          </>
        )}
      </section>
    </div>
  );
}
