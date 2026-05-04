import type { AuditLogEntry } from "@/types/api";
import { request } from "./api-client";

export const adminAuditApi = {
  adminAudit(input: {
    limit: number;
    actorUserId?: string;
    actionKeyword?: string;
    eventCategory?: string;
    severity?: string;
    result?: string;
  }) {
    const qs = new URLSearchParams();
    qs.set("limit", String(input.limit));
    if (input.actorUserId) qs.set("actor_user_id", input.actorUserId);
    if (input.actionKeyword) qs.set("action_keyword", input.actionKeyword);
    if (input.eventCategory) qs.set("event_category", input.eventCategory);
    if (input.severity) qs.set("severity", input.severity);
    if (input.result) qs.set("result", input.result);
    return request<AuditLogEntry[]>(`/admin/audit-logs?${qs.toString()}`);
  },
};
