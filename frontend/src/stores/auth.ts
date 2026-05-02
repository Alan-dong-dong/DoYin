import { defineStore } from "pinia";

import { ApiError } from "@/lib/api";
import {
  login,
  register,
  requestCurrentUser,
  type AuthUser,
  type LoginRequestPayload,
  type RegisterRequestPayload,
} from "@/lib/auth";

const AUTH_STORAGE_KEY = "doyin.auth.access-token";
let pendingHydration: Promise<void> | null = null;

interface AuthState {
  accessToken: string | null;
  currentUser: AuthUser | null;
  isHydrating: boolean;
  isAuthenticating: boolean;
  isRegistering: boolean;
  isReady: boolean;
  errorMessage: string | null;
  registrationFallbackEmail: string | null;
  registrationNotice: string | null;
}

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_STORAGE_KEY);
}

function writeStoredAccessToken(accessToken: string | null): void {
  if (typeof window === "undefined") {
    return;
  }

  if (accessToken) {
    window.localStorage.setItem(AUTH_STORAGE_KEY, accessToken);
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeUsername(value: string): string {
  return value.trim();
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    accessToken: readStoredAccessToken(),
    currentUser: null,
    isHydrating: false,
    isAuthenticating: false,
    isRegistering: false,
    isReady: false,
    errorMessage: null,
    registrationFallbackEmail: null,
    registrationNotice: null,
  }),
  getters: {
    isAuthenticated(state): boolean {
      return Boolean(state.accessToken && state.currentUser);
    },
  },
  actions: {
    setSession(accessToken: string, user: AuthUser) {
      this.accessToken = accessToken;
      this.currentUser = user;
      this.errorMessage = null;
      writeStoredAccessToken(accessToken);
    },
    setRegistrationFollowUp(email: string | null, notice: string | null) {
      this.registrationFallbackEmail = email;
      this.registrationNotice = notice;
    },
    clearRegistrationFollowUp() {
      this.registrationFallbackEmail = null;
      this.registrationNotice = null;
    },
    clearSession() {
      this.accessToken = null;
      this.currentUser = null;
      this.errorMessage = null;
      writeStoredAccessToken(null);
    },
    async establishSession(payload: LoginRequestPayload) {
      const response = await login({
        email: normalizeEmail(payload.email),
        password: payload.password,
      });
      this.setSession(response.access_token, response.user);
      return response.user;
    },
    async hydrateSession() {
      if (pendingHydration) {
        return pendingHydration;
      }

      if (!this.accessToken) {
        this.isReady = true;
        return;
      }

      pendingHydration = (async () => {
        this.isHydrating = true;
        try {
          this.currentUser = await requestCurrentUser(this.accessToken as string);
          this.errorMessage = null;
        } catch {
          this.clearSession();
        } finally {
          this.isHydrating = false;
          this.isReady = true;
          pendingHydration = null;
        }
      })();

      return pendingHydration;
    },
    async signIn(payload: LoginRequestPayload) {
      this.isAuthenticating = true;
      this.errorMessage = null;
      try {
        const user = await this.establishSession(payload);
        this.clearRegistrationFollowUp();
        return user;
      } catch (error) {
        this.errorMessage = getErrorMessage(error, "无法登录，请检查邮箱和密码。");
        throw error;
      } finally {
        this.isAuthenticating = false;
        this.isReady = true;
      }
    },
    async registerAccount(payload: RegisterRequestPayload) {
      const normalizedPayload = {
        email: normalizeEmail(payload.email),
        username: normalizeUsername(payload.username),
        password: payload.password,
      };

      this.isRegistering = true;
      this.errorMessage = null;
      this.clearRegistrationFollowUp();

      try {
        await register(normalizedPayload);

        this.isAuthenticating = true;
        try {
          const user = await this.establishSession({
            email: normalizedPayload.email,
            password: normalizedPayload.password,
          });
          this.clearRegistrationFollowUp();
          return {
            status: "signed_in" as const,
            user,
          };
        } catch {
          this.clearSession();
          const notice = "账号已创建，请使用新账号登录。";
          this.setRegistrationFollowUp(normalizedPayload.email, notice);
          return {
            status: "login_required" as const,
            email: normalizedPayload.email,
            notice,
          };
        } finally {
          this.isAuthenticating = false;
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error, "无法创建账号。");
        throw error;
      } finally {
        this.isRegistering = false;
        this.isReady = true;
      }
    },
  },
});
