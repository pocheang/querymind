import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

import { confirmToolApproval } from "./toolApprovalApi";
import type { PendingApproval } from "@/types/api";

type Props = {
  approval: PendingApproval | null;
  /** Re-run the request carrying the approved token. Confirming alone does not
   *  perform the action: it marks the token approved, and the run that replays
   *  it is what reaches the executor. This panel used to stop after confirming,
   *  so the action the user approved never actually happened. */
  onApproved: (token: string) => Promise<void> | void;
  onDismiss: () => void;
};

export function ToolApprovalPanel({ approval, onApproved, onDismiss }: Readonly<Props>) {
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!approval) return null;

  const confirm = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await confirmToolApproval(approval.token);
      await onApproved(approval.token);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : t("features.toolApproval.errorFallback"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    /* `tool-approval-panel` is a behavioural hook for useSectionToggle. The
       buttons carried no styling at all before -- browser defaults on a warm
       ground. */
    <section
      className="tool-approval-panel mx-auto w-full max-w-4xl shrink-0 px-4 pb-1"
      aria-label={t("features.toolApproval.ariaLabel")}
    >
      <div className="glass-card space-y-2 rounded-card border-2 border-warning-border bg-warning-surface/70 p-3">
        <h2 className="flex items-center gap-1.5 text-[11px] font-bold text-ink">
          <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
          {t("features.toolApproval.title")}
        </h2>
        <p className="font-mono text-[11px] text-ink">{approval.summary || approval.tool_id}</p>
        {error ? (
          <p className="text-[11px] text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => void confirm()} disabled={submitting}>
            {submitting ? t("features.toolApproval.confirming") : t("features.toolApproval.confirm")}
          </Button>
          <Button variant="secondary" size="sm" onClick={onDismiss} disabled={submitting}>
            {t("features.toolApproval.dismiss", "Not now")}
          </Button>
        </div>
      </div>
    </section>
  );
}
