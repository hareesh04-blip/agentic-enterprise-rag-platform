import { apiClient } from "./client";
import type { CurrentUser, LoginRequest, LoginResponse } from "../types/auth";

export const authApi = {
  async login(payload: LoginRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>("/auth/login", payload);
    return data;
  },

  async me(): Promise<CurrentUser> {
    const { data } = await apiClient.get<CurrentUser>("/auth/me");
    return data;
  },
};
