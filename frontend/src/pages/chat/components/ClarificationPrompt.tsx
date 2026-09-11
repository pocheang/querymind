import React, { useEffect, useState } from "react";
import { HelpCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CollapsibleSection } from "@/pages/chat/components/CollapsibleSection";
import { useTranslation } from "react-i18next";
import type { ClarificationQuestion, ClarificationContext } from "../../../types/api";

interface ClarificationPromptProps {
  question: ClarificationQuestion;
  context: ClarificationContext;
  onAnswer: (fieldName: string, answer: string) => void;
  onSkip: () => void;
  isSubmitting?: boolean;
}

export const ClarificationPrompt: React.FC<ClarificationPromptProps> = ({
  question,
  context,
  onAnswer,
  onSkip,
  isSubmitting = false,
}) => {
  const { t } = useTranslation();
  const [selectedOption, setSelectedOption] = useState<string>("");
  const [customInput, setCustomInput] = useState<string>("");
  const [useCustom, setUseCustom] = useState<boolean>(false);

  useEffect(() => {
    setSelectedOption("");
    setCustomInput("");
    setUseCustom(false);
  }, [question.field_name]);

  const handleSubmit = () => {
    const answer = useCustom ? customInput.trim() : selectedOption;
    if (!answer) return;
    onAnswer(question.field_name, answer);
  };

  const handleOptionSelect = (option: string) => {
    setSelectedOption(option);
    setUseCustom(false);
  };

  const handleCustomToggle = () => {
    setUseCustom(true);
    setSelectedOption("");
  };

  const isValid = useCustom ? customInput.trim().length > 0 : selectedOption.length > 0;

  return (
    <div className="mx-auto w-full max-w-4xl shrink-0 px-4 pb-2">
      <div className="glass-card space-y-3 rounded-card border-brand-border-strong p-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-brand-text-strong">
            <HelpCircle className="size-4 text-brand-accent" aria-hidden="true" />
            {t("clarification.title")}
          </h3>
          <Badge variant="brand" size="xs" mono>
            {t("clarification.round", {
              current: context.clarification_round + 1,
              max: context.max_rounds,
            })}
          </Badge>
        </div>

        <p className="text-xs sm:text-sm leading-relaxed text-ink">{question.question}</p>

        <div className="space-y-1.5">
          {question.options.map((option) => {
            const selected = selectedOption === option && !useCustom;
            return (
              <button
                key={option}
                type="button"
                className={cn(
                  "flex w-full items-center gap-2 rounded-control border p-2 text-left text-xs sm:text-sm font-medium transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  selected
                    ? "border-brand-border-strong bg-brand-surface text-brand-text-strong"
                    : "border-line bg-surface text-ink hover:border-brand-border hover:bg-brand-surface/60"
                )}
                aria-pressed={selected}
                onClick={() => handleOptionSelect(option)}
                disabled={isSubmitting}
              >
                <span
                  className={cn(
                    "flex size-3.5 shrink-0 items-center justify-center rounded-pill border",
                    selected ? "border-brand bg-brand" : "border-line-strong bg-surface"
                  )}
                  aria-hidden="true"
                >
                  {selected && <span className="size-1.5 rounded-pill bg-white" />}
                </span>
                <span className="min-w-0 flex-1">{option}</span>
              </button>
            );
          })}

          {question.allow_custom_input && (
            <div className="space-y-1.5">
              <button
                type="button"
                className={cn(
                  "flex w-full items-center gap-2 rounded-control border p-2 text-left text-xs sm:text-sm font-medium transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  useCustom
                    ? "border-brand-border-strong bg-brand-surface text-brand-text-strong"
                    : "border-line bg-surface text-ink hover:border-brand-border hover:bg-brand-surface/60"
                )}
                aria-pressed={useCustom}
                onClick={handleCustomToggle}
                disabled={isSubmitting}
              >
                <span
                  className={cn(
                    "flex size-3.5 shrink-0 items-center justify-center rounded-pill border",
                    useCustom ? "border-brand bg-brand" : "border-line-strong bg-surface"
                  )}
                  aria-hidden="true"
                >
                  {useCustom && <span className="size-1.5 rounded-pill bg-white" />}
                </span>
                <span className="min-w-0 flex-1">{t("clarification.customInput")}</span>
              </button>
              {useCustom && (
                <Input
                  type="text"
                  placeholder={t("clarification.customInputPlaceholder")}
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  disabled={isSubmitting}
                  autoFocus
                />
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onSkip} disabled={isSubmitting}>
            {t("clarification.skip")}
          </Button>
          <Button size="sm" onClick={handleSubmit} disabled={!isValid || isSubmitting}>
            {isSubmitting ? t("clarification.submitting") : t("clarification.submit")}
          </Button>
        </div>

        {context.collected_info && Object.keys(context.collected_info).length > 0 && (
          <CollapsibleSection title={t("clarification.collectedInfo")} ariaLabel={t("clarification.collectedInfo")}>
            <ul className="space-y-1 text-xs text-ink/75">
              {Object.entries(context.collected_info).map(([key, value]) => (
                <li key={key}>
                  <strong className="text-ink">{key}:</strong> {value}
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
};
