import { apiClient } from "./client";
import type { PlatformStatusResponse, RuntimeMetadata } from "../types/health";

export interface LivenessHealthResponse {
  status: string;
  app_name: string;
  environment: string;
  runtime?: RuntimeMetadata;
}

export const healthApi = {
  async getPlatformStatus(): Promise<PlatformStatusResponse> {
    const { data } = await apiClient.get<PlatformStatusResponse>("/status");
    return data;
  },
  /** Public liveness + runtime snapshot (same shape as GET /health). */
  async getLivenessHealth(): Promise<LivenessHealthResponse> {
    const { data } = await apiClient.get<LivenessHealthResponse>("/health");
    return data;
  },
};
