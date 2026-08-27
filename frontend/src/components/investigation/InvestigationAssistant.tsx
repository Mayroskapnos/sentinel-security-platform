import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  ExternalLink,
  MessageSquareText,
  RefreshCw,
  ShieldQuestion,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useAskInvestigationQuestion,
  useAssistantStatus,
  useGenerateInvestigationAnalysis,
  useInvestigationMessages,
  useLatestInvestigationAnalysis,
} from "../../hooks/useCoreData";
import { formatDateTime, humanize } from "../../lib/format";
import type {
  AssistantStatus,
  InvestigationAnalysis,
  InvestigationMessage,
} from "../../types/investigation";

function errorMessage(error: unknown): string | null {
  return error instanceof Error ? error.message : null;
}

function evidenceTarget(reference: string): string | null {
  const separator = reference.indexOf(":");
  const kind = reference.slice(0, separator);
  const id = reference.slice(separator + 1);
  if (!id) return null;
  if (kind === "incident") return `/incidents/${id}`;
  if (kind === "alert") return `/alerts/${id}`;
  if (kind === "asset") return `/assets/${id}`;
  if (kind === "event") return `/events?event=${id}`;
  if (kind === "connection") return "/attack-map?window=all";
  if (kind === "scenario") return `/simulator/runs/${id}`;
  return null;
}

export function EvidenceChips({
  catalog,
  references,
}: {
  catalog: Record<string, string>;
  references: string[];
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {references.map((reference) => {
        const target = evidenceTarget(reference);
        const label = catalog[reference] ?? reference;
        const className =
          "inline-flex items-center gap-1 rounded border border-accent/20 " +
          "bg-accent/[0.06] px-2 py-1 font-mono text-[9px] text-accent " +
          "hover:border-accent/40";
        return target ? (
          <Link className={className} key={reference} to={target}>
            {label} <ExternalLink className="size-2.5" />
          </Link>
        ) : (
          <span className={className} key={reference}>
            {label}
          </span>
        );
      })}
    </div>
  );
}

interface AssistantPanelProps {
  status: AssistantStatus | null;
  analysis: InvestigationAnalysis | null;
  messages: InvestigationMessage[];
  loadingStatus?: boolean;
  generating?: boolean;
  asking?: boolean;
  error?: string | null;
  onGenerate?: () => void;
  onAsk?: (question: string) => void;
}

