import type { Dispatch, SetStateAction } from "react";
import { appApi } from "@/lib/api";
import type { PromptTemplate } from "@/types/api";
import type { Toast } from "@/pages/chat/types";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

interface UsePromptActionsParams {
  setPrompts: Dispatch<SetStateAction<PromptTemplate[]>>;
  setPromptsLoading: Dispatch<SetStateAction<boolean>>;
  setEditingPromptId: Dispatch<SetStateAction<string | null>>;
  setPromptTitle: Dispatch<SetStateAction<string>>;
  setPromptContent: Dispatch<SetStateAction<string>>;
  setPromptCheckInfo: Dispatch<SetStateAction<string>>;
  setAgentClassHint: Dispatch<SetStateAction<AgentClassHint>>;
  setError: Dispatch<SetStateAction<string>>;
  notify: (text: string, kind?: Toast["kind"], ttl?: number) => void;
  handleApiError: (e: unknown, fallback: string) => Promise<void>;
}

export function usePromptActions(params: UsePromptActionsParams) {
  const {
    setPrompts,
    setPromptsLoading,
    setEditingPromptId,
    setPromptTitle,
    setPromptContent,
    setPromptCheckInfo,
    setAgentClassHint,
    setError,
    notify,
    handleApiError,
  } = params;

  const refreshPrompts = async (silent = false) => {
    if (!silent) setPromptsLoading(true);
    try {
      const rows = await appApi.prompts();
      setPrompts(rows);
      setError("");
    } catch (e) {
      await handleApiError(e, "Failed to load prompt templates");
    } finally {
      if (!silent) setPromptsLoading(false);
    }
  };

  const savePrompt = async (promptTitle: string, promptContent: string, editingPromptId: string | null) => {
    const title = promptTitle.trim();
    const content = promptContent.trim();
    if (!title || !content) {
      notify("Title and content are required", "warn");
      return;
    }
    try {
      const saved = editingPromptId
        ? await appApi.promptUpdate(editingPromptId, title, content)
        : await appApi.promptCreate(title, content);
      if (saved.agent_class) setAgentClassHint((saved.agent_class as AgentClassHint) || "");
      setEditingPromptId(null);
      setPromptTitle("");
      setPromptContent("");
      notify("Prompt saved", "success");
      await refreshPrompts();
    } catch (e) {
      await handleApiError(e, "Failed to save prompt");
    }
  };

  const checkPrompt = async (promptTitle: string, promptContent: string, useReasoning: boolean) => {
    const title = promptTitle.trim();
    const content = promptContent.trim();
    if (!title || !content) {
      notify("Fill in title and content first", "warn");
      return;
    }
    try {
      setPromptCheckInfo("Checking...");
      const res = await appApi.promptCheck(title, content, useReasoning);
      const suggestions = (res.suggestions || []).filter(Boolean);
      const suggestionBlock = suggestions.length
        ? `\n\n[Suggestions]\n${suggestions.map((x, i) => `${i + 1}. ${x}`).join("\n")}`
        : "";
      setPromptTitle(res.title || title);
      setPromptContent(`${(res.content || content).trim()}${suggestionBlock}`);
      setPromptCheckInfo(`Check done. ${(res.issues || []).slice(0, 3).join(";")}`);
      notify("Prompt check completed", "success");
    } catch (e) {
      setPromptCheckInfo("");
      await handleApiError(e, "Failed to check prompt");
    }
  };

  const deletePrompt = async (item: PromptTemplate, editingPromptId: string | null) => {
    if (!window.confirm(`Delete template: ${item.title}?`)) return;
    try {
      await appApi.promptDelete(item.prompt_id);
      if (editingPromptId === item.prompt_id) {
        setEditingPromptId(null);
        setPromptTitle("");
        setPromptContent("");
      }
      notify("Prompt deleted", "success");
      await refreshPrompts();
    } catch (e) {
      await handleApiError(e, "Failed to delete prompt");
    }
  };

  return {
    refreshPrompts,
    savePrompt,
    checkPrompt,
    deletePrompt,
  };
}
