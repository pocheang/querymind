import type { PromptCheckResponse, PromptTemplate } from "@/types/api";
import { authFetch, parseOrThrow } from "./api-client";

export const promptApi = {
  prompts() {
    return authFetch("/prompts").then(parseOrThrow<PromptTemplate[]>);
  },
  async promptCheck(title: string, content: string, useReasoning: boolean) {
    const res = await authFetch("/prompts/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content, use_reasoning: useReasoning }),
    });
    return parseOrThrow<PromptCheckResponse>(res);
  },
  async promptCreate(title: string, content: string) {
    const res = await authFetch("/prompts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    });
    return parseOrThrow<PromptTemplate>(res);
  },
  async promptUpdate(promptId: string, title: string, content: string) {
    const res = await authFetch(`/prompts/${encodeURIComponent(promptId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    });
    return parseOrThrow<PromptTemplate>(res);
  },
  async promptDelete(promptId: string) {
    const res = await authFetch(`/prompts/${encodeURIComponent(promptId)}`, { method: "DELETE" });
    return parseOrThrow<{ ok: boolean; prompt_id: string }>(res);
  },
};
