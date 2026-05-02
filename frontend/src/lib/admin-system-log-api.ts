import type { SystemLogEntry } from "@/types/api";
import { request } from "./api-client";

export const adminSystemLogApi = {
  adminSystemLogs(input: { limit?: number; level?: string; logger?: string; keyword?: string } = {}) {
    const qs = new URLSearchParams();
    qs.set("limit", String(input.limit ?? 200));
    if (input.level) qs.set("level", input.level);
    if (input.logger) qs.set("logger", input.logger);
    if (input.keyword) qs.set("keyword", input.keyword);
    return request<{ items: SystemLogEntry[]; count: number }>(`/admin/system-logs?${qs.toString()}`);
  },
};
