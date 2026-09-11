import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  CheckCheck,
  CheckCircle2,
  Compass,
  Database,
  FileText,
  Filter,
  Globe,
  Layers,
  MinusCircle,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDuration, type StructuredStage, type SubSourceItem } from "./traceFormatter";
import type { ExecutionStage, ExecutionStatus } from "./types";

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

function getSourceIcon(sourceKey: string) {
  if (sourceKey.includes("web")) return Globe;
  return Database;
}

interface TraceTimelineItemProps {
  stageItem: StructuredStage;
  roundsCount: number;
  stageLabel: (stage: ExecutionStage) => string;
  sourceLabel: (sourceKey: string) => string;
  statusLabel: (status: ExecutionStatus) => string;
}

export function TraceTimelineItem({
  stageItem,
  roundsCount,
  stageLabel,
  sourceLabel,
  statusLabel,
}: Readonly<TraceTimelineItemProps>) {
  const { t } = useTranslation();
  const StageIcon = getStageIcon(stageItem.stage);
  const isSkipped = stageItem.status === "skipped";
  const isFailed = stageItem.status === "failed";

  let nodeBadgeClass = "border-success-border bg-success-surface text-success";
  if (isFailed) {
    nodeBadgeClass = "border-danger-border bg-danger-surface text-danger";
  } else if (isSkipped) {
    nodeBadgeClass = "border-line bg-surface-muted text-ink-faint";
  }

  return (
    <div className="relative mb-3 last:mb-0">
      {/* Timeline node icon */}
      <div
        className={`absolute -left-6 top-0.5 flex size-5 items-center justify-center rounded-pill border ${nodeBadgeClass}`}
        aria-hidden="true"
      >
        <StageIcon className="size-3" />
      </div>

      {/* Stage Body */}
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-1.5 text-xs sm:text-sm">
          <span className="font-semibold text-ink">{stageLabel(stageItem.stage)}</span>

          {/* Round badge if multi-round */}
          {stageItem.round && roundsCount > 1 && (
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
            {stageItem.subSources.map((sub: SubSourceItem) => {
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
}
