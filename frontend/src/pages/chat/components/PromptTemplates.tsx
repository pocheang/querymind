import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { PromptTemplate } from "@/types/api";

type Props = {
  prompts: PromptTemplate[];
  promptsLoading: boolean;
  promptTitle: string;
  promptContent: string;
  editingPromptId: string | null;
  promptCheckInfo: string;
  onRefreshPrompts: () => Promise<void>;
  onPromptTitleChange: (title: string) => void;
  onPromptContentChange: (content: string) => void;
  onCheckPrompt: () => Promise<void>;
  onSavePrompt: () => Promise<void>;
  onUsePrompt: (prompt: PromptTemplate) => void;
  onEditPrompt: (prompt: PromptTemplate) => void;
  onDeletePrompt: (prompt: PromptTemplate) => Promise<void>;
};

export function PromptTemplates({
  prompts,
  promptsLoading,
  promptTitle,
  promptContent,
  editingPromptId,
  promptCheckInfo,
  onRefreshPrompts,
  onPromptTitleChange,
  onPromptContentChange,
  onCheckPrompt,
  onSavePrompt,
  onUsePrompt,
  onEditPrompt,
  onDeletePrompt,
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          {t("components.workbench.promptTemplates")}
        </span>
        <Button variant="ghost" size="xs" onClick={() => void onRefreshPrompts()}>
          <RefreshCw className="size-3.5" aria-hidden="true" />
          {t("components.workbench.refresh")}
        </Button>
      </div>

      <Input
        value={promptTitle}
        onChange={(event) => onPromptTitleChange(event.target.value)}
        placeholder={t("components.workbench.templateTitle")}
      />
      <Textarea
        value={promptContent}
        onChange={(event) => onPromptContentChange(event.target.value)}
        placeholder={t("components.workbench.promptPlaceholder")}
        rows={4}
      />

      <div className="flex flex-wrap gap-1">
        <Button variant="secondary" size="xs" onClick={() => void onCheckPrompt()}>
          {t("components.workbench.check")}
        </Button>
        <Button size="xs" onClick={() => void onSavePrompt()}>
          {editingPromptId ? t("components.workbench.update") : t("components.workbench.save")}
        </Button>
      </div>

      {promptCheckInfo && <p className="text-xs font-semibold text-brand-text">{promptCheckInfo}</p>}

      {promptsLoading && (
        <div className="space-y-1.5">
          {[0, 1].map((row) => (
            <div key={row} className="h-10 animate-pulse rounded-control bg-brand-surface-hover" />
          ))}
        </div>
      )}

      {!promptsLoading && prompts.length === 0 && (
        <p className="py-3 text-center text-xs text-ink/75">{t("components.workbench.noTemplates")}</p>
      )}

      {!promptsLoading &&
        prompts.map((prompt) => (
          <div key={prompt.prompt_id} className="rounded-control border border-line bg-surface p-2.5">
            <p className="truncate text-xs sm:text-sm font-semibold text-ink">{prompt.title}</p>
            <p className="mt-0.5 truncate font-mono text-xs text-ink/75">
              agent={prompt.agent_class || "general"} | {(prompt.content || "").slice(0, 72)}
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <Button variant="soft" size="xs" onClick={() => onUsePrompt(prompt)}>
                {t("components.workbench.use")}
              </Button>
              <Button variant="secondary" size="xs" onClick={() => onEditPrompt(prompt)}>
                {t("components.workbench.edit")}
              </Button>
              <Button variant="destructive-ghost" size="xs" onClick={() => void onDeletePrompt(prompt)}>
                {t("components.workbench.delete")}
              </Button>
            </div>
          </div>
        ))}
    </div>
  );
}
