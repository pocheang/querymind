import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LanguageToggle } from "@/components/LanguageToggle";

interface ArchitectureHeaderProps {
  isLoggedIn: boolean;
}

export function ArchitectureHeader({ isLoggedIn }: Readonly<ArchitectureHeaderProps>) {
  const { t } = useTranslation();

  return (
    <header className="glass-panel border-x-0 border-t-0 p-4 sm:p-6">
      <div className="mx-auto flex max-w-[1720px] w-full flex-wrap items-start justify-between gap-4 px-2 sm:px-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="brand" size="pill" className="uppercase tracking-wider">
              {t("architecture.badges.enterprise")}
            </Badge>
            <Badge variant="neutral" size="pill" mono>
              {t("architecture.badges.version")}
            </Badge>
            <Badge variant="success" size="pill" className="gap-1.5">
              <span className="size-1.5 rounded-pill bg-success animate-pulse" aria-hidden="true" />
              {t("architecture.badges.status")}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-4xl">QueryMind Architecture & Systems</h1>
          <p className="max-w-4xl text-sm sm:text-base text-ink-muted leading-relaxed">
            {t("dataFlow.description")}
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-ink-muted">
            <Badge variant="outline" size="sm" mono>
              {t("architecture.badges.stack")}
            </Badge>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <LanguageToggle />
          <Button asChild variant="secondary" size="sm">
            <Link to={isLoggedIn ? "/app" : "/app/login"}>{isLoggedIn ? t("nav.home") : t("auth.login")}</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
