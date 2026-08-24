import type { HealthResponse } from "../types/health";

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

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}
