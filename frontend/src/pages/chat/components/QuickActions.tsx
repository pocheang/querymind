import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  return (
    <div className="quick-actions">
      {quickPrompts.map((prompt) => (
        <button key={prompt} type="button" className="quick-action-btn" onClick={() => onPromptPick(prompt)}>
          {prompt}
        </button>
      ))}
      {isSending && (
        <button type="button" className="quick-action-btn danger" onClick={onStop} aria-label={t("components.chat.stopAria")}>
          {t("components.chat.stop")}
        </button>
      )}
      {question && !isSending && (
        <button type="button" className="quick-action-btn" onClick={onClearQuestion} aria-label={t("components.chat.clearAria")}>
          {t("components.chat.clear")}
        </button>
      )}
    </div>
  );
}
