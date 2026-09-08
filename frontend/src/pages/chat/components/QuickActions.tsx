import { Button } from "@/components/ui/button";

type Props = {
  quickPrompts: string[];
  question: string;
  isSending: boolean;
  onPromptPick: (prompt: string) => void;
  onStop: () => void;
  onClearQuestion: () => void;
};

/**
 * Suggested follow-ups, above the composer.
 *
 * Stop and Clear used to live here; they are controls of the composer, not
 * suggestions, and they now sit in its toolbar where the design puts them.
 * The props stay so the one call site is unchanged.
 */
export function QuickActions({
  quickPrompts,
  question: _question,
  isSending,
  onPromptPick,
  onStop: _onStop,
  onClearQuestion: _onClearQuestion,
}: Readonly<Props>) {
  if (quickPrompts.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 no-scrollbar">
      {quickPrompts.map((prompt) => (
        <Button
          key={prompt}
          variant="secondary"
          size="xs"
          className="max-w-full truncate rounded-pill font-normal"
          onClick={() => onPromptPick(prompt)}
          disabled={isSending}
        >
          {prompt}
        </Button>
      ))}
    </div>
  );
}
