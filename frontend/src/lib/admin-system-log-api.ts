import type { SystemLogEntry } from "@/types/api";
import { request } from "./api-client";
import { buildQueryString } from "./api-helpers";

export const adminSystemLogApi = {
  adminSystemLogs(input: { limit?: number; level?: string; logger?: string; keyword?: string } = {}) {
    const qs = buildQueryString({
      limit: input.limit ?? 200,
      level: input.level,
      logger: input.logger,
      keyword: input.keyword,
    });
    return request<{ items: SystemLogEntry[]; count: number }>(`/admin/system-logs?${qs}`);
  },
};
