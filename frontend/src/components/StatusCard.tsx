import type { LucideIcon } from "lucide-react";

interface StatusCardProps {
  title: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  state: "healthy" | "degraded" | "loading";
}

const stateStyles = {
  healthy: "bg-emerald-400",
  degraded: "bg-amber-400",
  loading: "bg-slate-500",
};

export function StatusCard({
  detail,
  icon: Icon,
  state,
  title,
  value,
}: StatusCardProps) {
  return (
    <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">
            {title}
          </p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-white">
            {value}
          </p>
        </div>
        <div className="grid size-10 place-items-center rounded-lg border border-line bg-[#0b111a] text-slate-400">
          <Icon className="size-5" strokeWidth={1.7} />
        </div>
      </div>
      <div className="mt-5 flex items-center gap-2 border-t border-line/80 pt-3 text-xs text-muted">
        <span className={`size-1.5 rounded-full ${stateStyles[state]}`} />
        {detail}
      </div>
    </article>
  );
}
