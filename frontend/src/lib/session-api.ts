import type { SessionDetail, SessionSummary } from "@/types/api";
import { authRequest } from "./api-client";
import { buildQueryString, buildPatchRequest, encodePathParam } from "./api-helpers";

export const sessionApi = {
  sessions() {
    return authRequest<SessionSummary[]>("/sessions");
  },
  sessionCreate() {
    return authRequest<SessionDetail>("/sessions", { method: "POST" });
  },
  sessionDetail(sessionId: string) {
    return authRequest<SessionDetail>(`/sessions/${encodePathParam(sessionId)}`);
  },
  sessionDelete(sessionId: string) {
    return authRequest<{ ok: boolean; session_id: string }>(`/sessions/${encodePathParam(sessionId)}`, { method: "DELETE" });
  },
  sessionRename(sessionId: string, newTitle: string) {
    return buildPatchRequest<{ ok: boolean; session_id: string }>(`/sessions/${encodePathParam(sessionId)}`, { title: newTitle });
  },
  messageUpdate(
    sessionId: string,
    messageId: string,
    content: string,
    rerun: boolean,
    useWebFallback: boolean,
    useReasoning: boolean,
  ) {
    const qs = buildQueryString({
      rerun: rerun ? "true" : "false",
      use_web_fallback: useWebFallback ? "1" : "0",
      use_reasoning: useReasoning ? "1" : "0",
    });
    return buildPatchRequest<SessionDetail>(
      `/sessions/${encodePathParam(sessionId)}/messages/${encodePathParam(messageId)}?${qs}`,
      { content },
    );
  },
  messageDelete(sessionId: string, messageId: string) {
    return authRequest<SessionDetail>(
      `/sessions/${encodePathParam(sessionId)}/messages/${encodePathParam(messageId)}`,
      { method: "DELETE" },
    );
  },
};
