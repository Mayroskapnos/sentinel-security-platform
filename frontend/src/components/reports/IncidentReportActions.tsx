import { FileCode2, FileDown } from "lucide-react";
import { useState } from "react";

import { getIncidentReportUrl } from "../../api/client";

export function IncidentReportActions({ incidentId }: { incidentId: string }) {
  const [includeAi, setIncludeAi] = useState(false);

  return (
    <section className="rounded-lg border border-line bg-black/10 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <a
          className="inline-flex items-center gap-2 rounded-md border border-accent/25 bg-accent/[0.06] px-3 py-2 text-xs text-accent hover:bg-accent/10"
          download
          href={getIncidentReportUrl(incidentId, "pdf", includeAi)}
        >
          <FileDown className="size-3.5" /> Download PDF
        </a>
        <a
          className="inline-flex items-center gap-2 rounded-md border border-line bg-white/[0.025] px-3 py-2 text-xs text-slate-300 hover:text-white"
          download
          href={getIncidentReportUrl(incidentId, "html", includeAi)}
        >
          <FileCode2 className="size-3.5" /> Download HTML
        </a>
      </div>
      <label className="mt-3 flex cursor-pointer items-start gap-2 text-[11px] leading-4 text-muted">
        <input
          checked={includeAi}
          className="mt-0.5 size-3.5 accent-emerald-400"
          onChange={(event) => setIncludeAi(event.target.checked)}
          type="checkbox"
        />
        <span>
          Include the latest completed AI analysis as a separate,
          non-authoritative section. Deterministic evidence is always included.
        </span>
      </label>
    </section>
  );
}
