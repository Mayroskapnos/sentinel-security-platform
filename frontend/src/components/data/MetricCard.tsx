import type { LucideIcon } from "lucide-react";

export function MetricCard({
  detail,
  icon: Icon,
  label,
  value,
}: {
  detail: string;
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <article className="rounded-xl border border-line bg-panel p-5 shadow-panel">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            {label}
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-white">
            {value.toLocaleString()}
          </p>
        </div>
        <div className="grid size-10 place-items-center rounded-lg border border-line bg-[#0b111a] text-accent">
          <Icon className="size-5" strokeWidth={1.7} />
        </div>
      </div>
      <p className="mt-5 border-t border-line/80 pt-3 text-xs text-muted">
        {detail}
      </p>
    </article>
  );
}
