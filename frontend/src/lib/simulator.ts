import type { ScenarioRunStatus } from "../types/core";

export type DetectionOutcome =
  "observed" | "awaiting_observation" | "expected_not_observed";

export function detectionOutcome(
  observed: boolean,
  runStatus: ScenarioRunStatus,
): DetectionOutcome {
  if (observed) return "observed";
  return runStatus === "pending" || runStatus === "running"
    ? "awaiting_observation"
    : "expected_not_observed";
}

export function detectionOutcomeLabel(outcome: DetectionOutcome): string {
  if (outcome === "observed") return "Observed";
  if (outcome === "awaiting_observation") return "Awaiting observation";
  return "Expected but not observed";
}

export interface SuppressionAdvisory {
  rule_id: string;
  recommended_retry_at: string;
}

export function suppressionAdvisories(
  result: Record<string, unknown>,
): SuppressionAdvisory[] {
  const value = result.suppression_advisories;
  if (!Array.isArray(value)) return [];
  return value.filter(
    (item): item is SuppressionAdvisory =>
      typeof item === "object" &&
      item !== null &&
      typeof (item as Record<string, unknown>).rule_id === "string" &&
      typeof (item as Record<string, unknown>).recommended_retry_at ===
        "string",
  );
}
