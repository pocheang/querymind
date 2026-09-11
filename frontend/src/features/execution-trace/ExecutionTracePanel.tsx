import { useCallback, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  Check,
  CheckCheck,
  CheckCircle2,
  Clock,
  Compass,
  Copy,
  Database,
  FileText,
  Filter,
  Globe,
  Layers,
  MinusCircle,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ExecutionTraceState } from "./state";
import { formatDuration, groupExecutionEvents } from "./traceFormatter";
import type { ExecutionStage, ExecutionStatus } from "./types";

type Props = { trace: ExecutionTraceState };

const COLLAPSE_KEY = "querymind.executionTrace.collapsed";
const VIEW_MODE_KEY = "querymind.executionTrace.viewMode";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  } catch {
    // Storage preference is non-critical
  }
}

function readViewMode(): "structured" | "raw" {
  try {
    return window.localStorage.getItem(VIEW_MODE_KEY) === "raw" ? "raw" : "structured";
  } catch {
    return "structured";
  }
}

function writeViewMode(mode: "structured" | "raw"): void {
  try {
    window.localStorage.setItem(VIEW_MODE_KEY, mode);
  } catch {
    // Storage preference is non-critical
  }
}

/**
 * Return stage icon based on the execution phase
 */
function getStageIcon(stage: ExecutionStage) {
  switch (stage) {
    case "privacy_permission":
      return ShieldCheck;
    case "route":
      return Compass;
    case "plan":
      return FileText;
    case "knowledge_strategy":
    case "knowledge":
    case "rag":
      return Search;
    case "synthesize":
      return Sparkles;
    case "verifier":
      return CheckCheck;
    case "finalize":
      return CheckCircle2;
    case "output_filter":
      return Filter;
    case "complete":
      return CheckCircle2;
    case "failed":
      return AlertCircle;
    default:
      return Layers;
  }
}

/**
 * Return source icon for retrieval sub-sources
 */
function getSourceIcon(sourceKey: string) {
  if (sourceKey.includes("web")) return Globe;
  return Database;
}

