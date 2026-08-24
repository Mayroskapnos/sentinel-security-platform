import { LoaderCircle } from "lucide-react";

interface HealthBadgeProps {
  isLoading: boolean;
  isHealthy: boolean;
}

export function HealthBadge({ isLoading, isHealthy }: HealthBadgeProps) {
  const label = isLoading
    ? "Checking system"
    : isHealthy
      ? "System healthy"
      : "System degraded";

  return (
    <div
      className="flex items-center gap-2 rounded-full border border-line bg-panel/80 px-3 py-1.5 text-xs font-medium text-slate-300"
      role="status"
    >
      {isLoading ? (
        <LoaderCircle className="size-3.5 animate-spin text-muted" />
      ) : (
        <span
          className={`size-2 rounded-full ${
            isHealthy
              ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]"
              : "bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.6)]"
          }`}
        />
      )}
      {label}
    </div>
  );
}
