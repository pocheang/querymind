import { useTranslation } from "react-i18next";
import { ArrowUpRight, Boxes, FileText, Globe, Images, Layers, Plus, Route, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/BrandMark";

type Props = {
  documentsCount?: number;
  sessionsCount?: number;
  onCreateSession?: () => void;
  onNavigateToArchitecture?: () => void;
};

export function WelcomeScreen({
  documentsCount = 0,
  sessionsCount = 0,
  onCreateSession,
  onNavigateToArchitecture,
}: Readonly<Props>) {
  const { t } = useTranslation();

  const stats = [
    { icon: FileText, value: documentsCount, label: t("components.chat.knowledgeDocs") },
    { icon: Layers, value: sessionsCount, label: t("components.chat.historySessions") },
    { icon: Boxes, value: 4, label: t("components.chat.agentModes") },
  ];

  const features = [
    { icon: Zap, title: t("components.chat.smartRetrieval"), desc: t("components.chat.smartRetrievalDesc") },
    { icon: Globe, title: t("components.chat.webResearch"), desc: t("components.chat.webResearchDesc") },
    { icon: Images, title: t("components.chat.multimodal"), desc: t("components.chat.multimodalDesc") },
    { icon: Route, title: t("components.chat.evidenceTrace"), desc: t("components.chat.evidenceTraceDesc") },
  ];

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 py-10 text-center">
      <BrandMark size="lg" className="mx-auto ring-brand-surface-hover" />

      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{t("components.chat.welcomeTitle")}</h2>
        <p className="mx-auto max-w-lg text-sm sm:text-base text-ink/80 leading-relaxed">{t("components.chat.welcomeSubtitle")}</p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2.5">
        {stats.map(({ icon: Icon, value, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-2 rounded-pill border border-brand-border bg-brand-surface px-3.5 py-1.5 shadow-xs"
          >
            <Icon className="size-4 text-brand-accent" aria-hidden="true" />
            <span className="font-mono text-sm font-bold text-brand-text">{value}</span>
            <span className="text-xs sm:text-sm font-medium text-ink/80">{label}</span>
          </span>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2.5">
        <Button size="lg" className="text-sm sm:text-base font-semibold" onClick={onCreateSession}>
          <Plus className="size-4" strokeWidth={2.5} aria-hidden="true" />
          {t("components.chat.startConversation")}
        </Button>
        <Button size="lg" variant="secondary" className="text-sm sm:text-base font-semibold" onClick={onNavigateToArchitecture}>
          <Boxes className="size-4" aria-hidden="true" />
          {t("components.chat.viewArchitecture")}
        </Button>
      </div>

      {/* The starter grid from the design: two columns of tappable cards that
          each name a capability and say what it does. */}
      <div className="grid grid-cols-1 gap-3.5 pt-2 text-left sm:grid-cols-2">
        {features.map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="group rounded-card border border-line bg-surface p-4 shadow-elev-1 transition-all hover:border-brand-border-strong hover:bg-brand-surface/70"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2 text-sm font-bold text-ink group-hover:text-brand-text">
                <Icon className="size-4 text-brand-accent" aria-hidden="true" />
                {title}
              </span>
              <ArrowUpRight
                className="size-4 shrink-0 text-ink-faint group-hover:text-brand-accent"
                aria-hidden="true"
              />
            </div>
            <p className="mt-1.5 text-xs sm:text-sm leading-relaxed text-ink/80">{desc}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 pt-2 text-xs text-ink/75 font-medium">
        <span>{t("components.chat.tipSend")}</span>
        <span>{t("components.chat.tipUpload")}</span>
        <span>{t("components.chat.tipAgent")}</span>
      </div>
    </div>
  );
}
