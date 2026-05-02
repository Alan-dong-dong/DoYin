export interface HealthServiceState {
  status: "ok" | "error";
  ready: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  api: HealthServiceState;
  database: HealthServiceState;
}

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_HEALTH_PATH = "/api/health";

export function getHealthEndpoint(): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const healthPath = import.meta.env.VITE_API_HEALTH_PATH ?? DEFAULT_HEALTH_PATH;
  return new URL(healthPath, baseUrl).toString();
}

export async function requestHealth(): Promise<{
  endpoint: string;
  httpStatus: number;
  payload: HealthResponse | null;
}> {
  const endpoint = getHealthEndpoint();
  const response = await fetch(endpoint, {
    headers: {
      Accept: "application/json",
    },
  });

  let payload: HealthResponse | null = null;
  try {
    payload = (await response.json()) as HealthResponse;
  } catch {
    payload = null;
  }

  return {
    endpoint,
    httpStatus: response.status,
    payload,
  };
}

