import type { HealthResponse } from "../types/health";
import type {
  Asset,
  AssetFilters,
  DashboardActivity,
  DashboardSummary,
  EventFilters,
  Page,
  SecurityEvent,
} from "../types/core";

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
    parameters as Record<string, string | number | undefined>,
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

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary");
}

export function getDashboardActivity(hours = 72): Promise<DashboardActivity> {
  return request<DashboardActivity>(`/dashboard/activity?hours=${hours}`);
}
