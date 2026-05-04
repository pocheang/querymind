import { sessionApi } from "./session-api";
import { queryApi } from "./query-api";
import { documentApi } from "./document-api";
import { promptApi } from "./prompt-api";
import { userSettingsApi } from "./user-settings-api";

export const appApi = {
  ...sessionApi,
  ...queryApi,
  ...documentApi,
  ...promptApi,
  ...userSettingsApi,
};
