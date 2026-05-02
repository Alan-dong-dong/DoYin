import { buildApiUrl, requestJson } from "@/lib/api";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequestPayload {
  email: string;
  password: string;
}

export interface RegisterRequestPayload {
  email: string;
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export type RegisterResponse = AuthUser;

const REGISTER_PATH = "/api/auth/register";
const LOGIN_PATH = "/api/auth/login";
const CURRENT_USER_PATH = "/api/auth/me";

export function getRegisterEndpoint(): string {
  return buildApiUrl(REGISTER_PATH);
}

export function getLoginEndpoint(): string {
  return buildApiUrl(LOGIN_PATH);
}

export function getCurrentUserEndpoint(): string {
  return buildApiUrl(CURRENT_USER_PATH);
}

export async function register(payload: RegisterRequestPayload): Promise<RegisterResponse> {
  const response = await requestJson<RegisterResponse>(REGISTER_PATH, {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuthRecovery: true,
  });

  if (!response.payload) {
    throw new Error("Register response did not include a payload.");
  }

  return response.payload;
}

export async function login(payload: LoginRequestPayload): Promise<LoginResponse> {
  const response = await requestJson<LoginResponse>(LOGIN_PATH, {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuthRecovery: true,
  });

  if (!response.payload) {
    throw new Error("Login response did not include a payload.");
  }

  return response.payload;
}

export async function requestCurrentUser(accessToken: string): Promise<AuthUser> {
  const response = await requestJson<AuthUser>(CURRENT_USER_PATH, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    skipAuthRecovery: true,
  });

  if (!response.payload) {
    throw new Error("Current-user response did not include a payload.");
  }

  return response.payload;
}
