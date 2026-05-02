import { defineStore } from "pinia";

import { getHealthEndpoint, requestHealth, type HealthResponse } from "@/lib/health";

interface HealthState {
  endpoint: string;
  isLoading: boolean;
  hasRequested: boolean;
  lastRequestedAt: string | null;
  lastCompletedAt: string | null;
  httpStatus: number | null;
  payload: HealthResponse | null;
  errorMessage: string | null;
}

export const useHealthStore = defineStore("health", {
  state: (): HealthState => ({
    endpoint: getHealthEndpoint(),
    isLoading: false,
    hasRequested: false,
    lastRequestedAt: null,
    lastCompletedAt: null,
    httpStatus: null,
    payload: null,
    errorMessage: null,
  }),
  getters: {
    connectivityState(state): "idle" | "checking" | "online" | "offline" {
      const hasSuccessResponse =
        state.httpStatus !== null &&
        state.httpStatus >= 200 &&
        state.httpStatus < 300 &&
        state.payload?.api.ready === true;

      if (hasSuccessResponse) {
        return "online";
      }

      if (state.errorMessage || (state.httpStatus !== null && state.httpStatus >= 400)) {
        return "offline";
      }

      if (state.isLoading) {
        return "checking";
      }

      return "idle";
    },
    connectivityTitle(): string {
      if (this.connectivityState === "online") {
        return "API 连接正常";
      }

      if (this.connectivityState === "offline") {
        return "API 暂时不可用";
      }

      if (this.connectivityState === "checking") {
        return "正在检查 API 连接";
      }

      return "尚未检查 API 连接";
    },
    connectivityDetail(): string {
      if (this.connectivityState === "online" && this.payload) {
        return `后端返回 api.ready=${this.payload.api.ready}，database.ready=${this.payload.database.ready}。`;
      }

      if (this.errorMessage) {
        return this.errorMessage;
      }

      if (this.payload) {
        return `后端返回 status=${this.payload.status}，api.ready=${this.payload.api.ready}，database.ready=${this.payload.database.ready}。`;
      }

      if (this.isLoading) {
        return "正在等待后端健康检查响应。";
      }

      return "页面加载后会触发第一次后端健康检查。";
    },
  },
  actions: {
    async loadHealth() {
      this.endpoint = getHealthEndpoint();
      this.isLoading = true;
      this.hasRequested = true;
      this.lastRequestedAt = new Date().toISOString();

      try {
        const result = await requestHealth();
        this.httpStatus = result.httpStatus;
        this.payload = result.payload;
        this.errorMessage = null;
      } catch (error) {
        this.httpStatus = null;
        this.payload = null;
        this.errorMessage =
          error instanceof Error ? error.message : "无法请求后端健康检查。";
      } finally {
        this.isLoading = false;
        this.lastCompletedAt = new Date().toISOString();
      }
    },
  },
});
