import type { Dispatch, SetStateAction } from "react";
import { appApi } from "@/lib/api";
import type { PromptTemplate } from "@/types/api";
import type { Toast } from "@/pages/chat/types";
import { sanitizeString } from "@/lib/validation";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

// Security constants
const MAX_TITLE_LENGTH = 200;
const MAX_CONTENT_LENGTH = 50000;
const VALID_AGENT_CLASSES: AgentClassHint[] = ["", "general", "cybersecurity", "artificial_intelligence", "pdf_text"];

// Validate agent class hint
function isValidAgentClass(value: unknown): value is AgentClassHint {
  return typeof value === "string" && VALID_AGENT_CLASSES.includes(value as AgentClassHint);
}

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

    // Validate required fields
    if (!title || !content) {
      notify("Title and content are required", "warn");
      return;
    }

    // Validate length limits
    if (title.length > MAX_TITLE_LENGTH) {
      notify(`Title must be under ${MAX_TITLE_LENGTH} characters`, "warn");
      return;
    }
    if (content.length > MAX_CONTENT_LENGTH) {
      notify(`Content must be under ${MAX_CONTENT_LENGTH} characters`, "warn");
      return;
    }

    try {
      const saved = editingPromptId
        ? await appApi.promptUpdate(editingPromptId, title, content)
        : await appApi.promptCreate(title, content);

      // Validate and set agent class with runtime type checking
      if (saved.agent_class && isValidAgentClass(saved.agent_class)) {
        setAgentClassHint(saved.agent_class);
      }

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

    // Validate required fields
    if (!title || !content) {
      notify("Fill in title and content first", "warn");
      return;
    }

    // Validate length limits
    if (title.length > MAX_TITLE_LENGTH) {
      notify(`Title must be under ${MAX_TITLE_LENGTH} characters`, "warn");
      return;
    }
    if (content.length > MAX_CONTENT_LENGTH) {
      notify(`Content must be under ${MAX_CONTENT_LENGTH} characters`, "warn");
      return;
    }

    try {
      setPromptCheckInfo("Checking...");
      const res = await appApi.promptCheck(title, content, useReasoning);

      // Sanitize API response data to prevent XSS
      const sanitizedTitle = sanitizeString(res.title || title);
      const sanitizedContent = sanitizeString(res.content || content);
      const sanitizedSuggestions = (res.suggestions || [])
        .filter(Boolean)
        .map((s) => sanitizeString(String(s)));

      const suggestionBlock = sanitizedSuggestions.length
        ? `\n\n[Suggestions]\n${sanitizedSuggestions.map((x, i) => `${i + 1}. ${x}`).join("\n")}`
        : "";

      const sanitizedIssues = (res.issues || [])
        .slice(0, 3)
        .map((issue) => sanitizeString(String(issue)));

      setPromptTitle(sanitizedTitle);
      setPromptContent(`${sanitizedContent.trim()}${suggestionBlock}`);
      setPromptCheckInfo(`Check done. ${sanitizedIssues.join(";")}`);
      notify("Prompt check completed", "success");
    } catch (e) {
      setPromptCheckInfo("");
      await handleApiError(e, "Failed to check prompt");
    }
  };

  const deletePrompt = async (item: PromptTemplate, editingPromptId: string | null) => {
    // Sanitize title for display in confirmation dialog
    const sanitizedTitle = sanitizeString(item.title);
    if (!window.confirm(`Delete template: ${sanitizedTitle}?`)) return;

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
