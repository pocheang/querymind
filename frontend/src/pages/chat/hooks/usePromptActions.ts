import type { Dispatch, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import { appApi } from "@/lib/api";
import type { PromptTemplate } from "@/types/api";
import type { Toast } from "@/pages/chat/types";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

// Security constants
const MAX_TITLE_LENGTH = 200;
const MAX_CONTENT_LENGTH = 50000;
const VALID_AGENT_CLASSES: ReadonlySet<AgentClassHint> = new Set([
  "",
  "general",
  "cybersecurity",
  "artificial_intelligence",
  "pdf_text",
]);

// Validate agent class hint
function isValidAgentClass(value: unknown): value is AgentClassHint {
  return typeof value === "string" && VALID_AGENT_CLASSES.has(value as AgentClassHint);
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
  confirm: (opts: { message: string; title?: string; isDanger?: boolean }) => Promise<boolean>;
}

export function usePromptActions(params: UsePromptActionsParams) {
  const { t } = useTranslation();
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
    confirm,
  } = params;

  const refreshPrompts = async (silent = false) => {
    if (!silent) setPromptsLoading(true);
    try {
      const rows = await appApi.prompts();
      setPrompts(rows);
      setError("");
    } catch (e) {
      await handleApiError(e, t("components.workbench.loadPromptsFailed"));
    } finally {
      if (!silent) setPromptsLoading(false);
    }
  };

  const savePrompt = async (promptTitle: string, promptContent: string, editingPromptId: string | null) => {
    const title = promptTitle.trim();
    const content = promptContent.trim();

    // Validate required fields
    if (!title || !content) {
      notify(t("components.workbench.titleContentRequired"), "warn");
      return;
    }

    // Validate length limits
    if (title.length > MAX_TITLE_LENGTH) {
      notify(t("components.workbench.titleTooLong", { max: MAX_TITLE_LENGTH }), "warn");
      return;
    }
    if (content.length > MAX_CONTENT_LENGTH) {
      notify(t("components.workbench.contentTooLong", { max: MAX_CONTENT_LENGTH }), "warn");
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
      notify(t("components.workbench.promptSaved"), "success");
      await refreshPrompts();
    } catch (e) {
      await handleApiError(e, t("components.workbench.savePromptFailed"));
    }
  };

  const checkPrompt = async (promptTitle: string, promptContent: string, useReasoning: boolean) => {
    const title = promptTitle.trim();
    const content = promptContent.trim();

    // Validate required fields
    if (!title || !content) {
      notify(t("components.workbench.fillTitleContentFirst"), "warn");
      return;
    }

    // Validate length limits
    if (title.length > MAX_TITLE_LENGTH) {
      notify(t("components.workbench.titleTooLong", { max: MAX_TITLE_LENGTH }), "warn");
      return;
    }
    if (content.length > MAX_CONTENT_LENGTH) {
      notify(t("components.workbench.contentTooLong", { max: MAX_CONTENT_LENGTH }), "warn");
      return;
    }

    try {
      setPromptCheckInfo(t("components.workbench.checkingPrompt"));
      const res = await appApi.promptCheck(title, content, useReasoning);

      // Kept as the server returned it. These values go into React state and are
      // rendered as text, which React escapes; a blacklist that stripped `<`, `>`
      // and `javascript:` here was no XSS defence and cut them out of prompts.
      const checkedTitle = String(res.title || title);
      const checkedContent = String(res.content || content);
      const suggestions = (res.suggestions || []).filter(Boolean).map(String);

      const numberedSuggestions = suggestions.map((x, i) => `${i + 1}. ${x}`).join("\n");
      const suggestionBlock = suggestions.length
        ? `${t("components.workbench.suggestionsLabel")}${numberedSuggestions}`
        : "";

      const issues = (res.issues || []).slice(0, 3).map(String);

      setPromptTitle(checkedTitle);
      setPromptContent(`${checkedContent.trim()}${suggestionBlock}`);
      setPromptCheckInfo(t("components.workbench.checkDone", { issues: issues.join(";") }));
      notify(t("components.workbench.promptCheckCompleted"), "success");
    } catch (e) {
      setPromptCheckInfo("");
      await handleApiError(e, t("components.workbench.checkPromptFailed"));
    }
  };

  const deletePrompt = async (item: PromptTemplate, editingPromptId: string | null) => {
    const confirmed = await confirm({
      // ConfirmDialog renders `message` as text, so the title needs no filtering.
      message: t("components.workbench.deleteTemplateConfirm", { title: item.title }),
      isDanger: true,
    });
    if (!confirmed) return;

    try {
      await appApi.promptDelete(item.prompt_id);
      if (editingPromptId === item.prompt_id) {
        setEditingPromptId(null);
        setPromptTitle("");
        setPromptContent("");
      }
      notify(t("components.workbench.promptDeleted"), "success");
      await refreshPrompts();
    } catch (e) {
      await handleApiError(e, t("components.workbench.deletePromptFailed"));
    }
  };

  return {
    refreshPrompts,
    savePrompt,
    checkPrompt,
    deletePrompt,
  };
}
