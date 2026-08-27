export type ComponentStatus = "healthy" | "unavailable";

export interface ComponentHealth {
  status: ComponentStatus;
  latency_ms: number | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  build_sha: string | null;
  build_time: string | null;
  environment: string;
  checks: Record<string, ComponentHealth>;
}
