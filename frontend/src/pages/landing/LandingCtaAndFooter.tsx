import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/BrandMark";

interface LandingCtaAndFooterProps {
  isLoggedIn: boolean;
}

export function LandingCtaAndFooter({ isLoggedIn }: Readonly<LandingCtaAndFooterProps>) {
  const { t } = useTranslation();

  return (
    <>
      {/* Call to Action Banner */}
      <section className="mx-auto max-w-5xl px-4 py-14">
        <div className="rounded-panel bg-[image:var(--brand-gradient)] p-8 text-center text-white shadow-elev-3 sm:p-12">
          <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-pill bg-white/15 backdrop-blur-sm">
            <Zap className="size-6 text-white" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl lg:text-4xl">{t("pages.landing.ctaTitle")}</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/90 sm:text-base">
            {t("pages.landing.ctaSubtitle")}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {isLoggedIn ? (
              <Button asChild size="lg" variant="secondary" className="shadow-elev-2 text-sm sm:text-base">
                <Link to="/app" className="gap-1.5">
                  <span>{t("pages.landing.enterApp")}</span>
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" variant="secondary" className="shadow-elev-2 text-sm sm:text-base">
                  <Link to="/app/login?mode=login" className="gap-1.5">
                    <span>{t("auth.loginButton")}</span>
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="ghost"
                  className="border border-white/40 text-white hover:bg-white/15 hover:text-white text-sm sm:text-base"
                >
                  <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line-subtle px-4 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2">
            <BrandMark size="sm" />
            <span className="text-sm font-bold text-ink">{t("app.title")}</span>
            <span className="text-xs font-medium text-ink-muted">· Enterprise Agentic RAG</span>
          </div>

          <nav className="flex flex-wrap items-center justify-center gap-5 text-xs font-medium text-ink/80 sm:text-sm">
            <a href="#features" className="hover:text-brand-text transition-colors">
              {t("pages.landing.navFeatures")}
            </a>
            <a href="#workflow" className="hover:text-brand-text transition-colors">
              {t("pages.landing.footerFlow")}
            </a>
            <a href="#agents" className="hover:text-brand-text transition-colors">
              {t("pages.landing.footerAgents")}
            </a>
            <Link to="/app/architecture" className="hover:text-brand-text transition-colors">
              {t("dataFlow.title")}
            </Link>
          </nav>

          <p className="text-xs text-ink/75">
            &copy; {new Date().getFullYear()} {t("app.title")}. All rights reserved.
          </p>
        </div>
      </footer>
    </>
  );
}