export function InvestigationAssistantPanel({
  status,
  analysis,
  messages,
  loadingStatus = false,
  generating = false,
  asking = false,
  error,
  onGenerate,
  onAsk,
}: AssistantPanelProps) {
  const [question, setQuestion] = useState("");
  const active =
    analysis?.status === "pending" || analysis?.status === "running";
  const canGenerate = status?.enabled && !active && !generating;
  const catalog = analysis?.evidence_catalog ?? {};

  const submitQuestion = () => {
    const normalized = question.trim();
    if (!normalized || asking || !onAsk) return;
    onAsk(normalized);
    setQuestion("");
  };

  return (
    <section
      aria-label="Investigation Assistant"
      className="mt-6 rounded-xl border border-violet-400/20 bg-panel p-5 shadow-panel"
    >
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <div className="flex items-center gap-2">
            <BrainCircuit className="size-4 text-violet-300" />
            <h2 className="text-sm font-semibold text-slate-100">
              Investigation Assistant
            </h2>
            <span className="rounded border border-violet-400/20 bg-violet-400/[0.06] px-2 py-0.5 text-[9px] uppercase tracking-wider text-violet-300">
              AI-assisted
            </span>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted">
            Generated from bounded SENTINEL evidence. Verify before taking
            action.
          </p>
          {status ? (
            <p className="mt-1 font-mono text-[10px] text-slate-500">
              {status.provider_label}
              {status.model ? ` · ${status.model}` : ""}
            </p>
          ) : null}
        </div>
        {status?.enabled ? (
          <button
            className="inline-flex items-center justify-center gap-2 rounded-md border border-violet-400/30 bg-violet-400/[0.08] px-3 py-2 text-xs text-violet-200 hover:bg-violet-400/[0.14] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canGenerate}
            onClick={onGenerate}
            type="button"
          >
            {active || generating ? (
              <RefreshCw className="size-3.5 animate-spin" />
            ) : (
              <Sparkles className="size-3.5" />
            )}
            {analysis
              ? "Regenerate Analysis"
              : "Generate Investigation Analysis"}
          </button>
        ) : null}
      </div>

      {loadingStatus ? (
        <p className="mt-5 rounded-lg border border-line bg-[#0b111a] p-4 text-xs text-muted">
          Loading optional assistant status...
        </p>
      ) : null}

      {!loadingStatus && (!status || !status.enabled) ? (
        <div className="mt-5 rounded-lg border border-line bg-[#0b111a] p-4">
          <p className="text-xs text-slate-300">
            {status?.message ??
              "Investigation Assistant status is unavailable."}
          </p>
          <p className="mt-2 text-xs text-muted">
            Deterministic Incident analysis remains available above.
          </p>
        </div>
      ) : null}

      {status?.external ? (
        <p className="mt-4 rounded-md border border-amber-400/15 bg-amber-400/[0.04] p-3 text-[10px] leading-4 text-amber-200/80">
          Selected, redacted Incident evidence is sent to the configured
          external provider.
        </p>
      ) : null}
      {status?.mode === "mock" ? (
        <p className="mt-4 rounded-md border border-line bg-[#0b111a] p-3 text-[10px] text-slate-400">
          Mock Investigation Provider runs locally and sends no data externally.
        </p>
      ) : null}

      {error ? (
        <div className="mt-4 flex gap-2 rounded-lg border border-red-400/20 bg-red-400/[0.05] p-3 text-xs text-red-200">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {error}
        </div>
      ) : null}

      {active ? (
        <div className="mt-5 rounded-lg border border-violet-400/20 bg-violet-400/[0.04] p-4">
          <div className="flex items-center gap-2 text-xs text-violet-200">
            <RefreshCw className="size-3.5 animate-spin" /> Analyzing Incident
            evidence...
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[10px] text-slate-500">
            <span>Preparing evidence</span>
            <span>Reviewing alert relationships</span>
            <span>Generating analyst summary</span>
          </div>
        </div>
      ) : null}

      {analysis?.status === "failed" ? (
        <div className="mt-5 rounded-lg border border-red-400/20 bg-red-400/[0.05] p-4">
          <p className="text-xs font-medium text-red-200">Analysis failed</p>
          <p className="mt-2 text-xs text-red-200/70">
            {analysis.error_message ??
              "The provider did not return a valid analysis."}
          </p>
          <p className="mt-2 text-[10px] text-muted">
            The Incident and its deterministic evidence were not changed.
          </p>
        </div>
      ) : null}

      {analysis?.status === "completed" && analysis.output ? (
        <div className="mt-5 space-y-5">
          <div className="flex flex-wrap items-center gap-2 border-b border-line pb-4 text-[10px]">
            <span className="inline-flex items-center gap-1 text-slate-400">
              <Clock3 className="size-3" /> Generated{" "}
              {formatDateTime(analysis.completed_at)}
            </span>
            <span
              className={
                analysis.is_stale
                  ? "rounded border border-amber-400/25 bg-amber-400/[0.06] px-2 py-1 text-amber-200"
                  : "rounded border border-emerald-400/20 bg-emerald-400/[0.05] px-2 py-1 text-emerald-300"
              }
            >
              Evidence version: {analysis.is_stale ? "outdated" : "current"}
            </span>
            <span className="text-slate-600">
              {analysis.provider_label} · {analysis.model}
            </span>
          </div>

          {analysis.is_stale ? (
            <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.05] p-3 text-xs text-amber-100/80">
              Incident evidence has changed since this analysis. Regenerate to
              analyze the latest evidence.
            </div>
          ) : null}

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-200">
              Executive Summary
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {analysis.output.executive_summary}
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-200">
              What SENTINEL Observed
            </h3>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {analysis.output.observations.map((observation, index) => (
                <article
                  className="rounded-lg border border-line bg-[#0b111a] p-3"
                  key={index}
                >
                  <p className="text-xs leading-5 text-slate-300">
                    {observation.statement}
                  </p>
                  <EvidenceChips
                    catalog={catalog}
                    references={observation.evidence_refs}
                  />
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-line bg-[#0b111a] p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-200">
              Why the Alerts Were Correlated
            </h3>
            <p className="mt-2 text-xs leading-5 text-slate-300">
              {analysis.output.correlation_explanation.statement}
            </p>
            <EvidenceChips
              catalog={catalog}
              references={analysis.output.correlation_explanation.evidence_refs}
            />
          </div>

          {analysis.output.key_assets.length ? (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-200">
                Key Assets
              </h3>
              <div className="mt-3 flex flex-wrap gap-3">
                {analysis.output.key_assets.map((asset) => (
                  <div
                    className="rounded-lg border border-line bg-[#0b111a] p-3"
                    key={asset.asset_ref}
                  >
                    <EvidenceChips
                      catalog={catalog}
                      references={[asset.asset_ref]}
                    />
                    <p className="mt-2 max-w-md text-xs leading-5 text-slate-400">
                      {asset.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid gap-5 xl:grid-cols-2">
            <div>
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-200">
                <ShieldQuestion className="size-3.5" /> Uncertainties
              </h3>
              <div className="mt-3 space-y-3">
                {analysis.output.uncertainties.map((item, index) => (
                  <article
                    className="rounded-lg border border-line bg-[#0b111a] p-3"
                    key={index}
                  >
                    <p className="text-xs leading-5 text-slate-300">
                      {item.statement}
                    </p>
                    <p className="mt-2 text-[10px] leading-4 text-muted">
                      {item.reason}
                    </p>
                    <EvidenceChips
                      catalog={catalog}
                      references={item.evidence_refs}
                    />
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-200">
                <CheckCircle2 className="size-3.5" /> Investigation Priorities
              </h3>
              <div className="mt-3 space-y-3">
                {analysis.output.recommended_actions.map((item, index) => (
                  <article
                    className="rounded-lg border border-line bg-[#0b111a] p-3"
                    key={index}
                  >
                    <span className="font-mono text-[9px] uppercase text-accent">
                      {humanize(item.priority)} priority
                    </span>
                    <p className="mt-1 text-xs leading-5 text-slate-300">
                      {item.action}
                    </p>
                    <p className="mt-2 text-[10px] leading-4 text-muted">
                      {item.reason}
                    </p>
                    <EvidenceChips
                      catalog={catalog}
                      references={item.evidence_refs}
                    />
                  </article>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {status?.enabled ? (
        <div className="mt-6 border-t border-line pt-5">
          <div className="flex items-center gap-2">
            <MessageSquareText className="size-4 text-violet-300" />
            <h3 className="text-sm font-semibold text-slate-100">
              Incident Q&amp;A
            </h3>
          </div>
          <p className="mt-2 text-xs text-muted">
            Answers are limited to the selected Incident and cannot execute
            actions.
          </p>
          {messages.length ? (
            <div className="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1">
              {messages.map((message) => (
                <div
                  className={
                    message.role === "assistant"
                      ? "rounded-lg border border-violet-400/15 bg-violet-400/[0.04] p-3"
                      : "ml-8 rounded-lg border border-line bg-[#0b111a] p-3"
                  }
                  key={message.id}
                >
                  <p className="text-[9px] uppercase tracking-wider text-slate-500">
                    {message.role === "assistant" ? "Assistant" : "Analyst"}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-300">
                    {message.content}
                  </p>
                  {message.role === "assistant" ? (
                    <EvidenceChips
                      catalog={catalog}
                      references={message.evidence_refs}
                    />
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex gap-2">
            <input
              aria-label="Ask about this Incident"
              className="min-w-0 flex-1 rounded-md border border-line bg-[#0b111a] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-violet-400/40"
              maxLength={500}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitQuestion();
              }}
              placeholder="Ask about this Incident..."
              value={question}
            />
            <button
              className="rounded-md border border-violet-400/25 px-3 py-2 text-xs text-violet-200 disabled:opacity-50"
              disabled={!question.trim() || asking}
              onClick={submitQuestion}
              type="button"
            >
              {asking ? "Reviewing..." : "Ask"}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function InvestigationAssistant({ incidentId }: { incidentId: string }) {
  const status = useAssistantStatus();
  const enabled = status.data?.enabled === true;
  const analysis = useLatestInvestigationAnalysis(incidentId, enabled);
  const messages = useInvestigationMessages(incidentId, enabled);
  const generate = useGenerateInvestigationAnalysis();
  const ask = useAskInvestigationQuestion();

  return (
    <InvestigationAssistantPanel
      analysis={analysis.data ?? null}
      asking={ask.isPending}
      error={
        errorMessage(generate.error) ??
        errorMessage(analysis.error) ??
        errorMessage(ask.error)
      }
      generating={generate.isPending}
      loadingStatus={status.isLoading}
      messages={messages.data ?? []}
      onAsk={(question) => ask.mutate({ incidentId, question })}
      onGenerate={() => generate.mutate(incidentId)}
      status={status.data ?? null}
    />
  );
}
