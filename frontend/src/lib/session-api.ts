import type { SessionDetail, SessionSummary } from "@/types/api";
import { authFetch, parseOrThrow } from "./api-client";

export const sessionApi = {
  sessions() {
    return authFetch("/sessions").then(parseOrThrow<SessionSummary[]>);
  },
  sessionCreate() {
    return authFetch("/sessions", { method: "POST" }).then(parseOrThrow<SessionDetail>);
  },
  sessionDetail(sessionId: string) {
    return authFetch(`/sessions/${encodeURIComponent(sessionId)}`).then(parseOrThrow<SessionDetail>);
  },
  async sessionDelete(sessionId: string) {
    const res = await authFetch(`/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    return parseOrThrow<{ ok: boolean; session_id: string }>(res);
  },
  async messageUpdate(
    sessionId: string,
    messageId: string,
    content: string,
    rerun: boolean,
    useWebFallback: boolean,
    useReasoning: boolean,
  ) {
    const qs = new URLSearchParams({
      rerun: rerun ? "true" : "false",
      use_web_fallback: useWebFallback ? "1" : "0",
      use_reasoning: useReasoning ? "1" : "0",
    });
    const res = await authFetch(
      `/sessions/${encodeURIComponent(sessionId)}/messages/${encodeURIComponent(messageId)}?${qs.toString()}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      },
    );
    return parseOrThrow<SessionDetail>(res);
  },
  async messageDelete(sessionId: string, messageId: string) {
    const res = await authFetch(
      `/sessions/${encodeURIComponent(sessionId)}/messages/${encodeURIComponent(messageId)}`,
      { method: "DELETE" },
    );
    return parseOrThrow<SessionDetail>(res);
  },
};
