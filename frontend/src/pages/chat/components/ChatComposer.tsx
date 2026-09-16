import type React from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight, Brain, EyeOff, Globe, Loader2, Paperclip, Square } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { QuickActions } from "@/pages/chat/components/QuickActions";
import { useChatStore } from "@/stores/useChatStore";
import { RUN_STATUS_PROCESSING } from "@/pages/chat/constants";
import { useTextareaAutoResize } from "@/pages/chat/hooks/useTextareaAutoResize";
import { CHAT_ACCEPT_ATTRIBUTE } from "@/lib/uploadFormats";

type Props = {
  questionRef: React.MutableRefObject<HTMLTextAreaElement | null>;
  chatUploadInputRef: React.MutableRefObject<HTMLInputElement | null>;
  isSending: boolean;
  quickPrompts: string[];
  onAsk: () => Promise<void>;
  onStop: () => void;
  onComposerDragEnter: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragOver: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragLeave: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDrop: (evt: React.DragEvent<HTMLElement>) => Promise<void>;
  onChatUploadChange: (evt: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  onToggleSections?: () => void;
};

/**
 * The composer capsule.
 *
 * The gradient edge is not a border: `composer-ring` is an outer wrapper with
 * 1.5px of padding over a gradient background, and the inner panel sits on
 * top of it. That is why the two radii differ by exactly that padding
 * (`--composer-radius-outer` 1.5rem, `--composer-radius-inner` 1.4rem) --
 * change one without the other and the ring goes visibly uneven at the
 * corners. Focus is handled by `:focus-within` on the wrapper, so tabbing
 * into the textarea lights the whole capsule.
 *
 * `composer-panel` stays on the root as a behavioural hook: `useSectionToggle`
 * hides the composer by class name.
 */
export function ChatComposer({
  questionRef,
  chatUploadInputRef,
  isSending,
  quickPrompts,
  onAsk,
  onStop,
  onComposerDragEnter,
  onComposerDragOver,
  onComposerDragLeave,
  onComposerDrop,
  onChatUploadChange,
  onToggleSections,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const question = useChatStore((s) => s.question);
  const setQuestion = useChatStore((s) => s.setQuestion);
  const runStatus = useChatStore((s) => s.runStatus);
  const composerDropActive = useChatStore((s) => s.composerDropActive);
  const useWebSearch = useChatStore((s) => s.useWebSearch);
  const setUseWebSearch = useChatStore((s) => s.setUseWebSearch);
  const showReasoning = useChatStore((s) => s.showReasoning);
  const setShowReasoning = useChatStore((s) => s.setShowReasoning);
  useTextareaAutoResize({ ref: questionRef, value: question });

  return (
    <section
      className="composer-panel relative z-20 mx-auto w-full max-w-4xl shrink-0 px-4 pb-3 pt-2"
      onDragEnter={onComposerDragEnter}
      onDragOver={onComposerDragOver}
      onDragLeave={onComposerDragLeave}
      onDrop={(event) => void onComposerDrop(event)}
    >
      <QuickActions
        quickPrompts={quickPrompts}
        question={question}
        isSending={isSending}
        onPromptPick={setQuestion}
        onStop={onStop}
        onClearQuestion={() => setQuestion("")}
      />

      <div
        className={cn(
          "composer-ring field-shell mt-2",
          composerDropActive && "scale-[1.01] bg-[image:var(--brand-mark-gradient)]"
        )}
      >
        <div className="glass-panel flex flex-col gap-2 rounded-[var(--composer-radius-inner)] border-line p-2">
          <textarea
            ref={questionRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("components.chat.composerPlaceholder")}
            rows={2}
            aria-label={t("components.chat.questionInput")}
            aria-describedby="composer-hint"
            className="max-h-48 w-full resize-none border-0 bg-transparent px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus-visible:outline-none focus-visible:ring-0 sm:text-sm"
            onKeyDown={(event) => {
              // Escape means "undo what I am in the middle of". While a answer
              // is streaming that is the run; otherwise it is the draft.
              // `KeyboardHelp` documented it as "clear input" and the handler
              // only ever stopped a run, so in the common case -- nothing
              // sending -- the key did nothing at all.
              if (event.key === "Escape") {
                if (isSending) {
                  event.preventDefault();
                  onStop();
                  return;
                }
                if (question) {
                  event.preventDefault();
                  setQuestion("");
                  return;
                }
              }
              if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                void onAsk();
              }
            }}
          />

          <div className="flex items-center justify-between gap-2 border-t border-line-subtle px-2 pt-1.5">
            <div className="flex min-w-0 items-center gap-1.5">
              <label
                className="inline-flex cursor-pointer items-center gap-1 rounded-control p-1.5 text-ink-muted transition-colors hover:bg-brand-surface hover:text-brand-text focus-within:ring-2 focus-within:ring-[var(--brand-ring)]"
                title={t("components.chat.uploadFiles")}
              >
                <Paperclip className="size-4" aria-hidden="true" />
                <span className="hidden text-xs sm:text-sm font-medium sm:inline">
                  {t("components.chat.uploadFiles")}
                </span>
                <input
                  ref={chatUploadInputRef}
                  type="file"
                  multiple
                  accept={CHAT_ACCEPT_ATTRIBUTE}
                  className="sr-only"
                  onChange={(event) => void onChatUploadChange(event)}
                  aria-label={t("components.chat.uploadFilesAria")}
                />
              </label>

              <button
                type="button"
                onClick={() => setUseWebSearch((prev) => !prev)}
                className={cn(
                  "inline-flex cursor-pointer items-center gap-1 rounded-control p-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  useWebSearch
                    ? "bg-brand-surface text-brand-text font-semibold ring-1 ring-[var(--brand-ring)]"
                    : "text-ink-muted hover:bg-brand-surface hover:text-brand-text"
                )}
                title={
                  useWebSearch
                    ? t("components.chat.webSearchEnabled", "联网检索已开启")
                    : t("components.chat.webSearchDisabled", "开启联网检索")
                }
                aria-label={t("components.chat.webSearchToggle", "切换联网检索")}
                aria-pressed={useWebSearch}
              >
                <Globe
                  className={cn("size-4 transition-transform", useWebSearch && "text-brand-text scale-110")}
                  aria-hidden="true"
                />
                <span className="hidden text-xs sm:text-sm font-medium sm:inline">
                  {t("components.chat.webSearch", "联网")}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setShowReasoning((prev) => !prev)}
                className={cn(
                  "inline-flex cursor-pointer items-center gap-1 rounded-control p-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  showReasoning
                    ? "bg-brand-surface text-brand-text font-semibold ring-1 ring-[var(--brand-ring)]"
                    : "text-ink-muted hover:bg-brand-surface hover:text-brand-text"
                )}
                title={
                  showReasoning
                    ? t("components.chat.deepReasoningEnabled", "已开启思考过程展示")
                    : t("components.chat.deepReasoningDisabled", "在回答前展示模型的思考过程")
                }
                aria-label={t("components.chat.deepReasoningToggle", "切换深度思考")}
                aria-pressed={showReasoning}
              >
                <Brain
                  className={cn("size-4 transition-transform", showReasoning && "text-brand-text scale-110")}
                  aria-hidden="true"
                />
                <span className="hidden text-xs sm:text-sm font-medium sm:inline">
                  {t("components.chat.deepReasoning", "深度思考")}
                </span>
              </button>

              <Badge variant="brand" size="pill" mono className="hidden truncate sm:inline-flex">
                {t("components.chat.modeHint.advancedReasoning")}
              </Badge>

              {onToggleSections && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={onToggleSections}
                  title={t("components.chat.hideSections")}
                  aria-label={t("components.chat.hideSections")}
                >
                  <EyeOff aria-hidden="true" />
                </Button>
              )}
            </div>

            <div className="flex shrink-0 items-center gap-1.5">
              {question && !isSending && (
                <Button variant="ghost" size="sm" onClick={() => setQuestion("")}>
                  {t("common.clear", "Clear")}
                </Button>
              )}
              {isSending ? (
                <Button variant="destructive" onClick={onStop}>
                  <Square className="size-3" aria-hidden="true" />
                  <span>{t("components.chat.stop", "Stop")}</span>
                </Button>
              ) : (
                <Button onClick={() => void onAsk()} disabled={!question.trim()}>
                  <span>{t("components.chat.startAnalysis")}</span>
                  <ArrowRight className="size-3.5" aria-hidden="true" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <p className="mt-1 text-center text-xs text-ink/75" id="composer-hint">
        <kbd className="rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-xs text-ink">Ctrl</kbd>
        {" / "}
        <kbd className="rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-xs text-ink">Cmd</kbd>
        {" + "}
        <kbd className="rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-xs text-ink">
          Enter
        </kbd>{" "}
        {t("components.chat.composerDropHint")}
      </p>

      {/* RUN_STATUS_PROCESSING is deliberately excluded: `ChatRuntimePanels`
          shows `GenerationStatusLine` for that state instead -- a ticking
          clock and a phrase grounded in the actual execution trace, not a
          static word. This line stays for the other transient states (no
          execution id exists yet to drive that richer view). */}
      {runStatus && runStatus !== RUN_STATUS_PROCESSING && (
        <output className="mt-1 flex items-center justify-center gap-1.5 text-xs font-semibold text-brand-text">
          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
          {t(`chat.runStatus.${runStatus.toLowerCase().replace(/[^a-z_]/g, "")}`, { defaultValue: runStatus })}
        </output>
      )}
    </section>
  );
}
