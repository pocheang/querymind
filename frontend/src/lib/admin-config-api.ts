import { authFetch, parseOrThrow } from "./api-client";

export const adminConfigApi = {
  async adminReloadConfig() {
    const res = await authFetch("/admin/config/reload", { method: "POST" });
    return parseOrThrow<{
      ok: boolean;
      reloaded_at: string;
      snapshot: Record<string, unknown>;
    }>(res);
  },
};
