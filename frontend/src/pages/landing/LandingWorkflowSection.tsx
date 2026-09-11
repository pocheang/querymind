import { useTranslation } from "react-i18next";
import { Compass, Search, Shield, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { SectionHeading } from "./SectionHeading";
import type { WorkflowStep } from "./types";

export function LandingWorkflowSection() {
  const { t } = useTranslation();

  const workflow: WorkflowStep[] = [
    {
      icon: Shield,
      title: t("pages.landing.step1Title"),
      body: t("pages.landing.step1Body"),
      tag: t("pages.landing.step1Tag"),
    },
    {
      icon: Compass,
      title: t("pages.landing.step2Title"),
      body: t("pages.landing.step2Body"),
      tag: t("pages.landing.step2Tag"),
    },
    {
      icon: Search,
      title: t("pages.landing.step3Title"),
      body: t("pages.landing.step3Body"),
      tag: t("pages.landing.step3Tag"),
    },
    {
      icon: Sparkles,
      title: t("pages.landing.step4Title"),
      body: t("pages.landing.step4Body"),
      tag: t("pages.landing.step4Tag"),
    },
  ];

  return (
    <section id="workflow" className="mx-auto max-w-4xl space-y-8 px-4 py-14">
      <SectionHeading lead={t("pages.landing.workflowTitle")} accent="" sub={t("pages.landing.workflowSubtitle")} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {workflow.map(({ icon: Icon, title, body, tag }, index) => (
          <Card key={title} className="p-5 sm:p-6 transition-all hover:border-brand-border-strong hover:shadow-elev-1">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <span className="flex size-8 items-center justify-center rounded-control bg-brand-surface text-brand-text">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <span className="font-mono text-sm font-bold text-brand-accent sm:text-base">
                  STEP {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <Badge variant="neutral" size="xs" className="text-xs font-semibold px-2 py-0.5">
                {tag}
              </Badge>
            </div>
            <h4 className="mt-3 text-sm font-bold text-ink sm:text-base">{title}</h4>
            <p className="mt-1.5 text-xs leading-relaxed text-ink/80 sm:text-sm">{body}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}
