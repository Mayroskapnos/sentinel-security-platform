import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock3,
  LoaderCircle,
  Network,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import { useCancelScenarioRun, useScenarioRun } from "../hooks/useCoreData";
import { formatDateTime } from "../lib/format";
import {
  detectionOutcome,
  detectionOutcomeLabel,
  suppressionAdvisories,
} from "../lib/simulator";
import type { ScenarioRunStep } from "../types/core";

function StepMarker({ status }: { status: ScenarioRunStep["status"] }) {
  if (status === "completed")
    return <CheckCircle2 className="size-5 text-emerald-400" />;
  if (status === "running")
    return <LoaderCircle className="size-5 animate-spin text-accent" />;
  if (["failed", "cancelled"].includes(status))
    return <XCircle className="size-5 text-amber-400" />;
  return <Circle className="size-5 text-slate-600" />;
}

export function ScenarioRunPage() {
  const { runId } = useParams();
  const runQuery = useScenarioRun(runId);
  const cancel = useCancelScenarioRun();

  if (runQuery.isLoading) return <LoadingState label="Loading scenario run" />;
  if (runQuery.isError || !runQuery.data)
    return <ErrorState error={runQuery.error} />;
  const run = runQuery.data;
  const active = ["pending", "running"].includes(run.status);
  const suppression = suppressionAdvisories(run.result);
  const duration = run.started_at
    ? Math.max(
        0,
        Math.round(
          (Date.parse(run.finished_at ?? new Date().toISOString()) -
            Date.parse(run.started_at)) /
            1000,
        ),
      )
    : 0;

  return (
    <div className="mx-auto max-w-[1300px]">
      <Link
        className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-accent"
        to="/simulator"
      >
        <ArrowLeft className="size-3.5" /> Back to Attack Simulator
      </Link>
      <PageHeading
        actions={
          <div className="flex flex-wrap gap-2">
            <Link
              className="inline-flex items-center gap-2 rounded-md border border-accent/25 bg-accent/[0.06] px-3 py-2 text-xs text-accent hover:bg-accent/10"
              to={`/attack-map?run=${run.id}`}
            >
              <Network className="size-3.5" /> View attack progression
            </Link>
            {active ? (
              <button
                className="rounded-md border border-amber-400/25 bg-amber-400/[0.06] px-3 py-2 text-xs text-amber-200 hover:bg-amber-400/10 disabled:opacity-60"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate(run.id)}
                type="button"
              >
                Cancel future steps
              </button>
            ) : (
              <span className="rounded-md border border-line bg-panel px-3 py-2 text-xs uppercase tracking-wider text-slate-300">
                {run.status}
              </span>
            )}
          </div>
        }
        description="Backend-owned execution state and telemetry-backed observations for this controlled lab run."
        eyebrow={`${run.scenario_id} · ${run.id.slice(0, 8)}`}
        title={run.scenario_name}
      />

      {run.error_message ? (
        <div className="mt-6 flex gap-3 rounded-lg border border-amber-400/20 bg-amber-400/[0.06] p-4 text-xs text-amber-100">
          <AlertTriangle className="size-4 shrink-0" />
          {run.error_message}
        </div>
      ) : null}

      {suppression.length ? (
        <div className="mt-6 rounded-lg border border-amber-400/20 bg-amber-400/[0.05] p-4 text-xs text-amber-100">
          <p className="font-medium">
            Detection suppression was active at run start.
          </p>
          <p className="mt-1 leading-5 text-amber-100/70">
            Existing alert history is preserved. For new alert records, retry
            after{" "}
            {suppression
              .map(
                (item) =>
                  `${item.rule_id}: ${formatDateTime(item.recommended_retry_at)}`,
              )
              .join("; ")}
            .
          </p>
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Status", run.status],
          ["Duration", `${duration} seconds`],
          ["Security events", String(run.event_count)],
          ["Alerts", String(run.alert_count)],
        ].map(([label, value]) => (
          <article
            className="rounded-xl border border-line bg-panel p-5 shadow-panel"
            key={label}
          >
            <p className="text-[10px] uppercase tracking-wider text-muted">
              {label}
            </p>
            <p className="mt-3 text-xl font-semibold text-slate-100">{value}</p>
          </article>
        ))}
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <Clock3 className="size-4 text-accent" />
            <h2 className="text-sm font-semibold text-slate-100">
              Step timeline
            </h2>
          </div>
          <div className="mt-5 space-y-3">
            {run.steps.map((step) => (
              <div
                className="flex gap-3 rounded-lg border border-line/80 bg-[#0b111a] p-4"
                key={step.index}
              >
                <StepMarker status={step.status} />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-200">
                    {step.index}. {step.name}
                  </p>
                  <p className="mt-1 font-mono text-[10px] text-muted">
                    {step.action} · {step.status}
                  </p>
                  {step.message ? (
                    <p className="mt-2 text-xs text-slate-400">
                      {step.message}
                    </p>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-panel p-5 shadow-panel">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-accent" />
            <h2 className="text-sm font-semibold text-slate-100">
              Expected vs observed
            </h2>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted">
            Expected detections are validation goals, not fabricated outcomes.
          </p>
          <div className="mt-5 overflow-hidden rounded-lg border border-line">
            {run.detections.map((detection) => {
              const outcome = detectionOutcome(detection.observed, run.status);
              return (
                <div
                  className="flex items-start justify-between gap-3 border-b border-line/70 bg-[#0b111a] p-3 last:border-b-0"
                  key={detection.rule_id}
                >
                  <div>
                    <p className="font-mono text-xs text-slate-200">
                      {detection.rule_id}
                    </p>
                    {outcome === "expected_not_observed" ? (
                      <p className="mt-1 text-[10px] leading-4 text-muted">
                        {detection.note}
                      </p>
                    ) : null}
                  </div>
                  {outcome === "observed" ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-300">
                      <CheckCircle2 className="size-3.5" />
                      {detectionOutcomeLabel(outcome)}
                    </span>
                  ) : outcome === "awaiting_observation" ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400">
                      <Clock3 className="size-3.5" />
                      {detectionOutcomeLabel(outcome)}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-300">
                      <XCircle className="size-3.5" />
                      {detectionOutcomeLabel(outcome)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-xl border border-line bg-panel p-5 shadow-panel">
        <h2 className="text-sm font-semibold text-slate-100">Run context</h2>
        {run.incident ? (
          <div className="mt-4 rounded-lg border border-accent/20 bg-accent/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-wider text-accent">
              Correlated Incident
            </p>
            <Link
              className="mt-2 inline-block text-sm text-slate-100 hover:text-accent"
              to={`/incidents/${run.incident.id}`}
            >
              {run.incident.incident_number} · {run.incident.title}
            </Link>
            <p className="mt-2 text-xs text-muted">
              The run records the controlled test; the Incident records
              evidence-based correlation.
            </p>
          </div>
        ) : null}
        <dl className="mt-4 grid gap-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-muted">Started</dt>
            <dd className="mt-1 text-slate-300">
              {formatDateTime(run.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Finished</dt>
            <dd className="mt-1 text-slate-300">
              {formatDateTime(run.finished_at)}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-muted">Affected lab assets</dt>
            <dd className="mt-1 text-slate-300">{run.targets.join(", ")}</dd>
          </div>
        </dl>
        {run.alerts.length ? (
          <div className="mt-5 border-t border-line pt-4">
            <p className="text-[10px] uppercase tracking-wider text-muted">
              Attributed alerts
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {run.alerts.map((alert) => (
                <Link
                  className="rounded-md border border-line bg-black/10 px-3 py-2 font-mono text-[10px] text-accent hover:border-accent/30"
                  key={alert.id}
                  to={`/alerts/${alert.id}`}
                >
                  {alert.rule_id} · {alert.title}
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
