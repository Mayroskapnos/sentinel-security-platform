import {
  CheckCircle2,
  Circle,
  Clock3,
  Crosshair,
  LoaderCircle,
  Play,
  Server,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { PageHeading } from "../components/data/PageHeading";
import { ErrorState, LoadingState } from "../components/data/QueryState";
import {
  useRunScenario,
  useScenarioRuns,
  useScenarios,
  useSimulatorStatus,
} from "../hooks/useCoreData";
import { formatDateTime } from "../lib/format";
import type {
  ScenarioRun,
  ScenarioRunStep,
  ScenarioSummary,
} from "../types/core";

function RunStatus({ status }: { status: ScenarioRun["status"] }) {
  const style =
    status === "completed"
      ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
      : status === "running" || status === "pending"
        ? "border-cyan-400/25 bg-cyan-400/10 text-cyan-300"
        : "border-amber-400/25 bg-amber-400/10 text-amber-300";
  return (
    <span
      className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${style}`}
    >
      {status}
    </span>
  );
}

function StepIcon({ step }: { step: ScenarioRunStep }) {
  if (step.status === "completed")
    return <CheckCircle2 className="size-4 text-emerald-400" />;
  if (step.status === "running")
    return <LoaderCircle className="size-4 animate-spin text-accent" />;
  if (["failed", "cancelled"].includes(step.status))
    return <XCircle className="size-4 text-amber-400" />;
  return <Circle className="size-4 text-slate-600" />;
}

export function ActiveRun({ run }: { run: ScenarioRun }) {
  return (
    <section className="mt-6 rounded-xl border border-accent/25 bg-accent/[0.045] p-5 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-accent">{run.scenario_id}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-100">
            {run.scenario_name}
          </h2>
          <p className="mt-2 text-xs text-muted">
            Step {run.current_step} / {run.total_steps}
          </p>
        </div>
        <RunStatus status={run.status} />
      </div>
      <div className="mt-5 grid gap-2 lg:grid-cols-2">
        {run.steps.map((step) => (
          <div
            className="flex items-center gap-3 rounded-lg border border-line/80 bg-[#0b111a] px-3 py-2.5"
            key={step.index}
          >
            <StepIcon step={step} />
            <span className="text-xs text-slate-300">{step.name}</span>
          </div>
        ))}
      </div>
      <Link
        className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-accent hover:text-cyan-200"
        to={`/simulator/runs/${run.id}`}
      >
        Open live run detail
        <Crosshair className="size-3.5" />
      </Link>
    </section>
  );
}

export function ScenarioCard({
  disabled,
  onRun,
  scenario,
}: {
  disabled: boolean;
  onRun: (scenario: ScenarioSummary) => void;
  scenario: ScenarioSummary;
}) {
  return (
    <article className="flex flex-col rounded-xl border border-line bg-panel p-5 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-accent">{scenario.id}</p>
          <h2 className="mt-2 text-base font-semibold text-slate-100">
            {scenario.name}
          </h2>
        </div>
        <span className="rounded-md border border-emerald-400/20 bg-emerald-400/[0.08] px-2 py-1 text-[10px] uppercase tracking-wider text-emerald-300">
          {scenario.risk} risk
        </span>
      </div>
      <p className="mt-3 flex-1 text-xs leading-5 text-muted">
        {scenario.description}
      </p>
      <div className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
        <div>
          <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-600">
            <Clock3 className="size-3" /> Estimated
          </p>
          <p className="mt-1 text-xs text-slate-300">
            {scenario.estimated_seconds} seconds
          </p>
        </div>
        <div>
          <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-600">
            <Server className="size-3" /> Lab assets
          </p>
          <p className="mt-1 text-xs text-slate-300">
            {scenario.targets.join(", ")}
          </p>
        </div>
      </div>
      <div className="mt-4">
        <p className="text-[10px] uppercase tracking-wider text-slate-600">
          Expected detections
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {scenario.expected_detections.map((rule) => (
            <span
              className="rounded border border-line bg-black/15 px-2 py-1 font-mono text-[10px] text-slate-400"
              key={rule}
            >
              {rule}
            </span>
          ))}
        </div>
      </div>
      <button
        className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-md border border-accent/30 bg-accent/10 text-xs font-semibold text-accent transition-colors hover:bg-accent/15 disabled:cursor-not-allowed disabled:border-line disabled:bg-transparent disabled:text-slate-600"
        disabled={disabled}
        onClick={() => onRun(scenario)}
        type="button"
      >
        <Play className="size-3.5" /> Run scenario
      </button>
    </article>
  );
}

export function RunConfirmation({
  onCancel,
  onConfirm,
  pending,
  scenario,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  pending: boolean;
  scenario: ScenarioSummary;
}) {
  return (
    <div
      aria-labelledby="run-confirmation-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
    >
      <div className="w-full max-w-lg rounded-xl border border-line bg-[#101722] p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-accent">{scenario.id}</p>
            <h2
              className="mt-1 text-lg font-semibold text-slate-100"
              id="run-confirmation-title"
            >
              Run {scenario.name}?
            </h2>
          </div>
          <button
            aria-label="Close confirmation"
            className="text-muted hover:text-white"
            onClick={onCancel}
            type="button"
          >
            <X className="size-5" />
          </button>
        </div>
        <dl className="mt-6 grid gap-3 rounded-lg border border-line bg-black/10 p-4 text-xs sm:grid-cols-3">
          <div>
            <dt className="text-muted">Targets</dt>
            <dd className="mt-1 text-slate-200">Corporate Lab only</dd>
          </div>
          <div>
            <dt className="text-muted">Duration</dt>
            <dd className="mt-1 text-slate-200">
              ~{scenario.estimated_seconds}s
            </dd>
          </div>
          <div>
            <dt className="text-muted">Expected</dt>
            <dd className="mt-1 text-slate-200">
              {scenario.expected_detections.length} detections
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-5 text-muted">
          The run executes predefined actions only. Custom and external targets
          are not supported.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            className="h-10 rounded-md border border-line px-4 text-xs text-slate-300 hover:bg-white/[0.04]"
            disabled={pending}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-60"
            disabled={pending}
            onClick={onConfirm}
            type="button"
          >
            {pending ? <LoaderCircle className="size-4 animate-spin" /> : null}
            Run
          </button>
        </div>
      </div>
    </div>
  );
}

export function SimulatorPage() {
  const scenarios = useScenarios();
  const simulator = useSimulatorStatus();
  const runs = useScenarioRuns();
  const mutation = useRunScenario();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<ScenarioSummary | null>(null);

  if (scenarios.isLoading || simulator.isLoading) {
    return <LoadingState label="Loading controlled scenarios" />;
  }
  if (
    scenarios.isError ||
    simulator.isError ||
    !scenarios.data ||
    !simulator.data
  ) {
    return <ErrorState error={scenarios.error ?? simulator.error} />;
  }

  async function confirmRun() {
    if (!selected) return;
    const run = await mutation.mutateAsync(selected.id);
    setSelected(null);
    void navigate(`/simulator/runs/${run.id}`);
  }

  const executionDisabled =
    !simulator.data.enabled ||
    !simulator.data.available ||
    simulator.data.state === "running";

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeading
        actions={
          <span className="rounded-md border border-line bg-panel px-3 py-2 text-xs text-slate-300">
            {simulator.data.state === "running"
              ? `Running ${simulator.data.active_run?.scenario_id ?? "scenario"}`
              : simulator.data.message}
          </span>
        }
        description="Run code-reviewed Purple Team validations against real services in the isolated Corporate Lab."
        eyebrow="Security control validation"
        title="Attack Simulator"
      />

      <div className="mt-6 flex items-start gap-3 rounded-lg border border-accent/20 bg-accent/[0.05] p-4">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-accent" />
        <p className="text-xs leading-5 text-slate-300">
          SENTINEL simulations operate only inside the isolated Corporate Lab.
          External and custom targets are not supported.
        </p>
      </div>

      {simulator.data.active_run ? (
        <ActiveRun run={simulator.data.active_run} />
      ) : null}

      {mutation.isError ? (
        <div className="mt-5 rounded-lg border border-amber-400/20 bg-amber-400/[0.06] p-3 text-xs text-amber-200">
          {mutation.error.message}
        </div>
      ) : null}

      <section className="mt-8">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Built-in scenarios
          </h2>
          <p className="mt-1 text-xs text-muted">
            Declarative definitions with fixed actions, targets, and safety
            limits
          </p>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {scenarios.data.map((scenario) => (
            <ScenarioCard
              disabled={executionDisabled}
              key={scenario.id}
              onRun={setSelected}
              scenario={scenario}
            />
          ))}
        </div>
      </section>

      <section className="mt-8 overflow-hidden rounded-xl border border-line bg-panel shadow-panel">
        <div className="border-b border-line p-5">
          <h2 className="text-sm font-semibold text-slate-100">Run history</h2>
          <p className="mt-1 text-xs text-muted">
            Persistent execution and observed telemetry results
          </p>
        </div>
        {!runs.data?.items.length ? (
          <p className="p-8 text-center text-xs text-muted">
            No controlled scenarios have been run yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left">
              <thead className="border-b border-line bg-black/10 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Run</th>
                  <th className="px-4 py-3 font-medium">Scenario</th>
                  <th className="px-4 py-3 font-medium">Started</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Events</th>
                  <th className="px-4 py-3 font-medium">Alerts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {runs.data.items.map((run) => (
                  <tr className="hover:bg-white/[0.025]" key={run.id}>
                    <td className="px-4 py-3 font-mono text-[11px] text-accent">
                      <Link to={`/simulator/runs/${run.id}`}>
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {run.scenario_id} · {run.scenario_name}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-muted">
                      {formatDateTime(run.started_at ?? run.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <RunStatus status={run.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {run.event_count}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {run.alert_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected ? (
        <RunConfirmation
          onCancel={() => setSelected(null)}
          onConfirm={() => void confirmRun()}
          pending={mutation.isPending}
          scenario={selected}
        />
      ) : null}
    </div>
  );
}
