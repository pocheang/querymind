import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type AgentMode = {
  key: AgentClassHint;
  title: string;
  desc: string;
};

type Props = {
  agentClassHint: AgentClassHint;
  agentModes: AgentMode[];
  agentDistribution: Array<{ agent: string; count: number }>;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
};

export function AgentWorkbench({ agentClassHint, agentModes, agentDistribution, onSwitchAgentMode }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-ink-muted">
        {t("components.messages.current", { mode: agentClassHint || t("components.workbench.auto") })}
      </p>

      <div className="grid grid-cols-1 gap-1.5">
        {agentModes.map((mode) => {
          const active = agentClassHint === mode.key;
          return (
            <button
              key={mode.title}
              type="button"
              className={cn(
                "rounded-control border p-2 text-left transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                active
                  ? "border-brand-border-strong bg-brand-surface shadow-elev-1"
                  : "border-line bg-surface hover:border-brand-border hover:bg-brand-surface/60"
              )}
              /* One mode is in effect at a time, so these are a single-select
                 group, not four independent actions. Without this the selection
                 is carried by colour alone and is not announced at all. */
              aria-pressed={active}
              onClick={() => onSwitchAgentMode(mode.key)}
              title={`${mode.title}: ${mode.desc}`}
            >
              <strong className={cn("block text-[11px]", active ? "text-brand-text-strong" : "text-ink")}>
                {mode.title}
              </strong>
              <span className="mt-0.5 block text-[10px] leading-snug text-ink-muted">{mode.desc}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-1">
        {agentDistribution.length === 0 && (
          <span className="text-[10px] text-ink-muted">{t("components.messages.noIndexedDocs")}</span>
        )}
        {agentDistribution.map((item) => (
          <Badge key={item.agent} variant="neutral" size="xs" mono>
            {item.agent}: {item.count}
          </Badge>
        ))}
      </div>
    </div>
  );
}
