import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { describeCurrentPhase } from "@/features/execution-trace/currentPhase";
import { formatElapsedClock } from "@/features/execution-trace/traceFormatter";
import type { ExecutionEvent } from "@/features/execution-trace/types";
import { useElapsedTime } from "@/pages/chat/hooks/useElapsedTime";

type Props = {
  events: readonly ExecutionEvent[];
  active: boolean;
};

/**
 * A live "what is it doing right now" line -- icon, a ticking clock, and a
 * short phrase -- shown while a run is in flight. Replaces the composer's
 * old plain "Processing" text, which gave no sense of progress or of how
 * long the wait had already been (found while live-testing the new
 * character-by-character streaming, 2026-09-15).
 */
export function GenerationStatusLine({ events, active }: Readonly<Props>) {
  const { t } = useTranslation();
  const elapsedMs = useElapsedTime(active);
  if (!active) return null;

  const phase = describeCurrentPhase(events);

  return (
    // `<output>` is an implicit `aria-live="polite"` region, which is what
    // makes the phase phrase announce itself as the run moves on. The clock
    // is inside it and changes every 250ms, so leaving it in the
    // accessibility tree turned one useful announcement per phase into four
    // announcements a second of a number nobody asked to hear. Hidden, the
    // region announces only when the phrase changes; a running timer is
    // decoration, and the phrase is the content.
    <output className="mx-auto flex w-full max-w-4xl items-center justify-center gap-1.5 px-4 pb-1 text-xs font-semibold text-brand-text">
      <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
      <span className="font-mono tabular-nums text-ink-muted" aria-hidden="true">
        {formatElapsedClock(elapsedMs)}
      </span>
      <span aria-hidden="true">·</span>
      <span>{t(`features.executionTrace.phase.${phase}`)}</span>
    </output>
  );
}
