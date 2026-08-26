import type { HealthResponse } from "../types/health";
import type {
  Alert,
  AlertDetail,
  AlertFilters,
  Asset,
  AssetFilters,
  DashboardActivity,
  DashboardSummary,
  DetectionRule,
  DetectionRuleFilters,
  EventFilters,
  LabStatus,
  NetworkTopology,
  Page,
  SecurityEvent,
  ScenarioDetail,
  ScenarioRun,
  ScenarioSummary,
  SimulatorStatus,
  TopologyParameters,
} from "../types/core";
import { parseNetworkTopology } from "../lib/network";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";

interface StructuredApiError {
  error?: {
    code?: string;
    message?: string;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "API_ERROR",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("Unable to reach the SENTINEL API.", 0, "NETWORK_ERROR");
  }

  if (!response.ok) {
    const body = (await response
      .json()
      .catch(() => ({}))) as StructuredApiError;
    throw new ApiError(
      body.error?.message ?? `The API returned status ${response.status}.`,
      response.status,
      body.error?.code,
    );
  }

  return (await response.json()) as T;
}

function queryString<T extends object>(parameters: T): string {
  const query = new URLSearchParams();
  Object.entries(
    parameters as Record<string, string | number | boolean | undefined>,
  ).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getLabStatus(): Promise<LabStatus> {
  return request<LabStatus>("/lab/status");
}

export function getSimulatorStatus(): Promise<SimulatorStatus> {
  return request<SimulatorStatus>("/simulator/status");
}

export function getScenarios(): Promise<ScenarioSummary[]> {
  return request<ScenarioSummary[]>("/simulator/scenarios");
}

export function getScenario(scenarioId: string): Promise<ScenarioDetail> {
  return request<ScenarioDetail>(`/simulator/scenarios/${scenarioId}`);
}

export function runScenario(scenarioId: string): Promise<ScenarioRun> {
  return request<ScenarioRun>(`/simulator/run/${scenarioId}`, {
    method: "POST",
  });
}

export function getScenarioRuns(
  page = 1,
  pageSize = 20,
): Promise<Page<ScenarioRun>> {
  return request<Page<ScenarioRun>>(
    `/simulator/runs?page=${page}&page_size=${pageSize}`,
  );
}

export function getScenarioRun(runId: string): Promise<ScenarioRun> {
  return request<ScenarioRun>(`/simulator/runs/${runId}`);
}

export function cancelScenarioRun(runId: string): Promise<ScenarioRun> {
  return request<ScenarioRun>(`/simulator/runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function getAssets(filters: AssetFilters): Promise<Page<Asset>> {
  return request<Page<Asset>>(`/assets${queryString(filters)}`);
}

export function getAsset(assetId: string): Promise<Asset> {
  return request<Asset>(`/assets/${assetId}`);
}

export function getEvents(filters: EventFilters): Promise<Page<SecurityEvent>> {
  return request<Page<SecurityEvent>>(`/events${queryString(filters)}`);
}

export function getEvent(eventId: string): Promise<SecurityEvent> {
  return request<SecurityEvent>(`/events/${eventId}`);
}

export function getAlerts(filters: AlertFilters): Promise<Page<Alert>> {
  return request<Page<Alert>>(`/alerts${queryString(filters)}`);
}

export function getAlert(alertId: string): Promise<AlertDetail> {
  return request<AlertDetail>(`/alerts/${alertId}`);
}

export function updateAlert(
  alertId: string,
  status: Alert["status"],
): Promise<Alert> {
  return request<Alert>(`/alerts/${alertId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export function getRules(
  filters: DetectionRuleFilters,
): Promise<Page<DetectionRule>> {
  return request<Page<DetectionRule>>(`/rules${queryString(filters)}`);
}

export function getRule(ruleId: string): Promise<DetectionRule> {
  return request<DetectionRule>(`/rules/${ruleId}`);
}

export function updateRule(
  ruleId: string,
  enabled: boolean,
): Promise<DetectionRule> {
  return request<DetectionRule>(`/rules/${ruleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary");
}

export function getDashboardActivity(hours = 72): Promise<DashboardActivity> {
  return request<DashboardActivity>(`/dashboard/activity?hours=${hours}`);
}

export async function getNetworkTopology(
  parameters: TopologyParameters,
): Promise<NetworkTopology> {
  const response = await request<unknown>(
    `/network/topology${queryString(parameters)}`,
  );
  return parseNetworkTopology(response);
}
