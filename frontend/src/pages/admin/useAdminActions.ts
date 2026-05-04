import { ApiError } from "@/lib/api";
import type { AdminActionsParams } from "./actions/types";
import { createUserActions } from "./actions/userActions";
import { createModelActions } from "./actions/modelActions";
import { createAuditActions } from "./actions/auditActions";
import { createSystemLogActions } from "./actions/systemLogActions";
import { createOpsActions } from "./actions/opsActions";

export function useAdminActions(params: AdminActionsParams) {
  const { onLogout, setError } = params;

  const handleApiError = async (e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return onLogout();
    setError(e instanceof Error ? e.message : fallback);
  };

  const errorHandler = { handleApiError };

  const userActions = createUserActions(params, errorHandler);
  const modelActions = createModelActions(params, errorHandler);
  const auditActions = createAuditActions(params, errorHandler);
  const systemLogActions = createSystemLogActions(params, errorHandler);
  const opsActions = createOpsActions(params, errorHandler);

  return {
    ...userActions,
    ...modelActions,
    ...auditActions,
    ...systemLogActions,
    ...opsActions,
  };
}
