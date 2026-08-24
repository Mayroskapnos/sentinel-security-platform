function riskStyle(score: number): string {
  if (score >= 81) return "bg-red-400 text-red-300";
  if (score >= 61) return "bg-orange-400 text-orange-300";
  if (score >= 41) return "bg-amber-400 text-amber-300";
  if (score >= 21) return "bg-sky-400 text-sky-300";
  return "bg-emerald-400 text-emerald-300";
}

export function RiskIndicator({
  score,
  detailed = false,
}: {
  score: number;
  detailed?: boolean;
}) {
  const colors = riskStyle(score).split(" ");
  return (
    <div className={detailed ? "w-full" : "w-28"}>
      <div className="flex items-center justify-between gap-3">
        <span className={`font-mono text-xs font-semibold ${colors[1]}`}>
          {Math.round(score)}
        </span>
        {detailed && (
          <span className="text-[10px] uppercase tracking-wider text-muted">
            of 100
          </span>
        )}
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${colors[0]}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}
