import type { AuditLogEntry } from "@/types/api";
import { request } from "./api-client";
import { buildQueryString } from "./api-helpers";

export const adminAuditApi = {
  adminAudit(input: {
    limit: number;
    actorUserId?: string;
    actionKeyword?: string;
    eventCategory?: string;
    severity?: string;
    result?: string;
  }) {
    const qs = buildQueryString({
      limit: input.limit,
      actor_user_id: input.actorUserId,
      action_keyword: input.actionKeyword,
      event_category: input.eventCategory,
      severity: input.severity,
      result: input.result,
    });
    return request<AuditLogEntry[]>(`/admin/audit-logs?${qs}`);
  },
};
