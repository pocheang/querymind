import type { PromptCheckResponse, PromptTemplate } from "@/types/api";
import { authFetch, parseOrThrow } from "./api-client";
import { buildPostRequest, buildPatchRequest, encodePathParam } from "./api-helpers";

export const promptApi = {
  prompts() {
    return authFetch("/prompts").then(parseOrThrow<PromptTemplate[]>);
  },
  promptCheck(title: string, content: string, useReasoning: boolean) {
    return buildPostRequest<PromptCheckResponse>("/prompts/check", {
      title,
      content,
      use_reasoning: useReasoning,
    });
  },
  promptCreate(title: string, content: string) {
    return buildPostRequest<PromptTemplate>("/prompts", { title, content });
  },
  promptUpdate(promptId: string, title: string, content: string) {
    return buildPatchRequest<PromptTemplate>(`/prompts/${encodePathParam(promptId)}`, { title, content });
  },
  async promptDelete(promptId: string) {
    const res = await authFetch(`/prompts/${encodePathParam(promptId)}`, { method: "DELETE" });
    return parseOrThrow<{ ok: boolean; prompt_id: string }>(res);
  },
};
