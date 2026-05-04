import { useState } from "react";
import type { PromptTemplate } from "@/types/api";

export function usePromptState() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [promptTitle, setPromptTitle] = useState("");
  const [promptContent, setPromptContent] = useState("");
  const [editingPromptId, setEditingPromptId] = useState<string | null>(null);
  const [promptCheckInfo, setPromptCheckInfo] = useState("");

  return {
    prompts,
    setPrompts,
    promptsLoading,
    setPromptsLoading,
    promptTitle,
    setPromptTitle,
    promptContent,
    setPromptContent,
    editingPromptId,
    setEditingPromptId,
    promptCheckInfo,
    setPromptCheckInfo,
  };
}

export type PromptState = ReturnType<typeof usePromptState>;
