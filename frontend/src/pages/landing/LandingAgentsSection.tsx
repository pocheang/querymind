import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  Brain,
  Check,
  Compass,
  Cpu,
  FileText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SectionHeading } from "./SectionHeading";
import type { AgentCard } from "./types";

export function LandingAgentsSection() {
  const { t } = useTranslation();

  const agentCards: AgentCard[] = [
    {
      key: "",
      icon: Compass,
      title: t("pages.landing.agentAutoTitle"),
      desc: t("pages.landing.agentAutoDesc"),
      badge: t("pages.landing.agentAutoBadge"),
      featured: true,
      accent: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      capabilities: [
        t("pages.landing.agentAutoCap1"),
        t("pages.landing.agentAutoCap2"),
        t("pages.landing.agentAutoCap3"),
        t("pages.landing.agentAutoCap4"),
      ],
      link: "/app",
      actionText: t("pages.landing.agentAutoAction"),
    },
    {
      key: "cybersecurity",
      icon: ShieldCheck,
      title: t("pages.landing.agentCyberTitle"),
      desc: t("pages.landing.agentCyberDesc"),
      badge: t("pages.landing.agentCyberBadge"),
      featured: false,
      accent: "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      capabilities: [
        t("pages.landing.agentCyberCap1"),
        t("pages.landing.agentCyberCap2"),
        t("pages.landing.agentCyberCap3"),
        t("pages.landing.agentCyberCap4"),
      ],
      link: "/app?mode=cybersecurity",
      actionText: t("pages.landing.agentCyberAction"),
    },
    {
      key: "artificial_intelligence",
      icon: Brain,
      title: t("pages.landing.agentAiTitle"),
      desc: t("pages.landing.agentAiDesc"),
      badge: t("pages.landing.agentAiBadge"),
      featured: false,
      accent: "text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20",
      capabilities: [
        t("pages.landing.agentAiCap1"),
        t("pages.landing.agentAiCap2"),
        t("pages.landing.agentAiCap3"),
        t("pages.landing.agentAiCap4"),
      ],
      link: "/app?mode=artificial_intelligence",
      actionText: t("pages.landing.agentAiAction"),
    },
    {
      key: "pdf_text",
      icon: FileText,
      title: t("pages.landing.agentPdfTitle"),
      desc: t("pages.landing.agentPdfDesc"),
      badge: t("pages.landing.agentPdfBadge"),
      featured: false,
      accent: "text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
      capabilities: [
        t("pages.landing.agentPdfCap1"),
        t("pages.landing.agentPdfCap2"),
        t("pages.landing.agentPdfCap3"),
        t("pages.landing.agentPdfCap4"),
      ],
      link: "/app?mode=pdf_text",
      actionText: t("pages.landing.agentPdfAction"),
    },
    {
      key: "general",
      icon: Sparkles,
      title: t("pages.landing.agentGeneralTitle"),
      desc: t("pages.landing.agentGeneralDesc"),
      badge: t("pages.landing.agentGeneralBadge"),
      featured: false,
      accent: "text-purple-600 dark:text-purple-400 bg-purple-500/10 border-purple-500/20",
      capabilities: [
        t("pages.landing.agentGeneralCap1"),
        t("pages.landing.agentGeneralCap2"),
        t("pages.landing.agentGeneralCap3"),
        t("pages.landing.agentGeneralCap4"),
      ],
      link: "/app?mode=general",
      actionText: t("pages.landing.agentGeneralAction"),
    },
  ];

  return (
    <section id="agents" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
      <SectionHeading
        lead={t("pages.landing.agentsHeadingLead")}
        accent={t("pages.landing.agentsHeadingAccent")}
        sub={t("pages.landing.agentsSubtitle")}
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agentCards.map((agent) => {
          const Icon = agent.icon;
          return (
            <Card
              key={agent.title}
              className={cn(
                "relative flex flex-col justify-between space-y-4 p-5 sm:p-6 transition-all hover:shadow-elev-2",
                agent.featured && "border-2 border-brand-border-strong bg-brand-surface/40 shadow-elev-2"
              )}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-control border shadow-xs", agent.accent)}>
                      <Icon className="size-4.5" aria-hidden="true" />
                    </span>
                    <h3 className="text-base font-bold text-ink">{agent.title}</h3>
                  </div>
                  <Badge variant={agent.featured ? "brand" : "neutral"} size="xs" className="text-xs font-semibold px-2 py-0.5">
                    {agent.badge}
                  </Badge>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-ink/80 sm:text-sm">{agent.desc}</p>

                <ul className="mt-4 space-y-2.5 border-t border-line-subtle pt-3.5">
                  {agent.capabilities.map((label) => (
                    <li
                      key={label}
                      className="flex items-start gap-2.5 text-xs font-medium leading-relaxed text-ink/90 sm:text-sm"
                    >
                      <Check
                        className="mt-0.5 size-4 shrink-0 rounded-pill bg-success p-0.5 text-white"
                        strokeWidth={3}
                        aria-hidden="true"
                      />
                      <span>{label}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-3">
                <Button asChild variant={agent.featured ? "default" : "secondary"} size="sm" className="w-full shadow-xs text-xs sm:text-sm font-semibold">
                  <Link to={agent.link} className="gap-1.5">
                    <span>{agent.actionText}</span>
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                  </Link>
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Dynamic Dispatch Note & Single Console Experience CTA */}
      <div className="flex flex-col items-center justify-between gap-4 rounded-card border border-line-subtle bg-surface/70 p-4 shadow-xs backdrop-blur-sm sm:flex-row sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text">
            <Cpu className="size-5" aria-hidden="true" />
          </div>
          <div className="text-left">
            <h4 className="text-sm font-bold text-ink sm:text-base">{t("pages.landing.agentsBannerTitle")}</h4>
            <p className="mt-1 text-xs leading-relaxed text-ink/80 sm:text-sm">
              {t("pages.landing.agentsBannerDesc")}
            </p>
          </div>
        </div>
        <Button asChild size="sm" className="shrink-0 shadow-xs text-xs sm:text-sm font-semibold">
          <Link to="/app" className="gap-1.5">
            <span>{t("pages.landing.enterApp")}</span>
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
