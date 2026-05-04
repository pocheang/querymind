import { adminUserApi } from "./admin-user-api";
import { adminAuditApi } from "./admin-audit-api";
import { adminOpsApi } from "./admin-ops-api";
import { adminModelApi } from "./admin-model-api";
import { adminSystemLogApi } from "./admin-system-log-api";
import { adminConfigApi } from "./admin-config-api";

export const adminApi = {
  ...adminUserApi,
  ...adminAuditApi,
  ...adminOpsApi,
  ...adminModelApi,
  ...adminSystemLogApi,
  ...adminConfigApi,
};
