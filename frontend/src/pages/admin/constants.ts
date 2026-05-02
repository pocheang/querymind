/**
 * 管理后台常量定义
 */

/** 用户角色选项 */
export const ROLE_OPTIONS = ["viewer", "analyst"];

/** 用户状态选项 */
export const STATUS_OPTIONS = ["active", "disabled"];

/** 审计日志操作关键词选项 */
export const ACTION_KEYWORD_OPTIONS = [
  "auth.login",
  "auth.logout",
  "session.create",
  "session.delete",
  "query.stream",
  "document.upload",
  "document.delete",
  "prompt.create",
  "prompt.update",
  "prompt.delete",
  "admin.user.create",
  "admin.user.role_update",
  "admin.user.status_update",
  "admin.user.classification_update",
  "admin.user.password_reset",
  "admin.user.approval_token_reset",
];
