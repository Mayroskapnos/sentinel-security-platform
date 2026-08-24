import type { AssetStatus, EventSeverity } from "../../types/core";
import { humanize } from "../../lib/format";

const severityStyles: Record<EventSeverity, string> = {
  informational: "border-slate-500/25 bg-slate-500/10 text-slate-300",
  low: "border-sky-400/25 bg-sky-400/10 text-sky-300",
  medium: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  high: "border-orange-400/25 bg-orange-400/10 text-orange-300",
  critical: "border-red-400/25 bg-red-400/10 text-red-300",
};

const statusStyles: Record<AssetStatus, string> = {
  online: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  offline: "border-slate-500/25 bg-slate-500/10 text-slate-300",
  warning: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  critical: "border-red-400/25 bg-red-400/10 text-red-300",
  unknown: "border-slate-500/25 bg-slate-500/10 text-slate-300",
};

function BadgeBase({ className, value }: { className: string; value: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] ${className}`}
    >
      {humanize(value)}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: EventSeverity }) {
  return <BadgeBase className={severityStyles[severity]} value={severity} />;
}

export function AssetStatusBadge({ status }: { status: AssetStatus }) {
  return <BadgeBase className={statusStyles[status]} value={status} />;
}

export function EventStatusBadge({ status }: { status: string }) {
  const success = ["success", "allowed", "accepted"].includes(status);
  const failed = ["failed", "denied", "blocked"].includes(status);
  const style = success
    ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
    : failed
      ? "border-red-400/25 bg-red-400/10 text-red-300"
      : "border-slate-500/25 bg-slate-500/10 text-slate-300";
  return <BadgeBase className={style} value={status} />;
}
