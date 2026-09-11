import { useTranslation } from "react-i18next";
import { CheckCircle2, Clock, Layers, Terminal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDuration } from "./traceFormatter";

interface TraceControlsHeaderProps {
  isComplete: boolean;
  eventsCount: number;
  collapsed: boolean;
  totalDurationMs: number;
  roundsCount: number;
  viewMode: "structured" | "raw";
  onToggle: () => void;
  onChangeViewMode: (mode: "structured" | "raw") => void;
}

export function TraceControlsHeader({
  isComplete,
  eventsCount,
  collapsed,
  totalDurationMs,
  roundsCount,
  viewMode,
  onToggle,
  onChangeViewMode,
}: Readonly<TraceControlsHeaderProps>) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="execution-trace-heading" className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-ink">
          {isComplete ? (
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
        {collapsed && eventsCount > 0 ? (
          <Badge variant="brand" size="xs" mono>
            {t("features.executionTrace.count", { count: eventsCount })}
          </Badge>
        ) : null}

        {/* Quick Metrics when expanded */}
        {!collapsed && eventsCount > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="neutral" size="xs" mono className="text-ink/80">
              <Clock className="size-3.5" aria-hidden="true" />
              {formatDuration(totalDurationMs)}
            </Badge>
            {roundsCount > 1 && (
              <Badge variant="warning" size="xs">
                {t("features.executionTrace.summary.rounds", { count: roundsCount })}
              </Badge>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        {/* View Mode Toggle (Structured vs Raw) */}
        {!collapsed && eventsCount > 0 && (
          <div className="flex items-center rounded-control border border-line-subtle bg-surface-inset/60 p-0.5">
            <button
              type="button"
              onClick={() => onChangeViewMode("structured")}
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
              onClick={() => onChangeViewMode("raw")}
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
          onClick={onToggle}
          className="h-7 px-2 text-xs text-ink/75"
          aria-expanded={!collapsed}
          aria-controls="execution-trace-events"
        >
          {t(collapsed ? "features.executionTrace.show" : "features.executionTrace.hide")}
        </Button>
      </div>
    </div>
  );
}
