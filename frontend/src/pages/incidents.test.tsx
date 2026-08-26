import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { IncidentStoryItem } from "../types/core";
import {
  incidentConfidenceLabel,
  incidentFiltersFromSearchParams,
} from "../lib/incidents";
import { IncidentStory } from "./IncidentDetailPage";

const story: IncidentStoryItem[] = [
  {
    timestamp: "2026-08-26T10:00:00Z",
    stage: "credential_activity",
    title: "Credential activity observed",
    description: "10 failed SSH authentication events were observed.",
    alert_id: "3dc90e82-759a-4ef1-b60b-24c4e8dd5685",
    rule_id: "DET-SSH-001",
    asset_ids: ["1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d"],
    event_ids: ["52384fa9-ebc1-475e-a1d7-16c8a3a3781a"],
    source_ip: "10.10.50.2",
    destination_ip: "10.10.20.10",
    mitre_technique_id: "T1110",
    mitre_technique_name: "Brute Force",
    network_connection_id: null,
    scenario_step: null,
  },
  {
    timestamp: "2026-08-26T10:00:20Z",
    stage: "database_access",
    title: "Unexpected database connection observed",
    description:
      "An unexpected workstation-to-database connection was observed.",
    alert_id: "9ed3eebd-1dff-490a-a44d-b825437ceeb0",
    rule_id: "DET-DB-001",
    asset_ids: [],
    event_ids: [],
    source_ip: "10.10.20.10",
    destination_ip: "10.10.30.20",
    mitre_technique_id: null,
    mitre_technique_name: null,
    network_connection_id: null,
    scenario_step: null,
  },
];

describe("Incident presentation", () => {
  it("renders chronological, evidence-linked story steps without inventing ATT&CK", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <IncidentStory items={story} />
      </MemoryRouter>,
    );
    expect(markup).toContain("Credential activity observed");
    expect(markup).toContain("DET-SSH-001");
    expect(markup).toContain("/alerts/3dc90e82");
    expect(markup).toContain("/assets/1a7a65a3");
    expect(markup).toContain("event=52384fa9");
    expect(markup).toContain("T1110 · Brute Force");
    expect(markup).toContain("No precise ATT&amp;CK mapping asserted");
  });

  it("distinguishes deterministic confidence labels from severity", () => {
    expect(incidentConfidenceLabel(49)).toBe("Low");
    expect(incidentConfidenceLabel(50)).toBe("Moderate");
    expect(incidentConfidenceLabel(80)).toBe("High");
  });

  it("builds server-side incident queue filters from the URL", () => {
    const filters = incidentFiltersFromSearchParams(
      new URLSearchParams(
        "severity=critical&status=investigating&confidence_min=80&" +
          "asset_id=1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d&search=employee&page=3",
      ),
    );
    expect(filters).toEqual({
      severity: "critical",
      status: "investigating",
      asset_id: "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d",
      confidence_min: 80,
      search: "employee",
      page: 3,
      page_size: 20,
    });
  });
});
