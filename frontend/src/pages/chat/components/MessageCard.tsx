import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, Pencil, Trash2, Zap } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SessionMessage } from "@/types/api";
import { EMPTY_METADATA } from "@/pages/chat/constants";
import { MarkdownBlock } from "@/pages/chat/components/MarkdownBlock";
import { CollapsibleSection } from "@/pages/chat/components/CollapsibleSection";
import { MetadataBadges } from "@/pages/chat/components/MetadataBadges";
import { MessageGraphPanel } from "@/pages/chat/components/MessageGraphPanel";
import { ThinkingIndicator } from "@/pages/chat/components/ThinkingIndicator";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useConfirmDialog } from "@/hooks/useConfirmDialog";

type Props = {
  message: SessionMessage;
  onEditMessage: (msg: SessionMessage) => Promise<void>;
  onRemoveMessage: (msg: SessionMessage) => Promise<void>;
};

/**
 * One conversation turn.
 *
 * The two roles are laid out differently on purpose, following the design:
 * the user's turn is right-aligned with its metadata ABOVE the bubble and an
 * avatar to the right; the assistant's is left-aligned with a gradient mark
 * and a glass card holding a stack of blocks (execution trace, thoughts, tool
 * runs, answer, citations, graph). The mirrored corner -- `rounded-tr-sm` on
 * one, `rounded-tl-sm` on the other -- is the speech tail.
 */
