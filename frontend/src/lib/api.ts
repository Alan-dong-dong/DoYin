const DEFAULT_API_BASE_URL = "http://localhost:8000";

let unauthorizedHandler: (() => void | Promise<void>) | null = null;

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function buildApiUrl(path: string): string {
  return new URL(path, getApiBaseUrl()).toString();
}

export function resolveBackendUrl(pathOrUrl: string): string {
  return new URL(pathOrUrl, getApiBaseUrl()).toString();
}

export function setUnauthorizedHandler(handler: (() => void | Promise<void>) | null): void {
  unauthorizedHandler = handler;
}

export async function requestJson<T>(
  path: string,
  init: RequestInit & { skipAuthRecovery?: boolean } = {},
): Promise<{
  endpoint: string;
  httpStatus: number;
  payload: T | null;
}> {
  const { skipAuthRecovery = false, ...requestInit } = init;
  const endpoint = buildApiUrl(path);
  const headers = new Headers(requestInit.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const isFormDataBody = typeof FormData !== "undefined" && requestInit.body instanceof FormData;
  if (requestInit.body && !isFormDataBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(endpoint, {
    ...requestInit,
    headers,
  });

  let payload: T | null = null;
  try {
    payload = (await response.json()) as T;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (response.status === 401 && !skipAuthRecovery) {
      void unauthorizedHandler?.();
    }

    const message =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}.`;

    throw new ApiError(message, response.status, payload);
  }

  return {
    endpoint,
    httpStatus: response.status,
    payload,
  };
}
