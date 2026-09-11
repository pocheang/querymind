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

/**
 * The five agent cards, in the reader's language.
 *
 * `AGENT_MODES` carries English `title`/`desc` literals and the component
 * rendered them straight, so switching to Chinese translated the whole sidebar
 * around these five cards and left them in English -- in an application whose
 * reason for existing is that it works in Chinese.
 *
 * `i18n/locales.test.ts` scans for LITERAL `t("...")` calls, so this is a switch
 * of literal keys rather than `t(`agentModes.${mode.key}.title`)`. An
 * interpolated key is invisible to that scan, and a locale entry missing behind
 * one renders English forever with nothing reporting it -- which is the same
 * failure, one level down.
 *
 * The constant's English stays as the fallback, so a key that has not landed yet
 * shows a word rather than a key path.
 */
function useAgentModeLabels() {
  const { t } = useTranslation();
  return (mode: AgentMode) => {
    switch (mode.key) {
      case "cybersecurity":
        return {
          title: t("agentModes.cybersecurity.title", mode.title),
          desc: t("agentModes.cybersecurity.desc", mode.desc),
        };
      case "artificial_intelligence":
        return {
          title: t("agentModes.artificialIntelligence.title", mode.title),
          desc: t("agentModes.artificialIntelligence.desc", mode.desc),
        };
      case "pdf_text":
        return {
          title: t("agentModes.pdfText.title", mode.title),
          desc: t("agentModes.pdfText.desc", mode.desc),
        };
      case "general":
        return {
          title: t("agentModes.general.title", mode.title),
          desc: t("agentModes.general.desc", mode.desc),
        };
      default:
        return {
          title: t("agentModes.auto.title", mode.title),
          desc: t("agentModes.auto.desc", mode.desc),
        };
    }
  };
}

export function AgentWorkbench({ agentClassHint, agentModes, agentDistribution, onSwitchAgentMode }: Readonly<Props>) {
  const { t } = useTranslation();
  const labelFor = useAgentModeLabels();

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-ink/75">
        {t("components.messages.current", { mode: agentClassHint || t("components.workbench.auto") })}
      </p>

      <div className="grid grid-cols-1 gap-1.5">
        {agentModes.map((mode) => {
          const active = agentClassHint === mode.key;
          const label = labelFor(mode);
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
              title={`${label.title}: ${label.desc}`}
            >
              <strong className={cn("block text-xs sm:text-sm font-semibold", active ? "text-brand-text-strong" : "text-ink")}>
                {label.title}
              </strong>
              <span className="mt-0.5 block text-xs leading-relaxed text-ink/75">{label.desc}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-1">
        {agentDistribution.length === 0 && (
          <span className="text-xs text-ink/75">{t("components.messages.noIndexedDocs")}</span>
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
