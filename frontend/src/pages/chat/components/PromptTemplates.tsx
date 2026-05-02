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
  return (
    <section className="panel">
      <div className="section-head">
        <strong>Prompt Templates</strong>
        <button type="button" className="secondary tiny-btn" onClick={() => void onRefreshPrompts()}>
          Refresh
        </button>
      </div>
      <input value={promptTitle} onChange={(e) => onPromptTitleChange(e.target.value)} placeholder="Template title" />
      <textarea
        value={promptContent}
        onChange={(e) => onPromptContentChange(e.target.value)}
        placeholder="Write your prompt template..."
        rows={4}
      />
      <div className="row-actions">
        <button type="button" className="secondary tiny-btn" onClick={() => void onCheckPrompt()}>
          Check
        </button>
        <button type="button" className="tiny-btn" onClick={() => void onSavePrompt()}>
          {editingPromptId ? "Update" : "Save"}
        </button>
      </div>
      {promptCheckInfo && <div className="hint">{promptCheckInfo}</div>}
      {promptsLoading && <div className="skeleton-list" />}
      {!promptsLoading && prompts.length === 0 && <div className="muted">No templates yet</div>}
      {!promptsLoading &&
        prompts.map((p) => (
          <div key={p.prompt_id} className="prompt-row">
            <div>
              <div>{p.title}</div>
              <small className="muted">
                agent={p.agent_class || "general"} | {(p.content || "").slice(0, 72)}
              </small>
            </div>
            <div className="row-actions">
              <button type="button" className="secondary tiny-btn" onClick={() => onUsePrompt(p)}>
                Use
              </button>
              <button type="button" className="secondary tiny-btn" onClick={() => onEditPrompt(p)}>
                Edit
              </button>
              <button type="button" className="danger tiny-btn" onClick={() => void onDeletePrompt(p)}>
                Delete
              </button>
            </div>
          </div>
        ))}
    </section>
  );
}
