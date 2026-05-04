import type { AdminModelSettingsView } from "@/types/api";
import { authFetch, parseOrThrow } from "./api-client";

export const adminModelApi = {
  async adminModelSettings() {
    const res = await authFetch("/admin/model-settings", { method: "GET" });
    return parseOrThrow<{ ok: boolean; settings: AdminModelSettingsView }>(res);
  },
  async adminSaveModelSettings(settings: {
    enabled: boolean;
    provider: string;
    api_key: string;
    base_url: string;
    chat_model: string;
    reasoning_model: string;
    embedding_model: string;
    temperature: number;
    max_tokens: number;
  }) {
    const res = await authFetch("/admin/model-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return parseOrThrow<{ ok: boolean; settings: AdminModelSettingsView }>(res);
  },
  async adminTestModelSettings(settings: {
    enabled: boolean;
    provider: string;
    api_key: string;
    base_url: string;
    chat_model: string;
    reasoning_model: string;
    embedding_model: string;
    temperature: number;
    max_tokens: number;
  }) {
    const res = await authFetch("/admin/model-settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return parseOrThrow<{
      ok: boolean;
      reachable: boolean;
      provider: string;
      model: string;
      latency_ms: number;
      message: string;
      preview: string;
    }>(res);
  },
};
