import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import type { ExecutionTraceState } from "./state";
import type { ExecutionStage } from "./types";

type Props = { trace: ExecutionTraceState };

const COLLAPSE_KEY = "querymind.executionTrace.collapsed";

/**
 * The trace runs to ~18 lines on an ordinary query and pushes the answer off
 * screen, so the choice to see it has to be the reader's. It is remembered in
 * localStorage rather than component state because the panel unmounts between
 * questions -- re-collapsing it on every turn would make the button useless to
 * anyone who wants it shut.
 *
 * Every access is guarded: a private window, cleared site data, or a browser set
 * to block storage all make this throw, and none of them is a reason to fail to
 * render a trace.
 */
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
    // A remembered preference is a convenience, not a requirement.
  }
}

export function ExecutionTracePanel({ trace }: Readonly<Props>) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(readCollapsed);

  const toggle = useCallback(() => {
    setCollapsed((previous) => {
      writeCollapsed(!previous);
      return !previous;
    });
  }, []);

  // Falls back to the raw stage id so a stage added to the backend shows up
  // as itself rather than disappearing while the locale files catch up.
  const stageLabel = (stage: ExecutionStage) => t(`features.executionTrace.stages.${stage}`, { defaultValue: stage });

  return (
    /* `execution-trace-panel` is a behavioural hook: useSectionToggle hides
       this panel by class name. The test suite pins `aria-expanded`, the
       `id` below, and that hiding uses the `hidden` attribute rather than
       unmounting -- keep all three. */
    <section
      className="execution-trace-panel mx-auto w-full max-w-4xl shrink-0 px-4 pb-1"
      aria-label={t("features.executionTrace.ariaLabel")}
    >
      <div className="glass-card rounded-card p-2.5">
        <div className="flex items-center justify-between gap-2">
          <h2 id="execution-trace-heading" className="flex items-center gap-1.5 text-[11px] font-semibold text-ink">
            <span className="size-2 animate-pulse rounded-pill bg-success" aria-hidden="true" />
            {t("features.executionTrace.title")}
            {collapsed && trace.events.length > 0 ? (
              // Collapsed must not read as "nothing happened": the count is what
              // tells the reader there is something here to open.
              <Badge variant="brand" size="xs" mono>
                {t("features.executionTrace.count", { count: trace.events.length })}
              </Badge>
            ) : null}
          </h2>
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
        <div id="execution-trace-events" hidden={collapsed} className="mt-2 border-t border-line-subtle pt-2">
          {trace.events.length === 0 ? (
            <p className="text-[10px] text-ink-muted">{t("features.executionTrace.empty")}</p>
          ) : (
            <ol className="space-y-0.5">
              {trace.events.map((event, index) => (
                <li key={`${event.occurred_at}-${index}`} className="font-mono text-[10px] text-ink-muted">
                  {t("features.executionTrace.event", {
                    stage: stageLabel(event.stage),
                    message: event.message || event.status,
                    duration: event.duration_ms,
                  })}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}
