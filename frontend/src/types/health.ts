export type ComponentStatus = "healthy" | "unavailable";

export interface ComponentHealth {
  status: ComponentStatus;
  latency_ms: number | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  environment: string;
  checks: Record<string, ComponentHealth>;
}
