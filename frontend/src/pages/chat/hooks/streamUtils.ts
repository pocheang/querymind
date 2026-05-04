import type { SessionMessage } from "@/types/api";
import { EMPTY_METADATA } from "@/pages/chat/constants";

/**
 * 解析流式请求错误响应
 */
export function parseStreamError(raw: string): string {
  if (!raw) return "Stream request failed";
  try {
    const parsed = JSON.parse(raw);
    return String(parsed?.detail || raw);
  } catch {
    return raw;
  }
}

/**
 * 判断是否为中止错误
 */
export function isAbortError(e: unknown, streamStopped: boolean): boolean {
  const rawError = e instanceof Error && e.message ? e.message : "request aborted";
  return (
    streamStopped ||
    (e instanceof DOMException && e.name === "AbortError") ||
    String(rawError).toLowerCase().includes("abort")
  );
}

/**
 * 判断是否为网络错误
 */
export function isNetworkError(errorText: string): boolean {
  const lowered = String(errorText).toLowerCase();
  return (
    lowered.includes("networkerror") ||
    lowered.includes("failed to fetch") ||
    lowered.includes("network error")
  );
}

/**
 * 创建初始流式消息（用户消息 + 空的助手消息）
 */
export function createInitialStreamMessages(question: string): SessionMessage[] {
  return [
    { message_id: `local-user-${Date.now()}`, role: "user", content: question },
    {
      message_id: "local-assistant-stream",
      role: "assistant",
      content: "",
      metadata: { ...EMPTY_METADATA }
    },
  ];
}
