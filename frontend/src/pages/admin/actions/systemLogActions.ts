import { appApi } from "@/lib/api";
import type { AdminActionsParams, ErrorHandler } from "./types";

export function createSystemLogActions(params: AdminActionsParams, errorHandler: ErrorHandler) {
  const {
    systemLogLimit,
    systemLogLevel,
    systemLogLogger,
    systemLogKeyword,
    isAdmin,
    setSystemLogs,
    setError,
    setLoadingSystemLogs,
  } = params;

  const { handleApiError } = errorHandler;

  const loadSystemLogs = async () => {
    if (!isAdmin) return;
    setLoadingSystemLogs(true);
    try {
      const res = await appApi.adminSystemLogs({
        limit: systemLogLimit,
        level: systemLogLevel.trim() || undefined,
        logger: systemLogLogger.trim() || undefined,
        keyword: systemLogKeyword.trim() || undefined,
      });
      setSystemLogs(res.items || []);
      setError("");
    } catch (e) {
      await handleApiError(e, "加载系统日志失败");
    } finally {
      setLoadingSystemLogs(false);
    }
  };

  return {
    loadSystemLogs,
  };
}
