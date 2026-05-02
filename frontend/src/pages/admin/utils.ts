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