export function ExecutionTracePanel({ trace }: Readonly<Props>) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [viewMode, setViewMode] = useState<"structured" | "raw">(readViewMode);
  const [copied, setCopied] = useState(false);

  const toggle = useCallback(() => {
    setCollapsed((previous) => {
      writeCollapsed(!previous);
      return !previous;
    });
  }, []);

  const changeViewMode = useCallback((mode: "structured" | "raw") => {
    setViewMode(mode);
    writeViewMode(mode);
  }, []);

  const { stages, summary } = useMemo(() => {
    return groupExecutionEvents(trace.events);
  }, [trace.events]);

  const stageLabel = useCallback(
    (stage: ExecutionStage) => t(`features.executionTrace.stages.${stage}`, { defaultValue: stage }),
    [t]
  );

  const sourceLabel = useCallback(
    (sourceKey: string) =>
      t(`features.executionTrace.sources.${sourceKey}`, {
        defaultValue: sourceKey.toUpperCase(),
      }),
    [t]
  );

  const statusLabel = useCallback(
    (status: ExecutionStatus) =>
      t(`features.executionTrace.status.${status}`, {
        defaultValue: status,
      }),
    [t]
  );

  const copyRawLog = useCallback(() => {
    const rawText = trace.events
      .map((e, index) => {
        const stage = stageLabel(e.stage);
        const msg = e.message || e.status;
        return `${index + 1}. ${stage}: ${msg} (${e.duration_ms}ms)`;
      })
      .join("\n");

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(rawText).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }, [trace.events, stageLabel]);

  return (
    <section
      className="execution-trace-panel mx-auto w-full max-w-4xl shrink-0 px-4 pb-1"
      aria-label={t("features.executionTrace.ariaLabel")}
    >
      <div className="glass-card rounded-card p-3 transition-all">
        {/* Header bar */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="execution-trace-heading" className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-ink">
              {summary.isComplete ? (
                <CheckCircle2 className="size-3.5 text-success" aria-hidden="true" />
              ) : (
                <span className="relative flex size-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-pill bg-success opacity-75" />
                  <span className="relative inline-flex size-2.5 rounded-pill bg-success" />
                </span>
              )}
              {t("features.executionTrace.title")}
            </h2>

            {/* When collapsed, show the step count badge for test contract & immediate feedback */}
            {collapsed && trace.events.length > 0 ? (
              <Badge variant="brand" size="xs" mono>
                {t("features.executionTrace.count", { count: trace.events.length })}
              </Badge>
            ) : null}

            {/* Quick Metrics when expanded */}
            {!collapsed && trace.events.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant="neutral" size="xs" mono className="text-ink/80">
                  <Clock className="size-3.5" aria-hidden="true" />
                  {formatDuration(summary.totalDurationMs)}
                </Badge>
                {summary.roundsCount > 1 && (
                  <Badge variant="warning" size="xs">
                    {t("features.executionTrace.summary.rounds", { count: summary.roundsCount })}
                  </Badge>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {/* View Mode Toggle (Structured vs Raw) */}
            {!collapsed && trace.events.length > 0 && (
              <div className="flex items-center rounded-control border border-line-subtle bg-surface-inset/60 p-0.5">
                <button
                  type="button"
                  onClick={() => changeViewMode("structured")}
                  className={`flex size-6 items-center justify-center rounded transition-colors ${
                    viewMode === "structured"
                      ? "bg-surface text-ink shadow-xs"
                      : "text-ink-muted hover:text-ink"
                  }`}
                  title={t("features.executionTrace.views.structured")}
                  aria-label={t("features.executionTrace.views.structured")}
                >
                  <Layers className="size-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => changeViewMode("raw")}
                  className={`flex size-6 items-center justify-center rounded transition-colors ${
                    viewMode === "raw"
                      ? "bg-surface text-ink shadow-xs"
                      : "text-ink-muted hover:text-ink"
                  }`}
                  title={t("features.executionTrace.views.raw")}
                  aria-label={t("features.executionTrace.views.raw")}
                >
                  <Terminal className="size-3.5" aria-hidden="true" />
                </button>
              </div>
            )}

            {/* Collapse / Expand Toggle */}
            <Button
              variant="ghost"
              size="xs"
              onClick={toggle}
              aria-expanded={!collapsed}
              aria-controls="execution-trace-events"
            >
              {t(collapsed ? "features.executionTrace.show" : "features.executionTrace.hide")}
            </Button>
          </div>
        </div>

        {/* Content Container (Pinned id & hidden attribute for test suite) */}
        <div id="execution-trace-events" hidden={collapsed} className="mt-2.5 border-t border-line-subtle pt-2.5">
          {trace.events.length === 0 ? (
            <p className="text-xs text-ink/75">{t("features.executionTrace.empty")}</p>
          ) : viewMode === "raw" ? (
            /* Raw Log View */
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-ink/75">
                <span>{t("features.executionTrace.count", { count: trace.events.length })}</span>
                <Button variant="ghost" size="xs" onClick={copyRawLog} className="h-6 gap-1 px-2 text-xs">
                  {copied ? (
                    <>
                      <Check className="size-3.5 text-success" aria-hidden="true" />
                      {t("features.executionTrace.summary.copied")}
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5" aria-hidden="true" />
                      {t("features.executionTrace.summary.copy")}
                    </>
                  )}
                </Button>
              </div>
              <ol className="max-h-64 space-y-1 overflow-y-auto rounded-control border border-line-subtle bg-surface-inset/70 p-2.5 font-mono text-xs">
                {trace.events.map((event, index) => (
                  <li
                    key={`${event.occurred_at}-${index}`}
                    className="flex items-baseline gap-2 border-b border-line-subtle/30 pb-0.5 last:border-0 last:pb-0 text-ink/80"
                  >
                    <span className="w-5 shrink-0 select-none text-right text-ink/60">
                      {String(index + 1).padStart(2, "0")}.
                    </span>
                    <span className="min-w-0 flex-1 truncate">
                      {t("features.executionTrace.event", {
                        stage: stageLabel(event.stage),
                        message: event.message || event.status,
                        duration: event.duration_ms,
                      })}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            /* Structured Timeline View */
            <div className="space-y-2">
              <div className="relative pl-6 before:absolute before:bottom-3 before:left-2.5 before:top-3 before:w-px before:bg-line-subtle">
                {stages.map((stageItem) => {
                  const StageIcon = getStageIcon(stageItem.stage);
                  const isSkipped = stageItem.status === "skipped";
                  const isFailed = stageItem.status === "failed";

                  return (
                    <div key={stageItem.id} className="relative mb-3 last:mb-0">
                      {/* Timeline node icon */}
                      <div
                        className={`absolute -left-6 top-0.5 flex size-5 items-center justify-center rounded-pill border ${
                          isFailed
                            ? "border-danger-border bg-danger-surface text-danger"
                            : isSkipped
                            ? "border-line bg-surface-muted text-ink-faint"
                            : "border-success-border bg-success-surface text-success"
                        }`}
                        aria-hidden="true"
                      >
                        <StageIcon className="size-3" />
                      </div>

                      {/* Stage Body */}
                      <div className="flex flex-col gap-1">
                        <div className="flex flex-wrap items-center gap-1.5 text-xs sm:text-sm">
                          <span className="font-semibold text-ink">{stageLabel(stageItem.stage)}</span>

                          {/* Round badge if multi-round */}
                          {stageItem.round && summary.roundsCount > 1 && (
                            <Badge variant={stageItem.isRefinement ? "warning" : "neutral"} size="xs">
                              {stageItem.isRefinement
                                ? t("features.executionTrace.round", { number: stageItem.round })
                                : t("features.executionTrace.round", { number: 1 })}
                            </Badge>
                          )}

                          {/* Status Badge if skipped or failed */}
                          {isSkipped && (
                            <Badge variant="neutral" size="xs">
                              <MinusCircle className="size-3" aria-hidden="true" />
                              {statusLabel("skipped")}
                            </Badge>
                          )}
                          {isFailed && (
                            <Badge variant="danger" size="xs">
                              <AlertCircle className="size-3" aria-hidden="true" />
                              {statusLabel("failed")}
                            </Badge>
                          )}

                          {/* Duration Badge */}
                          <span className="font-mono text-xs text-ink/75">
                            ({formatDuration(stageItem.duration_ms)})
                          </span>
                        </div>

                        {/* Sub-sources (e.g. Vector, BM25, Web search) */}
                        {stageItem.subSources && stageItem.subSources.length > 0 && (
                          <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                            {stageItem.subSources.map((sub) => {
                              const SourceIcon = getSourceIcon(sub.sourceKey);
                              const subSkipped = sub.status === "skipped";

                              return (
                                <div
                                  key={sub.id}
                                  className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs ${
                                    subSkipped
                                      ? "border-line/60 bg-surface-muted/60 text-ink/60"
                                      : "border-brand-border/60 bg-brand-surface/70 text-brand-text font-medium"
                                  }`}
                                >
                                  <SourceIcon className="size-3 opacity-70" aria-hidden="true" />
                                  <span>{sourceLabel(sub.sourceKey)}</span>
                                  {subSkipped ? (
                                    <span className="text-xs text-ink/60">({statusLabel("skipped")})</span>
                                  ) : (
                                    <span className="font-mono text-xs">
                                      {formatDuration(sub.duration_ms)}
                                      {sub.resultCount !== undefined
                                        ? ` · ${t("features.executionTrace.resultsCount", { count: sub.resultCount })}`
                                        : ""}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Extra detail / message if present and meaningful */}
                        {stageItem.message &&
                          !stageItem.message.toLowerCase().includes("completed") &&
                          !stageItem.message.toLowerCase().includes("retrieval") && (
                            <p className="text-xs text-ink/75">{stageItem.message}</p>
                          )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
