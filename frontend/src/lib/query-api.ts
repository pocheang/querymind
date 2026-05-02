import { authFetch, parseOrThrow } from "./api-client";

export const queryApi = {
  async streamQuery(input: {
    question: string;
    useWebFallback: boolean;
    useReasoning: boolean;
    sessionId: string;
    agentClassHint?: string;
    retrievalStrategy?: string;
    signal?: AbortSignal;
  }) {
    const form = new FormData();
    form.append("question", input.question);
    form.append("use_web_fallback", input.useWebFallback ? "1" : "0");
    form.append("use_reasoning", input.useReasoning ? "1" : "0");
    form.append("session_id", input.sessionId);
    if (input.agentClassHint) form.append("agent_class_hint", input.agentClassHint);
    if (input.retrievalStrategy) form.append("retrieval_strategy", input.retrievalStrategy);
    return authFetch(
      "/query/stream",
      { method: "POST", body: form, signal: input.signal },
      { networkRetry: 2, retryDelayMs: 350 },
    );
  },
  async query(input: {
    question: string;
    useWebFallback: boolean;
    useReasoning: boolean;
    sessionId: string;
    agentClassHint?: string;
    retrievalStrategy?: string;
  }) {
    const res = await authFetch(
      "/query",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: input.question,
          use_web_fallback: input.useWebFallback,
          use_reasoning: input.useReasoning,
          session_id: input.sessionId,
          agent_class_hint: input.agentClassHint || null,
          retrieval_strategy: input.retrievalStrategy || null,
        }),
      },
      { networkRetry: 2, retryDelayMs: 350 },
    );
    return parseOrThrow<{ answer: string; route?: string }>(res);
  },
};
