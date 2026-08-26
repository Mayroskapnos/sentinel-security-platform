import type { IncidentFilters } from "../types/core";

function positiveInteger(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function incidentFiltersFromSearchParams(
  searchParams: URLSearchParams,
): IncidentFilters {
  return {
    severity:
      (searchParams.get("severity") as IncidentFilters["severity"]) ||
      undefined,
    status:
      (searchParams.get("status") as IncidentFilters["status"]) || undefined,
    asset_id: searchParams.get("asset_id") || undefined,
    confidence_min: searchParams.get("confidence_min")
      ? Number(searchParams.get("confidence_min"))
      : undefined,
    search: searchParams.get("search") || undefined,
    page: positiveInteger(searchParams.get("page")),
    page_size: 20,
  };
}

export function incidentConfidenceLabel(score: number) {
  if (score >= 80) return "High";
  if (score >= 50) return "Moderate";
  return "Low";
}
