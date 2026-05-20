import { appApi } from "@/lib/api";
import type { AdminActionsParams, ErrorHandler } from "./types";
import { resolveUserIdFromInput } from "../utils";

export function createAuditActions(params: AdminActionsParams, errorHandler: ErrorHandler) {
  const {
    users,
    auditLimit,
    auditActorUserId,
    auditActionKeyword,
    auditEventCategory,
    auditSeverity,
    auditResult,
    isAdmin,
    setLogs,
    setError,
    setLoadingLogs,
  } = params;

  const { handleApiError } = errorHandler;

  const loadLogs = async () => {
    if (!isAdmin) return;
    setLoadingLogs(true);
    try {
      const rawActor = auditActorUserId.trim();
      const resolvedActorId = resolveUserIdFromInput(rawActor, users);
      let rows = await appApi.adminAudit({
        limit: auditLimit,
        actorUserId: resolvedActorId,
        actionKeyword: auditActionKeyword.trim() || undefined,
        eventCategory: auditEventCategory.trim() || undefined,
        severity: auditSeverity.trim() || undefined,
        result: auditResult.trim() || undefined,
      });

      if (rawActor && !resolvedActorId) {
        const q = rawActor.toLowerCase();
        rows = rows.filter((x) => {
          const uid = (x.actor_user_id || "").toLowerCase();
          const uname = (users.find((u) => u.user_id === x.actor_user_id)?.username || "").toLowerCase();
          return uid.includes(q) || uname.includes(q);
        });
      }

      setLogs(rows);
      setError("");
    } catch (e) {
      await handleApiError(e, "加载审计日志失败");
    } finally {
      setLoadingLogs(false);
    }
  };

  return {
    loadLogs,
  };
}
