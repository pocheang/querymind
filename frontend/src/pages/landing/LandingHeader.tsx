import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/BrandMark";
import { LanguageToggle } from "@/components/LanguageToggle";

interface LandingHeaderProps {
  isLoggedIn: boolean;
}

export function LandingHeader({ isLoggedIn }: Readonly<LandingHeaderProps>) {
  const { t } = useTranslation();

  const navLinks = [
    { href: "#features", label: t("pages.landing.navFeatures") },
    { href: "#workflow", label: t("pages.landing.navWorkflow") },
    { href: "#agents", label: t("pages.landing.navAgents") },
    { href: "#architecture", label: t("pages.landing.navArchitecture") },
  ];

  return (
    <header className="glass-panel sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-x-0 border-t-0 px-4 shadow-elev-1 sm:px-6">
      <Link to="/" className="flex items-center gap-2">
        <BrandMark />
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-bold tracking-tight text-ink sm:text-base">{t("app.title")}</span>
          <Badge variant="brand" size="xs" mono className="text-xs uppercase font-medium px-1.5 py-0.5">
            v0.7
          </Badge>
        </div>
      </Link>

      <nav className="hidden items-center gap-1 md:flex" aria-label="Main Navigation">
        {navLinks.map(({ href, label }) => (
          <a
            key={href}
            href={href}
            className="rounded-control px-3 py-1.5 text-xs font-medium text-ink/80 transition-colors hover:bg-brand-surface hover:text-brand-text sm:text-sm"
          >
            {label}
          </a>
        ))}
        <Link
          to="/app/architecture"
          className="flex items-center gap-1.5 rounded-control px-3 py-1.5 text-xs font-medium text-ink/80 transition-colors hover:bg-brand-surface hover:text-brand-text sm:text-sm"
        >
          <span>{t("dataFlow.title", "架构流转")}</span>
          <ExternalLink className="size-3.5 opacity-70" aria-hidden="true" />
        </Link>
      </nav>

      <div className="flex items-center gap-1.5">
        <LanguageToggle />
        {isLoggedIn ? (
          <Button asChild size="sm">
            <Link to="/app" className="gap-1.5 text-xs sm:text-sm font-semibold">
              <span>{t("pages.landing.enterApp")}</span>
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </Button>
        ) : (
          <>
            <Button asChild variant="secondary" size="sm">
              <Link to="/app/login?mode=login" className="text-xs sm:text-sm font-semibold">{t("auth.login")}</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/app/login?mode=register" className="text-xs sm:text-sm font-semibold">{t("pages.landing.register")}</Link>
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
