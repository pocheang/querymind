import type { AuthUser, LoginResponse } from "@/types/api";
import { request, getToken, setToken as setTokenInternal } from "@/services/http/client";

export const authApi = {
  async me() {
    return request<AuthUser>("/api/v1/auth/me");
  },
  async login(username: string, password: string) {
    const response = await request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (response.token) {
      setTokenInternal(response.token);
    }
    return response;
  },
  async register(username: string, password: string) {
    return request<AuthUser>("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  },
  async logout() {
    try {
      await request("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // ignore logout error
    }
  },
  async changePassword(oldPassword: string, newPassword: string) {
    return request<{ ok: boolean; message: string }>("/api/v1/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },
  async updateProfile(displayName: string) {
    return request<AuthUser>("/api/v1/auth/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: displayName }),
    });
  },
  setToken(token: string) {
    setTokenInternal(token);
  },
  token() {
    return getToken();
  },
};
