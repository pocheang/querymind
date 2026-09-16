import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Brain, ChevronDown, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { MarkdownBlock } from "@/pages/chat/components/MarkdownBlock";

type Props = {
  reasoning: string;
  /** Measured server-side and only ever present on the final response, so it
   *  is undefined for the whole time this message is still the streaming
   *  placeholder -- including after reasoning has ended and the answer has
   *  started. Absent means "not known", which is why the header falls back to
   *  a label with no number rather than reporting a duration of zero. */
  durationMs?: number;
  /** True only while this specific message is still streaming reasoning --
   *  the placeholder message AND the answer channel has not started yet.
   *  Once the answer starts (or the message is persisted/reloaded), the
   *  split has already resolved and this is false, even if `durationMs`
   *  has not been reported. */
  isStreaming: boolean;
};

/** Three states, not two: still writing reasoning, finished with a measured
 *  duration, and finished without one (see `Props.durationMs`). Literal `t()`
 *  keys, never an interpolated one -- `i18n/locales.test.ts` scans for literal
 *  calls, and a key it cannot see renders English forever in silence. */
function labelFor(isStreaming: boolean, hasDuration: boolean, seconds: number, t: TFunction): string {
  if (isStreaming) return t("components.messages.thinkingInProgress");
  if (hasDuration) return t("components.messages.thoughtFor", { seconds, defaultValue: `Thought for ${seconds}s` });
  return t("components.messages.thoughtComplete", { defaultValue: "Reasoning" });
}

/**
 * A collapsible panel showing the model's own reasoning, above the answer.
 * Mirrors the interaction shape `MessageCard`'s existing "Thought for Ns"
 * toggle already uses for `execution_steps` (chevron + button, collapsed by
 * default) -- here applied to actual model-written reasoning text instead of
 * pipeline stage names, and keyed on a real measured duration rather than
 * one derived from stage timestamps.
 *
 * Only ever rendered with content: `reasoning` is empty exactly when the
 * request did not opt in to visible reasoning, or the model produced none.
 */
export function ThinkingPanel({ reasoning, durationMs, isStreaming }: Readonly<Props>) {
  const { t } = useTranslation();
  // `null` means "no manual choice yet" -- default to following the stream.
  // Once a reader clicks, their choice sticks regardless of how the stream
  // state changes afterward (e.g. reasoning finishing must not yank open
  // panel closed if they had already collapsed it while it was still live).
  const [userExpanded, setUserExpanded] = useState<boolean | null>(null);
  if (!reasoning) return null;
  const expanded = userExpanded ?? isStreaming;
  // `durationMs` arrives with the final response; `isStreaming` goes false as
  // soon as the ANSWER channel starts. Between those two moments -- which is
  // however long the answer takes to stream -- there is no measured duration,
  // and `durationMs || 0` reported that gap as a confident "Thought for 0s".
  const seconds = Math.round((durationMs ?? 0) / 1000);
  // Also covers a real duration that rounds to zero: "Thought for 0s" is the
  // same wrong claim whether the number is missing or merely sub-second.
  const hasDuration = typeof durationMs === "number" && seconds > 0;

  return (
    // Opaque, not `/60`: an alpha tint over the aurora has no fixed contrast,
    // and a contrast audit skips it entirely -- as the memory panel's did.
    <div className="overflow-hidden rounded-card border border-line-subtle bg-surface-muted">
      <button
        type="button"
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-semibold text-ink/80 transition-colors hover:text-brand-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] sm:text-sm"
        onClick={() => setUserExpanded(!expanded)}
        // Deliberately no aria-label. The button's own text is "Thinking...",
        // "Thought for 12s" or "Reasoning" -- the state a reader is being
        // shown -- and an aria-label REPLACES that as the accessible name, so
        // a generic "expand or collapse reasoning" was the one thing a screen
        // reader heard and the duration never reached it. `aria-expanded`
        // already carries the toggle affordance. (`CollapsibleSection` next
        // door keeps its own aria-label, correctly: its titles are static
        // nouns, so naming the action there costs nothing.)
        aria-expanded={expanded}
      >
        {isStreaming ? (
          <Loader2 className="size-3.5 shrink-0 animate-spin text-brand-text" aria-hidden="true" />
        ) : (
          <Brain className="size-3.5 shrink-0 text-brand-text" aria-hidden="true" />
        )}
        <span className="flex-1">{labelFor(isStreaming, hasDuration, seconds, t)}</span>
        <ChevronDown
          className={cn("size-3.5 shrink-0 transition-transform", expanded && "rotate-180")}
          aria-hidden="true"
        />
      </button>

      {expanded && (
        <div className="border-t border-line-subtle px-3 py-2.5 text-xs leading-relaxed text-ink/85 select-text sm:text-sm">
          <MarkdownBlock text={reasoning} />
        </div>
      )}
    </div>
  );
}
