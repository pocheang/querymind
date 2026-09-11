import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  CheckCircle2,
  Database,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface LandingHeroSectionProps {
  isLoggedIn: boolean;
}

export function LandingHeroSection({ isLoggedIn }: Readonly<LandingHeroSectionProps>) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"chat" | "graph" | "metrics">("chat");

  const trustMetrics = [
    { value: "100%", label: t("pages.landing.trustPrivate"), desc: t("pages.landing.trustPrivateDesc") },
    { value: "< 800ms", label: t("pages.landing.trustLatency"), desc: t("pages.landing.trustLatencyDesc") },
    { value: "99.8%", label: t("pages.landing.trustGrounding"), desc: t("pages.landing.trustGroundingDesc") },
    { value: t("pages.landing.trustZeroDepsVal"), label: t("pages.landing.trustZeroDeps"), desc: t("pages.landing.trustZeroDepsDesc") },
  ];

  return (
    <section className="relative mx-auto max-w-5xl px-4 pt-12 pb-16 text-center sm:pt-20 sm:pb-24">
      {/* Floating Top Pill */}
      <div className="mb-6 flex justify-center">
        <div className="inline-flex items-center gap-2 rounded-pill border border-brand-border bg-brand-surface/80 px-3.5 py-1.5 text-xs font-medium text-brand-text shadow-xs backdrop-blur-sm sm:text-sm">
          <Sparkles className="size-3.5 text-brand" aria-hidden="true" />
          <span>{t("pages.landing.heroPill")}</span>
          <span className="hidden rounded bg-brand/10 px-2 py-0.5 text-xs font-semibold uppercase sm:inline">
            Production Ready
          </span>
        </div>
      </div>

      <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl lg:text-6xl">
        {t("pages.landing.heroName")}
        <br />
        <span className="bg-[image:var(--brand-gradient)] bg-clip-text text-transparent">
          {t("pages.landing.heroTagline")}
        </span>
      </h1>

      <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-ink/80 sm:text-base">
        {t("pages.landing.heroSubtitle")}
      </p>

      {/* Action Buttons */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-2.5">
        {isLoggedIn ? (
          <Button asChild size="lg" className="gap-1.5 shadow-elev-2 text-sm sm:text-base">
            <Link to="/app">
              {t("pages.landing.enterApp")}
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </Button>
        ) : (
          <>
            <Button asChild size="lg" className="gap-1.5 shadow-elev-2 text-sm sm:text-base">
              <Link to="/app/login?mode=login">
                {t("auth.login")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary" className="text-sm sm:text-base">
              <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
            </Button>
          </>
        )}
        <Button asChild size="lg" variant="ghost" className="text-sm sm:text-base">
          <a href="#features" className="gap-1">
            <span>{t("pages.landing.learnMore")}</span>
          </a>
        </Button>
      </div>

      {/* Live Interactive Product Preview Card */}
      <div className="mt-12 overflow-hidden rounded-panel border border-line-subtle bg-surface/80 shadow-elev-3 backdrop-blur-md transition-all sm:mt-16">
        {/* Mock Window Top Bar */}
        <div className="flex items-center justify-between border-b border-line-subtle bg-surface-muted/60 px-4 py-3 text-xs text-ink-muted sm:text-sm">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="size-2.5 rounded-pill bg-danger/80" />
              <span className="size-2.5 rounded-pill bg-warning/80" />
              <span className="size-2.5 rounded-pill bg-success/80" />
            </div>
            <span className="ml-2 font-mono text-xs text-ink/70">
              querymind-deck://session/enterprise-kb-v4
            </span>
          </div>

          {/* Interactive Preview Switch Tabs */}
          <div className="flex items-center rounded-control border border-line-subtle bg-surface p-1 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab("chat")}
              className={cn(
                "rounded px-3 py-1 font-medium transition-colors text-xs",
                activeTab === "chat" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
              )}
            >
              {t("pages.landing.demoTabChat")}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("graph")}
              className={cn(
                "rounded px-3 py-1 font-medium transition-colors text-xs",
                activeTab === "graph" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
              )}
            >
              {t("pages.landing.demoTabGraph")}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("metrics")}
              className={cn(
                "rounded px-3 py-1 font-medium transition-colors text-xs",
                activeTab === "metrics" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
              )}
            >
              {t("pages.landing.demoTabMetrics")}
            </button>
          </div>
        </div>

        {/* Mock Console Content Body */}
        <div className="p-4 text-left sm:p-6">
          {activeTab === "chat" && (
            <div className="space-y-4">
              {/* User Query Bubble */}
              <div className="flex items-start gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-brand-surface font-bold text-brand-text text-xs sm:text-sm">
                  U
                </div>
                <div className="rounded-panel rounded-tl-sm bg-surface-muted p-3.5 text-sm font-medium leading-relaxed text-ink">
                  {t("pages.landing.heroDemoQuery")}
                </div>
              </div>

              {/* Execution Trace Live Stepper */}
              <div className="ml-11 rounded-card border border-line-subtle bg-surface-inset/60 p-3">
                <div className="flex flex-wrap items-center gap-2.5 text-xs font-medium text-ink/80">
                  <span className="flex items-center gap-1.5 font-semibold text-success">
                    <CheckCircle2 className="size-3.5" />
                    {t("pages.landing.heroRouteDecision")}
                  </span>
                  <span className="text-line-strong">&bull;</span>
                  <span className="flex items-center gap-1.5">
                    <Database className="size-3.5 text-brand" />
                    {t("pages.landing.heroVectorStep")}
                  </span>
                  <span className="text-line-strong">&bull;</span>
                  <span className="flex items-center gap-1.5">
                    <Network className="size-3.5 text-blue-500" />
                    {t("pages.landing.heroGraphStep")}
                  </span>
                  <span className="text-line-strong">&bull;</span>
                  <span className="font-mono text-ink/70">{t("pages.landing.heroElapsed")}</span>
                </div>
              </div>

              {/* Assistant Answer Bubble with Grounding */}
              <div className="flex items-start gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-[image:var(--brand-gradient)] text-white text-xs sm:text-sm font-bold shadow-xs">
                  AI
                </div>
                <div className="space-y-2.5 rounded-panel rounded-tl-sm border border-line-subtle bg-surface p-4 text-sm leading-relaxed text-ink shadow-xs">
                  <p className="leading-relaxed text-ink font-normal">
                    {t("pages.landing.heroAnswerIntro")}
                  </p>
                  <ol className="list-decimal space-y-1.5 pl-4 text-xs leading-relaxed text-ink/85 sm:text-sm">
                    <li>
                      {t("pages.landing.heroAnswerPoint1")}<span className="ml-1 cursor-pointer font-mono font-bold text-brand-text hover:underline">[1]</span>。
                    </li>
                    <li>
                      {t("pages.landing.heroAnswerPoint2")}<span className="ml-1 cursor-pointer font-mono font-bold text-brand-text hover:underline">[2]</span>。
                    </li>
                    <li>
                      {t("pages.landing.heroAnswerPoint3")}
                    </li>
                  </ol>

                  <div className="flex flex-wrap items-center gap-2.5 pt-2.5 border-t border-line-subtle text-xs">
                    <Badge variant="success" size="xs" mono className="text-xs font-semibold px-2 py-0.5">
                      Grounding: 99.8%
                    </Badge>
                    <Badge variant="brand" size="xs" mono className="text-xs font-semibold px-2 py-0.5">
                      BGE-Reranker Score: 0.94
                    </Badge>
                    <span className="text-xs font-medium text-ink/75">{t("pages.landing.heroDataSource")}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "graph" && (
            <div className="space-y-3 py-4 text-center">
              <div className="mx-auto flex max-w-md items-center justify-center gap-3 py-6">
                <div className="rounded-card border border-blue-500/30 bg-blue-500/10 p-3.5 text-center">
                  <Network className="mx-auto size-6 text-blue-500" />
                  <span className="mt-1.5 block text-sm font-bold text-ink">{t("pages.landing.heroEntityRegulation")}</span>
                  <span className="text-xs font-medium text-ink/70">Node: Regulation</span>
                </div>
                <div className="h-0.5 w-12 bg-blue-500/40 relative">
                  <span className="absolute -top-3 left-1 text-xs font-mono font-semibold text-ink/70">APPLIES_TO</span>
                </div>
                <div className="rounded-card border border-amber-500/30 bg-amber-500/10 p-3.5 text-center">
                  <Database className="mx-auto size-6 text-amber-500" />
                  <span className="mt-1.5 block text-sm font-bold text-ink">{t("pages.landing.heroEntityProduct")}</span>
                  <span className="text-xs font-medium text-ink/70">Node: Product</span>
                </div>
                <div className="h-0.5 w-12 bg-amber-500/40 relative">
                  <span className="absolute -top-3 left-1 text-xs font-mono font-semibold text-ink/70">GOVERNED_BY</span>
                </div>
                <div className="rounded-card border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-center">
                  <ShieldCheck className="mx-auto size-6 text-emerald-500" />
                  <span className="mt-1.5 block text-sm font-bold text-ink">{t("pages.landing.heroEntityAudit")}</span>
                  <span className="text-xs font-medium text-ink/70">Node: AuditEvent</span>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-ink/80 sm:text-sm">
                {t("pages.landing.heroGraphDesc")}
              </p>
            </div>
          )}

          {activeTab === "metrics" && (
            <div className="grid grid-cols-2 gap-3 py-3 sm:grid-cols-4">
              <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                <span className="text-xs font-medium text-ink/80 sm:text-sm">{t("pages.landing.heroTtftLabel")}</span>
                <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">420ms</p>
                <span className="text-xs font-semibold text-success">{t("pages.landing.heroTtftSub")}</span>
              </div>
              <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                <span className="text-xs font-medium text-ink/80 sm:text-sm">{t("pages.landing.heroRecallLabel")}</span>
                <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">98.4%</p>
                <span className="text-xs font-semibold text-success">{t("pages.landing.heroRecallSub")}</span>
              </div>
              <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                <span className="text-xs font-medium text-ink/80 sm:text-sm">{t("pages.landing.heroTpsLabel")}</span>
                <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">48 tok/s</p>
                <span className="text-xs font-medium text-ink/70">{t("pages.landing.heroTpsSub")}</span>
              </div>
              <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                <span className="text-xs font-medium text-ink/80 sm:text-sm">{t("pages.landing.heroLeakageLabel")}</span>
                <p className="mt-1 font-mono text-xl font-bold text-success sm:text-2xl">{t("pages.landing.heroZeroExfil")}</p>
                <span className="text-xs font-medium text-ink/70">{t("pages.landing.heroAirGapped")}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Trust Metrics Bar */}
      <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {trustMetrics.map((item) => (
          <div
            key={item.label}
            className="rounded-card border border-line-subtle bg-surface/60 p-4 text-center shadow-xs backdrop-blur-sm transition-all hover:bg-surface"
          >
            <div className="font-mono text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
              <span className="bg-[image:var(--brand-gradient)] bg-clip-text text-transparent">{item.value}</span>
            </div>
            <div className="mt-1.5 text-sm font-bold text-ink sm:text-base">{item.label}</div>
            <div className="mt-1 text-xs leading-relaxed text-ink/75 sm:text-sm">{item.desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
