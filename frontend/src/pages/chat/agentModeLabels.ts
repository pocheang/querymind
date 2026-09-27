import { useTranslation } from "react-i18next";

import type { AgentMode } from "@/pages/chat/types";

/**
 * An agent mode's title and description, in the reader's language.
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
 * shows a word rather than a key path. Shared by the mode cards and the
 * document label selector, so a class is named the same way in both.
 */
export function useAgentModeLabels() {
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
