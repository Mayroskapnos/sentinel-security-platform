import { Search, SlidersHorizontal } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { SeverityBadge } from "../components/data/Badge";
import { PageHeading } from "../components/data/PageHeading";
import { Pagination } from "../components/data/Pagination";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../components/data/QueryState";
import { useRules, useUpdateRule } from "../hooks/useCoreData";
import { humanize } from "../lib/format";
import type { DetectionRuleFilters } from "../types/core";

const inputClass =
  "h-9 rounded-md border border-line bg-[#0b111a] px-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent/50";

export function RulesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const filters = useMemo<DetectionRuleFilters>(
    () => ({
      search: searchParams.get("search") || undefined,
      severity:
        (searchParams.get("severity") as DetectionRuleFilters["severity"]) ||
        undefined,
      rule_type:
        (searchParams.get("rule_type") as DetectionRuleFilters["rule_type"]) ||
        undefined,
      enabled:
        searchParams.get("enabled") === null
          ? undefined
          : searchParams.get("enabled") === "true",
      page: Math.max(1, Number(searchParams.get("page")) || 1),
      page_size: 20,
    }),
    [searchParams],
  );
  const rules = useRules(filters);
  const update = useUpdateRule();

  function updateParameters(updates: Record<string, string>) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    next.delete("page");
    setSearchParams(next);
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    updateParameters({ search: search.trim() });
  }

  function setPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(page));
    setSearchParams(next);
  }

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeading
        actions={
          <span className="rounded-md border border-line bg-panel px-3 py-2 font-mono text-xs text-muted">
            {rules.data?.total ?? 0} synchronized rules
          </span>
        }
        description="Inspect version-controlled, deterministic detections and control future evaluation without altering alert history."
        eyebrow="Detection content"
        title="Detection Rules"
      />
      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="flex flex-col gap-3 border-b border-line p-4 lg:flex-row lg:items-center">
          <form className="relative flex-1" onSubmit={submitSearch}>
            <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-600" />
            <input
              aria-label="Search rules"
              className={`${inputClass} w-full pl-9`}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search rule ID, name, or description"
              value={search}
            />
          </form>
          <div className="flex flex-wrap items-center gap-2">
            <SlidersHorizontal className="size-4 text-slate-600" />
            <select
              aria-label="Rule type"
              className={inputClass}
              onChange={(event) =>
                updateParameters({ rule_type: event.target.value })
              }
              value={filters.rule_type ?? ""}
            >
              <option value="">All rule types</option>
              <option value="threshold">Threshold</option>
              <option value="sequence">Sequence</option>
              <option value="single_event">Single event</option>
            </select>
            <select
              aria-label="Rule severity"
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
              aria-label="Rule status"
              className={inputClass}
              onChange={(event) =>
                updateParameters({ enabled: event.target.value })
              }
              value={
                filters.enabled === undefined ? "" : String(filters.enabled)
              }
            >
              <option value="">All states</option>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
            <button
              className="h-9 rounded-md border border-accent/30 bg-accent/10 px-4 text-xs font-medium text-accent"
              onClick={() => updateParameters({ search: search.trim() })}
              type="button"
            >
              Apply
            </button>
          </div>
        </div>
        {rules.isLoading ? (
          <LoadingState label="Loading detection rules" />
        ) : rules.isError ? (
          <ErrorState error={rules.error} />
        ) : !rules.data?.items.length ? (
          <EmptyState message="No detection rules match the current filters." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[950px] text-left">
                <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Rule ID</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">MITRE technique</th>
                    <th className="px-4 py-3">Enabled</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {rules.data.items.map((rule) => (
                    <tr className="hover:bg-white/[0.025]" key={rule.id}>
                      <td className="px-4 py-3">
                        <Link
                          className="font-mono text-xs text-accent hover:text-accent/80"
                          to={`/rules/${rule.id}`}
                        >
                          {rule.rule_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          className="text-xs font-medium text-slate-200 hover:text-accent"
                          to={`/rules/${rule.id}`}
                        >
                          {rule.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">
                        {humanize(rule.rule_type)}
                      </td>
                      <td className="px-4 py-3">
                        <SeverityBadge severity={rule.severity} />
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {rule.mitre_technique_id
                          ? `${rule.mitre_technique_id} · ${rule.mitre_technique_name}`
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-slate-300">
                          <input
                            aria-label={`${rule.enabled ? "Disable" : "Enable"} ${rule.rule_id}`}
                            checked={rule.enabled}
                            className="size-4 accent-[#39c6a3]"
                            disabled={update.isPending}
                            onChange={(event) =>
                              update.mutate({
                                ruleId: rule.id,
                                enabled: event.target.checked,
                              })
                            }
                            type="checkbox"
                          />
                          {rule.enabled ? "Enabled" : "Disabled"}
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              onPageChange={setPage}
              page={rules.data.page}
              pages={rules.data.pages}
              total={rules.data.total}
            />
          </>
        )}
      </section>
    </div>
  );
}