export function MessageCard({ message, onEditMessage, onRemoveMessage }: Readonly<Props>) {
  const { t, i18n } = useTranslation();
  const isAssistant = message.role === "assistant";
  const metadata = message.metadata || EMPTY_METADATA;
  const timeLocale = i18n.language === "zh" ? "zh-CN" : "en-US";
  const [processExpanded, setProcessExpanded] = useState(false);
  const confirmDialog = useConfirmDialog();

  const isStreaming = message.message_id === "local-assistant-stream";
  const isThinking = isStreaming && !message.content;
  const isGenerating = isStreaming && !!message.content;
  const hasExecutionSteps = (metadata.execution_steps || []).length > 0;
  const isPersisted = !!message.message_id && !message.message_id.startsWith("local-");

  const getElapsedSeconds = () => {
    if (!hasExecutionSteps) return 0;
    const steps = metadata.execution_steps || [];
    const firstStep = steps[0];
    const lastStep = steps[steps.length - 1];
    if (!firstStep?.at || !lastStep?.at) return 0;
    const start = new Date(firstStep.at).getTime();
    const end = new Date(lastStep.at).getTime();
    return Math.round((end - start) / 1000);
  };

  const timestamp = message.created_at
    ? new Date(message.created_at).toLocaleTimeString(timeLocale, { hour: "2-digit", minute: "2-digit" })
    : "";

  const rowActions = isPersisted && (
    <div className="flex items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={() => void onEditMessage(message)}
        title={t("components.messages.edit")}
      >
        <Pencil aria-hidden="true" />
        <span className="sr-only">{t("components.messages.edit")}</span>
      </Button>
      <Button
        variant="destructive-ghost"
        size="icon-sm"
        title={t("components.messages.delete")}
        onClick={async () => {
          const confirmMsg = isAssistant
            ? t("components.messages.deleteAssistantConfirm")
            : t("components.messages.deleteUserConfirm");
          const confirmed = await confirmDialog.confirm({ message: confirmMsg, isDanger: true });
          if (confirmed) await onRemoveMessage(message);
        }}
      >
        <Trash2 aria-hidden="true" />
        <span className="sr-only">{t("components.messages.delete")}</span>
      </Button>
    </div>
  );

  if (!isAssistant) {
    return (
      <>
        <article
          className="bubble user group flex items-start justify-end gap-3"
          aria-label={t("components.messages.userMessage")}
        >
          <div className="min-w-0 max-w-2xl space-y-1">
            <div className="flex items-center justify-end gap-2 text-[11px] text-ink-muted">
              {rowActions}
              {timestamp && <span className="font-mono">{timestamp}</span>}
              <span className="font-semibold text-ink">{t("components.messages.you")}</span>
            </div>
            <div className="glass-panel rounded-panel rounded-tr-sm border-brand-border bg-brand-surface/80 p-3.5 text-left text-xs text-brand-text-strong shadow-elev-1 sm:text-sm">
              <MarkdownBlock text={message.content || ""} />
            </div>
          </div>
          <span
            className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-control border border-brand-border-strong bg-surface text-[11px] font-bold text-brand-text"
            aria-hidden="true"
          >
            {t("components.messages.you").slice(0, 1).toUpperCase()}
          </span>
        </article>
        <ConfirmDialog
          isOpen={confirmDialog.isOpen}
          title={t("components.messages.delete")}
          message={confirmDialog.options?.message || ""}
          isDanger={confirmDialog.options?.isDanger}
          onConfirm={confirmDialog.handleConfirm}
          onCancel={confirmDialog.handleCancel}
        />
      </>
    );
  }

  return (
    <>
      <article
        className="bubble assistant group flex items-start justify-start gap-3"
        aria-label={t("components.messages.assistantReply")}
      >
        <span
          className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-control bg-[image:var(--brand-mark-gradient)] text-white shadow-elev-2 ring-2 ring-brand-border"
          aria-hidden="true"
        >
          <Zap className="size-4" strokeWidth={2} />
        </span>

        <div className="min-w-0 max-w-3xl flex-1 space-y-2">
          <div className="flex items-center gap-2 text-[11px] text-ink-muted">
            <span className="flex items-center gap-1 font-bold text-brand-text-strong">
              {t("components.messages.assistant")}
              <span className="size-1.5 rounded-pill bg-success" aria-hidden="true" />
            </span>
            {timestamp && (
              <>
                <span aria-hidden="true">&bull;</span>
                <span className="font-mono">{timestamp}</span>
              </>
            )}
            {rowActions}
          </div>

          <div className="glass-card space-y-3 rounded-panel rounded-tl-sm p-4">
            {isThinking ? (
              <ThinkingIndicator elapsedSeconds={getElapsedSeconds()} />
            ) : (
              <div className="markdown select-text text-xs text-ink sm:text-sm">
                <MarkdownBlock text={message.content || ""} />
                {isGenerating && (
                  <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-brand-accent align-middle" />
                )}
              </div>
            )}

            {!isThinking && (
              <>
                <MetadataBadges metadata={metadata} />

                {hasExecutionSteps && (
                  <div className="space-y-2">
                    <button
                      type="button"
                      className="flex items-center gap-1.5 rounded-control text-[11px] font-medium text-ink-muted transition-colors hover:text-brand-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
                      onClick={() => setProcessExpanded(!processExpanded)}
                      aria-expanded={processExpanded}
                    >
                      <ChevronDown
                        className={cn("size-3 transition-transform", processExpanded && "rotate-180")}
                        aria-hidden="true"
                      />
                      {t("components.messages.thoughtFor", {
                        seconds: getElapsedSeconds(),
                        defaultValue: `Thought for ${getElapsedSeconds()}s`,
                      })}
                    </button>

                    {processExpanded && (
                      <ol className="space-y-1 border-l-2 border-brand-border pl-3">
                        {(metadata.execution_steps || [])
                          .filter(
                            (step) =>
                              !["execution started", "trace", "STATUS"].some((tech) =>
                                step.label?.toLowerCase().includes(tech.toLowerCase())
                              )
                          )
                          .map((step, index) => (
                            <li key={`${message.message_id}-step-${index}`} className="text-[11px]">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <Badge variant="info" size="xs" mono className="uppercase">
                                  {step.kind || "step"}
                                </Badge>
                                <strong className="font-semibold text-ink">
                                  {step.label || t("components.messages.processing")}
                                </strong>
                                {step.at && (
                                  <span className="font-mono text-[10px] text-ink-faint">
                                    {new Date(step.at).toLocaleTimeString(timeLocale, { hour12: false })}
                                  </span>
                                )}
                              </div>
                              {step.detail && <p className="mt-0.5 text-ink-muted">{step.detail}</p>}
                            </li>
                          ))}
                      </ol>
                    )}
                  </div>
                )}

                {(metadata.thoughts || []).length > 0 && (
                  <CollapsibleSection
                    title={t("components.messages.thoughts")}
                    ariaLabel={t("components.messages.toggleThoughts")}
                  >
                    <ul className="space-y-1 text-[11px] text-ink-muted">
                      {(metadata.thoughts || []).slice(-8).map((thought, index) => (
                        <li key={`${message.message_id}-thought-${index}`}>{thought}</li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                )}

                {(metadata.tool_runs || []).length > 0 && (
                  <CollapsibleSection
                    title={t("components.messages.toolRuns")}
                    ariaLabel={t("components.messages.toggleToolRuns")}
                  >
                    <ul className="space-y-1 text-[11px]">
                      {(metadata.tool_runs || []).map((run, index) => (
                        <li key={`${message.message_id}-tool-${index}`} className="flex flex-wrap items-center gap-1.5">
                          <Badge variant="brand" size="xs" mono>
                            {run.tool_id}
                          </Badge>
                          <span className="text-ink-muted">
                            {t(`components.messages.toolStatus.${run.status}`, { defaultValue: run.status })}
                            {run.summary ? `: ${run.summary}` : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                )}

                {(metadata.citations || []).length > 0 && (
                  <CollapsibleSection
                    title={t("components.messages.citations")}
                    ariaLabel={t("components.messages.toggleCitations")}
                  >
                    {/* Not truncated: the answer cites these by number, so hiding
                        an entry leaves a [n] in the text resolving to nothing. */}
                    <div className="space-y-1.5">
                      {(metadata.citations || []).map((citation, index) => (
                        <div
                          key={`${message.message_id}-cit-${index}`}
                          className="rounded-control border border-brand-border bg-brand-surface/60 p-2"
                        >
                          <div className="flex items-center gap-1.5">
                            {citation.marker && (
                              <span className="flex size-4 shrink-0 items-center justify-center rounded bg-brand font-mono text-[9px] font-bold text-white">
                                {citation.marker.replace(/[[\]]/g, "")}
                              </span>
                            )}
                            <span className="truncate font-mono text-[11px] font-semibold text-brand-text-strong">
                              {citation.source || "unknown"}
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] text-ink-muted select-text">
                            <MarkdownBlock text={citation.content || ""} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {metadata.quality_report && Object.keys(metadata.quality_report).length > 0 && (
                  <CollapsibleSection
                    title={t("components.messages.qualityReport")}
                    ariaLabel={t("components.messages.toggleQualityReport")}
                  >
                    <pre className="max-h-48 overflow-auto rounded-control border border-line bg-surface p-2 font-mono text-[10px] text-ink select-text">
                      {JSON.stringify(metadata.quality_report, null, 2)}
                    </pre>
                  </CollapsibleSection>
                )}

                {metadata.graph_result &&
                  (metadata.graph_result.neighbors.length > 0 || metadata.graph_result.paths.length > 0) && (
                    <CollapsibleSection
                      title={t("components.messages.graph")}
                      ariaLabel={t("components.messages.toggleGraph")}
                    >
                      <MessageGraphPanel graph={metadata.graph_result} keyPrefix={message.message_id || "message"} />
                    </CollapsibleSection>
                  )}
              </>
            )}
          </div>
        </div>
      </article>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={t("components.messages.delete")}
        message={confirmDialog.options?.message || ""}
        isDanger={confirmDialog.options?.isDanger}
        onConfirm={confirmDialog.handleConfirm}
        onCancel={confirmDialog.handleCancel}
      />
    </>
  );
}
