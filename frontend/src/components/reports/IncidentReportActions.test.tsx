import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { getIncidentReportUrl } from "../../api/client";
import { IncidentReportActions } from "./IncidentReportActions";

describe("Incident report actions", () => {
  it("defaults to evidence-only PDF and HTML reports", () => {
    const markup = renderToStaticMarkup(
      <IncidentReportActions incidentId="incident/unsafe" />,
    );

    expect(markup).toContain("Download PDF");
    expect(markup).toContain("Download HTML");
    expect(markup).toContain("include_ai=false");
    expect(markup).toContain("non-authoritative");
    expect(markup).not.toContain('checked=""');
  });

  it("constructs scoped report URLs with an explicit AI opt-in", () => {
    expect(getIncidentReportUrl("abc/123", "pdf", true)).toBe(
      "/api/v1/incidents/abc%2F123/report?format=pdf&amp;include_ai=true".replace(
        "&amp;",
        "&",
      ),
    );
  });
});
