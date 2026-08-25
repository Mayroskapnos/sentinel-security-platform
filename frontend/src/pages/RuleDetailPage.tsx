import { ArrowLeft, Braces, ShieldCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { SeverityBadge } from "../components/data/Badge";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useRule, useUpdateRule } from "../hooks/useCoreData";
import { humanize } from "../lib/format";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-[0.14em] text-slate-600">
        {label}
      </dt>
      <dd className="mt-1.5 text-sm text-slate-200">{value}</dd>
    </div>
  );
}

export function RuleDetailPage() {
  const { ruleId } = useParams();
  const rule = useRule(ruleId);
  const update = useUpdateRule();
  if (rule.isLoading) return <LoadingState label="Loading rule definition" />;
  if (rule.isError || !rule.data) return <ErrorState error={rule.error} />;
  const data = rule.data;
  const configuration = data.configuration;
  const threshold =
    typeof configuration.threshold === "object" &&
    configuration.threshold !== null
      ? (configuration.threshold as Record<string, unknown>)
      : null;
  const sequence =
    typeof configuration.sequence === "object" &&
    configuration.sequence !== null
      ? (configuration.sequence as Record<string, unknown>)
      : null;
  const groupBy = Array.isArray(configuration.group_by)
    ? configuration.group_by.map(String).join(", ")
    : "None";

  return (
    <div className="mx-auto max-w-[1200px]">
      <Link
        className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-accent"
        to="/rules"
      >
        <ArrowLeft className="size-3.5" /> Back to rules
      </Link>
      <section className="rounded-xl border border-line bg-panel p-6 shadow-panel">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <p className="font-mono text-xs tracking-wider text-accent">
              {data.rule_id}
            </p>
            <h1 className="mt-2 text-2xl font-semibold text-white">
              {data.name}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
              {data.description}
            </p>
            <div className="mt-4 flex gap-2">
              <SeverityBadge severity={data.severity} />
              <span className="rounded-md border border-line px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-300">
                {humanize(data.rule_type)}
              </span>
            </div>
          </div>
          <label className="flex items-center gap-3 rounded-lg border border-line bg-black/10 px-4 py-3 text-sm text-slate-200">
            <input
              checked={data.enabled}
              className="size-4 accent-[#39c6a3]"
              disabled={update.isPending}
              onChange={(event) =>
                update.mutate({
                  ruleId: data.id,
                  enabled: event.target.checked,
                })
              }
              type="checkbox"
            />
            {data.enabled ? "Evaluation enabled" : "Evaluation disabled"}
          </label>
        </div>
      </section>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-accent" />
            <h2 className="text-sm font-semibold">Rule behavior</h2>
          </div>
          <dl className="mt-5 grid gap-5 sm:grid-cols-2">
            <Detail label="Event type" value={data.event_type ?? "Any"} />
            <Detail label="Grouping" value={groupBy} />
            <Detail
              label="Threshold"
              value={
                threshold
                  ? `${String(threshold.count)} qualifying values`
                  : sequence
                    ? `${String(sequence.count)} prerequisite events`
                    : "One matching event"
              }
            />
            <Detail
              label="Timeframe"
              value={
                threshold
                  ? `${String(threshold.timeframe_seconds)} seconds`
                  : sequence
                    ? `${String(sequence.timeframe_seconds)} seconds`
                    : "Not applicable"
              }
            />
            <Detail
              label="Suppression"
              value={`${String(configuration.suppression_seconds ?? 0)} seconds`}
            />
            <Detail
              label="MITRE tactic"
              value={data.mitre_tactic ?? "Not mapped"}
            />
            <Detail
              label="MITRE technique"
              value={
                data.mitre_technique_id
                  ? `${data.mitre_technique_id} · ${data.mitre_technique_name}`
                  : "Not mapped"
              }
            />
          </dl>
        </section>
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <Braces className="size-4 text-accent" />
            <h2 className="text-sm font-semibold">Validated configuration</h2>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted">
            Repository YAML is safely parsed and synchronized as data. It never
            executes code, SQL, or expressions.
          </p>
          <pre className="mt-4 max-h-[440px] overflow-auto rounded-lg border border-line bg-[#080d14] p-4 text-[11px] leading-5 text-slate-300">
            {JSON.stringify(configuration, null, 2)}
          </pre>
        </section>
      </div>
    </div>
  );
}
