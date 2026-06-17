import { useTranslation } from "react-i18next";
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
}: Props) {
  const { t } = useTranslation();

  return (
    <section className="panel">
      <div className="section-head">
        <strong>{t("components.workbench.promptTemplates")}</strong>
        <button type="button" className="secondary tiny-btn" onClick={() => void onRefreshPrompts()}>
          {t("components.workbench.refresh")}
        </button>
      </div>
      <input value={promptTitle} onChange={(event) => onPromptTitleChange(event.target.value)} placeholder={t("components.workbench.templateTitle")} />
      <textarea
        value={promptContent}
        onChange={(event) => onPromptContentChange(event.target.value)}
        placeholder={t("components.workbench.promptPlaceholder")}
        rows={4}
      />
      <div className="row-actions">
        <button type="button" className="secondary tiny-btn" onClick={() => void onCheckPrompt()}>
          {t("components.workbench.check")}
        </button>
        <button type="button" className="tiny-btn" onClick={() => void onSavePrompt()}>
          {editingPromptId ? t("components.workbench.update") : t("components.workbench.save")}
        </button>
      </div>
      {promptCheckInfo && <div className="hint">{promptCheckInfo}</div>}
      {promptsLoading && <div className="skeleton-list" />}
      {!promptsLoading && prompts.length === 0 && <div className="muted">{t("components.workbench.noTemplates")}</div>}
      {!promptsLoading &&
        prompts.map((prompt) => (
          <div key={prompt.prompt_id} className="prompt-row">
            <div>
              <div>{prompt.title}</div>
              <small className="muted">
                agent={prompt.agent_class || "general"} | {(prompt.content || "").slice(0, 72)}
              </small>
            </div>
            <div className="row-actions">
              <button type="button" className="secondary tiny-btn" onClick={() => onUsePrompt(prompt)}>
                {t("components.workbench.use")}
              </button>
              <button type="button" className="secondary tiny-btn" onClick={() => onEditPrompt(prompt)}>
                {t("components.workbench.edit")}
              </button>
              <button type="button" className="danger tiny-btn" onClick={() => void onDeletePrompt(prompt)}>
                {t("components.workbench.delete")}
              </button>
            </div>
          </div>
        ))}
    </section>
  );
}
