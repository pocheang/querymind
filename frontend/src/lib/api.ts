export { ApiError, authFetch } from "./api-client";
export { authApi } from "./auth-api";
import { appApi as appApiCore } from "./app-api";
import { adminApi as adminApiCore } from "./admin-api";

export const appApi = {
  ...appApiCore,
  ...adminApiCore,
};
