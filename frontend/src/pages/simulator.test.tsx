import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { ScenarioRun, ScenarioSummary } from "../types/core";
import {
  detectionOutcome,
  detectionOutcomeLabel,
  suppressionAdvisories,
} from "../lib/simulator";
import { ActiveRun, RunConfirmation, ScenarioCard } from "./SimulatorPage";

const scenario: ScenarioSummary = {
  id: "SCN-005",
  name: "Multi-Stage Enterprise Security Exercise",
  description: "Controlled Corporate Lab validation.",
  risk: "low",
  estimated_seconds: 48,
  targets: ["employee-01", "admin-server", "database"],
  expected_detections: ["DET-SSH-001", "DET-DB-001"],
  step_count: 5,
};

const activeRun: ScenarioRun = {
  id: "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d",
  scenario_id: scenario.id,
  scenario_name: scenario.name,
  status: "running",
  started_at: "2026-08-25T12:00:00Z",
  finished_at: null,
  current_step: 1,
  total_steps: 2,
  requested_by: "local-user",
  steps: [
    {
      index: 1,
      name: "Credential activity",
      action: "controlled_failed_authentication",
      status: "running",
      started_at: "2026-08-25T12:00:00Z",
      finished_at: null,
      message: "Action started.",
    },
    {
      index: 2,
      name: "Database access",
      action: "controlled_database_connection",
      status: "pending",
      started_at: null,
      finished_at: null,
      message: null,
    },
  ],
  expected_detections: scenario.expected_detections,
  targets: scenario.targets,
  result: {},
  error_message: null,
  created_at: "2026-08-25T12:00:00Z",
  updated_at: "2026-08-25T12:00:00Z",
  event_count: 0,
  alert_count: 0,
  detections: [],
  alerts: [],
  incident: null,
};

describe("Attack Simulator presentation", () => {
  it("renders scenario safety metadata and expected detections", () => {
    const markup = renderToStaticMarkup(
      <ScenarioCard
        disabled={false}
        onRun={() => undefined}
        scenario={scenario}
      />,
    );

    expect(markup).toContain("SCN-005");
    expect(markup).toContain("low risk");
    expect(markup).toContain("DET-SSH-001");
    expect(markup).toContain("Run scenario");
  });

  it("disables scenario execution when the simulator is unavailable", () => {
    const markup = renderToStaticMarkup(
      <ScenarioCard
        disabled={true}
        onRun={() => undefined}
        scenario={scenario}
      />,
    );

    expect(markup).toContain("disabled");
    expect(markup).toContain("Run scenario");
  });

  it("renders concise Corporate Lab-only confirmation", () => {
    const markup = renderToStaticMarkup(
      <RunConfirmation
        onCancel={() => undefined}
        onConfirm={() => undefined}
        pending={false}
        scenario={scenario}
      />,
    );

    expect(markup).toContain("Corporate Lab only");
    expect(markup).toContain("Custom and external targets are not supported");
  });

  it("renders persisted active step state and honest outcome labels", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <ActiveRun run={activeRun} />
      </MemoryRouter>,
    );

    expect(markup).toContain("Step 1 / 2");
    expect(markup).toContain("Credential activity");
  });

  it.each([
    ["running + not observed", false, "running", "Awaiting observation"],
    ["running + observed", true, "running", "Observed"],
    [
      "completed + not observed",
      false,
      "completed",
      "Expected but not observed",
    ],
    ["completed + observed", true, "completed", "Observed"],
  ] as const)("models %s", (_case, observed, status, expected) => {
    expect(detectionOutcomeLabel(detectionOutcome(observed, status))).toBe(
      expected,
    );
  });

  it("keeps suppression retry guidance structured and honest", () => {
    expect(
      suppressionAdvisories({
        suppression_advisories: [
          {
            rule_id: "DET-SSH-001",
            recommended_retry_at: "2026-08-25T12:05:00Z",
          },
        ],
      }),
    ).toEqual([
      {
        rule_id: "DET-SSH-001",
        recommended_retry_at: "2026-08-25T12:05:00Z",
      },
    ]);
    expect(
      suppressionAdvisories({ suppression_advisories: ["invalid"] }),
    ).toEqual([]);
  });
});
