import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Check, Brain, FileText, Network, Search, Shield, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LanguageToggle } from "@/components/LanguageToggle";
import { BrandMark } from "@/components/layout/BrandMark";
import { DataFlowVisualization } from "@/components/DataFlowVisualization";

interface LandingPageProps {
  isLoggedIn: boolean;
}

/**
 * The public showcase page -- the design prototype's `#view-landing`.
 *
 * Its copy used to be 46 `i18n.language === "zh" ? ... : ...` ternaries inline
 * in the JSX. They are locale keys now, under `pages.landing.*`, and the data
 * tables below hold structure rather than translations -- so the markup reads
 * as markup and a translator has one place to look.
 */
export function LandingPage({ isLoggedIn }: Readonly<LandingPageProps>) {
  const { t, i18n } = useTranslation();

  useEffect(() => {
    document.title = `${t("app.title")} - ${t("app.subtitle")}`;
  }, [i18n.language, t]);

  const navLinks = [
    { href: "#features", label: t("pages.landing.navFeatures") },
    { href: "#workflow", label: t("pages.landing.navWorkflow") },
    { href: "#tiers", label: t("pages.landing.navTiers") },
    { href: "#architecture", label: t("pages.landing.navArchitecture") },
  ];

  const features = [
    { icon: Brain, title: t("pages.landing.feature1Title"), desc: t("pages.landing.feature1Desc") },
    { icon: Search, title: t("pages.landing.feature2Title"), desc: t("pages.landing.feature2Desc") },
    { icon: Network, title: t("pages.landing.feature3Title"), desc: t("pages.landing.feature3Desc") },
    { icon: FileText, title: t("pages.landing.feature4Title"), desc: t("pages.landing.feature4Desc") },
    { icon: Wrench, title: t("pages.landing.feature5Title"), desc: t("pages.landing.feature5Desc") },
    { icon: Shield, title: t("pages.landing.feature6Title"), desc: t("pages.landing.feature6Desc") },
  ];

  const metricLabels = {
    time: t("pages.landing.metricResponseTime"),
    depth: t("pages.landing.metricRetrievalDepth"),
    tokens: t("pages.landing.metricMaxTokens"),
  };

  const tiers = [
    {
      name: `${t("query.mode.fast")} (Fast)`,
      desc: t("pages.landing.tierFastDesc"),
      featured: false,
      metrics: [
        [metricLabels.time, "< 800ms"],
        [metricLabels.depth, "top_k=5 / rr=3"],
        [metricLabels.tokens, "300"],
      ],
      capabilities: [
        [true, t("pages.landing.capVectorDb")],
        [true, t("pages.landing.capBm25")],
        [false, t("pages.landing.capWebFallback")],
        [false, t("pages.landing.capMultiHopGraph")],
      ] as Array<[boolean, string]>,
    },
    {
      name: `${t("query.mode.balanced")} (Balanced)`,
      desc: t("pages.landing.tierBalancedDesc"),
      featured: true,
      metrics: [
        [metricLabels.time, "< 2000ms"],
        [metricLabels.depth, "top_k=10 / rr=5"],
        [metricLabels.tokens, "800"],
      ],
      capabilities: [
        [true, t("pages.landing.capHybrid")],
        [true, t("pages.landing.capRrf")],
        [true, t("pages.landing.capConditionalWeb")],
        [false, t("pages.landing.capDeepGraph")],
      ] as Array<[boolean, string]>,
    },
    {
      name: `${t("query.mode.deep")} (Deep)`,
      desc: t("pages.landing.tierDeepDesc"),
      featured: false,
      metrics: [
        [metricLabels.time, "< 5000ms"],
        [metricLabels.depth, "top_k=20 / rr=10"],
        [metricLabels.tokens, "1500"],
      ],
      capabilities: [
        [true, t("pages.landing.capMaxDepth")],
        [true, t("pages.landing.capReranker")],
        [true, t("pages.landing.capActiveWeb")],
        [true, t("pages.landing.capNeo4jPaths")],
      ] as Array<[boolean, string]>,
    },
  ];

  const workflow = [
    {
      title: t("pages.landing.step1Title"),
      body: t("pages.landing.step1Body"),
    },
    {
      title: t("pages.landing.step2Title"),
      body: t("pages.landing.step2Body"),
    },
    {
      title: t("pages.landing.step3Title"),
      body: t("pages.landing.step3Body"),
    },
    {
      title: t("pages.landing.step4Title"),
      body: t("pages.landing.step4Body"),
    },
  ];

  const SectionHeading = ({ lead, accent, sub }: { lead: string; accent: string; sub: string }) => (
    <div className="mx-auto max-w-2xl space-y-2 text-center">
      <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
        {lead} <span className="text-brand-text">{accent}</span>
      </h2>
      <p className="text-xs leading-relaxed text-ink-muted sm:text-sm">{sub}</p>
    </div>
  );

  return (
    <div className="landing-root aurora-bg min-h-screen">
      <header className="glass-panel sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-x-0 border-t-0 px-4">
        <Link to="/" className="flex items-center gap-2">
          <BrandMark />
          <span className="text-sm font-bold tracking-tight text-ink">{t("app.title")}</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Main Navigation">
          {navLinks.map(({ href, label }) => (
            <a
              key={href}
              href={href}
              className="rounded-control px-2.5 py-1 text-[11px] font-medium text-ink-muted transition-colors hover:bg-brand-surface hover:text-brand-text"
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-1.5">
          <LanguageToggle />
          {isLoggedIn ? (
            <Button asChild size="sm">
              <Link to="/app">{t("pages.landing.enterApp")}</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="secondary" size="sm">
                <Link to="/app/login?mode=login">{t("auth.login")}</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
              </Button>
            </>
          )}
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-4 py-16 text-center sm:py-24">
        <BrandMark size="lg" className="mx-auto mb-6 ring-brand-surface-hover" />
        <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl lg:text-6xl">
          {t("pages.landing.heroName")}
          <br />
          <span className="bg-[image:var(--brand-gradient)] bg-clip-text text-transparent">
            {t("pages.landing.heroTagline")}
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
          {t("pages.landing.heroSubtitle")}
        </p>
        <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
          {isLoggedIn ? (
            <Button asChild size="lg">
              <Link to="/app">
                {t("pages.landing.enterApp")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
          ) : (
            <>
              <Button asChild size="lg">
                <Link to="/app/login?mode=login">
                  {t("auth.login")}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary">
                <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
              </Button>
            </>
          )}
          <Button asChild size="lg" variant="ghost">
            <a href="#features">{t("pages.landing.learnMore")}</a>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
        <SectionHeading
          lead={t("pages.landing.featuresHeadingLead")}
          accent={t("pages.landing.featuresHeadingAccent")}
          sub={t("pages.landing.featuresSubtitle")}
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="p-5 transition-all hover:border-brand-border-strong hover:shadow-elev-2">
              <span className="mb-3 flex size-9 items-center justify-center rounded-card bg-brand-surface text-brand-text">
                <Icon className="size-4.5" aria-hidden="true" />
              </span>
              <h3 className="text-sm font-bold text-ink">{title}</h3>
              <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">{desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Retrieval tiers */}
      <section id="tiers" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
        <SectionHeading
          lead={t("pages.landing.tiersHeadingLead")}
          accent={t("pages.landing.tiersHeadingAccent")}
          sub={t("pages.landing.tiersSubtitle")}
        />
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {tiers.map((tier) => (
            <Card
              key={tier.name}
              className={cn(
                "space-y-3 p-5",
                tier.featured && "border-2 border-brand-border-strong bg-brand-surface/70 shadow-elev-2"
              )}
            >
              <div>
                <h3 className="text-sm font-bold text-ink">{tier.name}</h3>
                <p className="mt-0.5 text-[11px] text-ink-muted">{tier.desc}</p>
              </div>

              <dl className="space-y-1 border-y border-line-subtle py-2.5">
                {tier.metrics.map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between gap-2 text-[11px]">
                    <dt className="text-ink-muted">{label}</dt>
                    <dd className="font-mono font-semibold text-brand-text">{value}</dd>
                  </div>
                ))}
              </dl>

              <ul className="space-y-1.5">
                {tier.capabilities.map(([enabled, label]) => (
                  <li
                    key={label}
                    /* An unavailable capability still has to be readable: `--text-faint`
                       is placeholder-only. The check icon carries the state. */
                    className={cn("flex items-start gap-1.5 text-[11px]", enabled ? "text-ink" : "text-ink-muted")}
                  >
                    <Check
                      className={cn("mt-0.5 size-3 shrink-0", enabled ? "text-success" : "text-line-strong")}
                      strokeWidth={3}
                      aria-hidden="true"
                    />
                    {label}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="mx-auto max-w-4xl space-y-8 px-4 py-14">
        <SectionHeading lead={t("pages.landing.workflowTitle")} accent="" sub={t("pages.landing.workflowSubtitle")} />
        <ol className="space-y-3">
          {workflow.map(({ title, body }, index) => (
            <li key={title}>
              <Card className="flex gap-4 p-4">
                <span className="font-mono text-xl font-bold text-brand-accent" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0">
                  <h4 className="text-xs font-bold text-ink">{title}</h4>
                  <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">{body}</p>
                </div>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      {/* Architecture */}
      <section id="architecture" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
        <SectionHeading
          lead={t("pages.landing.archHeadingLead")}
          accent={t("pages.landing.archHeadingAccent")}
          sub={t("pages.landing.archSubtitle")}
        />
        <Card className="relative overflow-hidden">
          <Badge variant="brand" size="pill" className="absolute left-3 top-3 z-10">
            {t("pages.landing.archPreviewHint")}
          </Badge>
          <DataFlowVisualization />
        </Card>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-5xl px-4 py-14">
        <div className="rounded-panel bg-[image:var(--brand-gradient)] p-8 text-center text-white shadow-elev-3 sm:p-12">
          <h2 className="text-2xl font-bold tracking-tight">{t("pages.landing.ctaTitle")}</h2>
          <p className="mx-auto mt-2 max-w-xl text-xs leading-relaxed text-white/80">
            {t("pages.landing.ctaSubtitle")}
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            {isLoggedIn ? (
              <Button asChild size="lg" variant="secondary">
                <Link to="/app">
                  {t("pages.landing.enterApp")}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" variant="secondary">
                  <Link to="/app/login?mode=login">
                    {t("auth.loginButton")}
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="ghost"
                  className="border border-white/40 text-white hover:bg-white/15 hover:text-white"
                >
                  <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      <footer className="border-t border-line-subtle px-4 py-6">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-2">
          <nav className="flex flex-wrap items-center justify-center gap-4">
            <a href="#features" className="text-[11px] text-ink-muted hover:text-brand-text">
              {t("pages.landing.navFeatures")}
            </a>
            <a href="#workflow" className="text-[11px] text-ink-muted hover:text-brand-text">
              {t("pages.landing.footerFlow")}
            </a>
            <a href="#tiers" className="text-[11px] text-ink-muted hover:text-brand-text">
              {t("pages.landing.footerTiers")}
            </a>
            <Link to="/app/architecture" className="text-[11px] text-ink-muted hover:text-brand-text">
              {t("dataFlow.title")}
            </Link>
          </nav>
          <p className="text-[10px] text-ink-muted">
            &copy; {new Date().getFullYear()} {t("app.title")}. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
