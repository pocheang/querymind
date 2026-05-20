import type { AdminUserSummary } from "@/types/api";

/**
 * 格式化审计日志时间戳
 * @param ts ISO 时间字符串
 * @returns 格式化后的时间字符串（中文格式）
 */
export function formatAuditTime(ts?: string | null): string {
  if (!ts) return "-";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(d);
}

/**
 * Resolves a user input string to a user ID by trying multiple strategies:
 * 1. Exact user_id match
 * 2. Exact username match (case-insensitive)
 * 3. Fuzzy username match (if only one result)
 * 4. Returns the raw value if it looks like a valid ID format
 */
export function resolveUserIdFromInput(
  input: string,
  users: AdminUserSummary[],
  options: { allowRawId?: boolean; minIdLength?: number } = {}
): string | undefined {
  const { allowRawId = true, minIdLength = 16 } = options;
  const value = input.trim();

  if (!value) return undefined;

  const exactId = users.find((u) => u.user_id === value);
  if (exactId) return exactId.user_id;

  const exactName = users.find((u) => (u.username || "").toLowerCase() === value.toLowerCase());
  if (exactName) return exactName.user_id;

  const fuzzy = users.filter((u) => (u.username || "").toLowerCase().includes(value.toLowerCase()));
  if (fuzzy.length === 1) return fuzzy[0].user_id;

  if (allowRawId && new RegExp(`^[a-zA-Z0-9_-]{${minIdLength},}$`).test(value)) {
    return value;
  }

  return undefined;
}
