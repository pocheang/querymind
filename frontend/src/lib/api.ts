import { adminApi } from "@/services/api/admin";
import { appApi as appApiCore } from "@/services/api/app";

export { ApiError, authFetch } from "@/services/http/client";
export { authApi } from "@/services/api/auth";

export const appApi = {
  ...appApiCore,
  ...adminApi,
};
