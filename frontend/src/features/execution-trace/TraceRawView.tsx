import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExecutionEvent, ExecutionStage } from "./types";

interface TraceRawViewProps {
  events: readonly ExecutionEvent[];
  stageLabel: (stage: ExecutionStage) => string;
}

export function TraceRawView({ events, stageLabel }: Readonly<TraceRawViewProps>) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copyRawLog = () => {
    const rawText = events
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
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-ink/75">
        <span>{t("features.executionTrace.count", { count: events.length })}</span>
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
        {events.map((event, index) => (
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
  );
}
