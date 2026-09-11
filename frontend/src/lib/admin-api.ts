import {
  adminUserApi,
  adminAuditApi,
  adminOpsApi,
  adminModelApi,
  adminSystemLogApi,
  adminConfigApi,
} from "@/services/api/admin";

export {
  adminUserApi,
  adminAuditApi,
  adminOpsApi,
  adminModelApi,
  adminSystemLogApi,
  adminConfigApi,
};

export const adminApi = {
  ...adminUserApi,
  ...adminAuditApi,
  ...adminOpsApi,
  ...adminModelApi,
  ...adminSystemLogApi,
  ...adminConfigApi,
};
