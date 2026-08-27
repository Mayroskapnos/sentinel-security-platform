import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type {
  AssistantStatus,
  InvestigationAnalysis,
  InvestigationMessage,
} from "../../types/investigation";
import { InvestigationAssistantPanel } from "./InvestigationAssistant";

const incidentId = "11111111-1111-1111-1111-111111111111";
const alertId = "22222222-2222-2222-2222-222222222222";
const assetId = "33333333-3333-3333-3333-333333333333";
const incidentRef = `incident:${incidentId}`;
const alertRef = `alert:${alertId}`;
const assetRef = `asset:${assetId}`;

const mockStatus: AssistantStatus = {
  enabled: true,
  mode: "mock",
  provider: "mock",
  provider_label: "Mock Investigation Provider",
  model: "sentinel-mock-v1",
  external: false,
  message: "Local mock available.",
};

const disabledStatus: AssistantStatus = {
  enabled: false,
  mode: "disabled",
  provider: null,
  provider_label: "Investigation Assistant",
  model: null,
  external: false,
  message: "AI analysis is not configured for this SENTINEL deployment.",
};

function analysis(
  overrides: Partial<InvestigationAnalysis> = {},
): InvestigationAnalysis {
  return {
    id: "44444444-4444-4444-4444-444444444444",
    incident_id: incidentId,
    status: "completed",
    provider: "mock",
    provider_label: "Mock Investigation Provider",
    model: "sentinel-mock-v1",
    requested_at: "2026-08-26T10:00:00Z",
    started_at: "2026-08-26T10:00:01Z",
    completed_at: "2026-08-26T10:00:02Z",
    analysis_version: "1",
    context_hash: "a".repeat(64),
    is_stale: false,
    input_tokens: null,
    output_tokens: null,
    error_message: null,
    created_at: "2026-08-26T10:00:00Z",
    updated_at: "2026-08-26T10:00:02Z",
    evidence_catalog: {
      [incidentRef]: "INC-TEST",
      [alertRef]: "DET-SSH-001",
      [assetRef]: "employee-01",
    },
    output: {
      executive_summary:
        "SENTINEL correlated bounded evidence. Analyst verification remains required.",
      observations: [
        {
          statement: "Repeated authentication failures were observed.",
          evidence_refs: [alertRef],
        },
      ],
      correlation_explanation: {
        statement: "Shared identity and asset signals grouped these alerts.",
        evidence_refs: [alertRef],
      },
      key_assets: [
        { asset_ref: assetRef, reason: "Affected high-priority asset." },
      ],
      uncertainties: [
        {
          statement: "Authorization intent is unknown.",
          reason: "Intent is not in telemetry.",
          evidence_refs: [incidentRef],
        },
      ],
      recommended_actions: [
        {
          priority: "high",
          action: "Review authentication logs.",
          reason: "Verify whether activity was expected.",
          evidence_refs: [alertRef],
        },
      ],
    },
    ...overrides,
  };
}

function render(
  status: AssistantStatus | null,
  currentAnalysis: InvestigationAnalysis | null,
  messages: InvestigationMessage[] = [],
) {
  return renderToStaticMarkup(
    <MemoryRouter>
      <InvestigationAssistantPanel
        analysis={currentAnalysis}
        messages={messages}
        status={status}
      />
    </MemoryRouter>,
  );
}

describe("Investigation Assistant presentation", () => {
  it("shows a neutral disabled state without treating optional AI as an error", () => {
    const markup = render(disabledStatus, null);
    expect(markup).toContain("AI analysis is not configured");
    expect(markup).toContain(
      "Deterministic Incident analysis remains available above",
    );
    expect(markup).not.toContain("Analysis failed");
  });

  it("shows configured generation and a clearly labeled local mock provider", () => {
    const markup = render(mockStatus, null);
    expect(markup).toContain("Generate Investigation Analysis");
    expect(markup).toContain("AI-assisted");
    expect(markup).toContain("Mock Investigation Provider");
    expect(markup).toContain("sends no data externally");
  });

  it("discloses the external-provider privacy boundary", () => {
    const markup = render(
      {
        ...mockStatus,
        mode: "configured",
        provider: "openai",
        provider_label: "OpenAI",
        model: "configured-model",
        external: true,
      },
      null,
    );
    expect(markup).toContain("Generate Investigation Analysis");
    expect(markup).toContain("sent to the configured external provider");
    expect(markup).not.toContain("Mock Investigation Provider runs locally");
  });

  it("shows the non-percentage analysis loading stages", () => {
    const markup = render(
      mockStatus,
      analysis({ status: "running", completed_at: null, output: null }),
    );
    expect(markup).toContain("Analyzing Incident evidence");
    expect(markup).toContain("Preparing evidence");
    expect(markup).toContain("Reviewing alert relationships");
    expect(markup).not.toContain("%");
  });

  it("renders completed grounded sections, recommendations, and evidence links", () => {
    const markup = render(mockStatus, analysis());
    expect(markup).toContain("Executive Summary");
    expect(markup).toContain("What SENTINEL Observed");
    expect(markup).toContain("Why the Alerts Were Correlated");
    expect(markup).toContain("Uncertainties");
    expect(markup).toContain("Investigation Priorities");
    expect(markup).toContain("Review authentication logs");
    expect(markup).toContain("DET-SSH-001");
    expect(markup).toContain(`/alerts/${alertId}`);
    expect(markup).toContain(`/assets/${assetId}`);
    expect(markup).toContain("Evidence version: current");
  });

  it("warns when persisted analysis is stale", () => {
    const markup = render(mockStatus, analysis({ is_stale: true }));
    expect(markup).toContain("Evidence version: outdated");
    expect(markup).toContain(
      "Incident evidence has changed since this analysis",
    );
    expect(markup).toContain("Regenerate Analysis");
  });

  it("isolates provider failure from deterministic Incident evidence", () => {
    const markup = render(
      mockStatus,
      analysis({
        status: "failed",
        output: null,
        error_message: "The Investigation Assistant timed out.",
      }),
    );
    expect(markup).toContain("Analysis failed");
    expect(markup).toContain("timed out");
    expect(markup).toContain("deterministic evidence were not changed");
  });

  it("renders persisted Q&A with cited Incident evidence", () => {
    const messages: InvestigationMessage[] = [
      {
        id: "55555555-5555-5555-5555-555555555555",
        incident_id: incidentId,
        analysis_id: null,
        reply_to_id: null,
        role: "user",
        content: "Did data exfiltration occur?",
        evidence_refs: [],
        context_hash: "a".repeat(64),
        provider: null,
        model: null,
        created_at: "2026-08-26T10:01:00Z",
      },
      {
        id: "66666666-6666-6666-6666-666666666666",
        incident_id: incidentId,
        analysis_id: null,
        reply_to_id: "55555555-5555-5555-5555-555555555555",
        role: "assistant",
        content: "SENTINEL has no evidence proving data exfiltration.",
        evidence_refs: [incidentRef],
        context_hash: "a".repeat(64),
        provider: "mock",
        model: "sentinel-mock-v1",
        created_at: "2026-08-26T10:01:01Z",
      },
    ];
    const markup = render(mockStatus, analysis(), messages);
    expect(markup).toContain("Incident Q&amp;A");
    expect(markup).toContain("no evidence proving data exfiltration");
    expect(markup).toContain("INC-TEST");
    expect(markup).toContain("cannot execute actions");
  });
});
