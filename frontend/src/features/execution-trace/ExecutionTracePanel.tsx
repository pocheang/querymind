import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ExecutionTraceState } from "./state";
import { groupExecutionEvents } from "./traceFormatter";
import type { ExecutionStage, ExecutionStatus } from "./types";
import { TraceControlsHeader } from "./TraceControlsHeader";
import { TraceTimelineItem } from "./TraceTimelineItem";
import { TraceRawView } from "./TraceRawView";

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

export function ExecutionTracePanel({ trace }: Readonly<Props>) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [viewMode, setViewMode] = useState<"structured" | "raw">(readViewMode);

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

  const renderTraceBody = () => {
    if (trace.events.length === 0) {
      return <p className="text-xs text-ink/75">{t("features.executionTrace.empty")}</p>;
    }

    if (viewMode === "raw") {
      return <TraceRawView events={trace.events} stageLabel={stageLabel} />;
    }

    return (
      <div className="space-y-2">
        <div className="relative pl-6 before:absolute before:bottom-3 before:left-2.5 before:top-3 before:w-px before:bg-line-subtle">
          {stages.map((stageItem) => (
            <TraceTimelineItem
              key={stageItem.id}
              stageItem={stageItem}
              roundsCount={summary.roundsCount}
              stageLabel={stageLabel}
              sourceLabel={sourceLabel}
              statusLabel={statusLabel}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <section
      className="execution-trace-panel mx-auto w-full max-w-4xl shrink-0 px-4 pb-1"
      aria-label={t("features.executionTrace.ariaLabel")}
    >
      <div className="glass-card rounded-card p-3 transition-all">
        <TraceControlsHeader
          isComplete={summary.isComplete}
          eventsCount={trace.events.length}
          collapsed={collapsed}
          totalDurationMs={summary.totalDurationMs}
          roundsCount={summary.roundsCount}
          viewMode={viewMode}
          onToggle={toggle}
          onChangeViewMode={changeViewMode}
        />

        <div id="execution-trace-events" hidden={collapsed} className="mt-2.5 border-t border-line-subtle pt-2.5">
          {renderTraceBody()}
        </div>
      </div>
    </section>
  );
}
