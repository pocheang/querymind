export { ApiError, authFetch } from "./api-client";
export { authApi } from "@/services/api/auth";
import { appApi as appApiCore } from "@/services/api/app";
import { adminApi as adminApiCore } from "./admin-api";

export const appApi = {
  ...appApiCore,
  ...adminApiCore,
};
