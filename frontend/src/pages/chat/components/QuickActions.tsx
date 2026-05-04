type Props = {
  quickPrompts: string[];
  question: string;
  isSending: boolean;
  onPromptPick: (prompt: string) => void;
  onStop: () => void;
  onClearQuestion: () => void;
};

export function QuickActions({
  quickPrompts,
  question,
  isSending,
  onPromptPick,
  onStop,
  onClearQuestion,
}: Props) {
  return (
    <div className="quick-actions">
      {quickPrompts.map((prompt) => (
        <button key={prompt} type="button" className="quick-action-btn" onClick={() => onPromptPick(prompt)}>
          {prompt}
        </button>
      ))}
      {isSending && (
        <button type="button" className="quick-action-btn danger" onClick={onStop} aria-label="停止当前处理">
          停止
        </button>
      )}
      {question && !isSending && (
        <button type="button" className="quick-action-btn" onClick={onClearQuestion} aria-label="清空输入框">
          清空
        </button>
      )}
    </div>
  );
}
