import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/BrandMark";

export function NotFoundPage({ pathname }: Readonly<{ pathname: string }>) {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <BrandMark size="lg" className="ring-brand-surface-hover" />
      <h1 className="font-mono text-5xl font-bold tracking-tight text-brand-text-strong">404</h1>
      <p className="max-w-md text-sm sm:text-base text-ink/80 leading-relaxed">{t("pages.notFound.message", { pathname })}</p>
      <div className="flex items-center gap-2.5">
        <Button asChild className="text-xs sm:text-sm font-semibold">
          <Link to="/app">{t("pages.notFound.backToApp")}</Link>
        </Button>
        <Button asChild variant="secondary" className="text-xs sm:text-sm font-semibold">
          <Link to="/app/login">{t("pages.notFound.login")}</Link>
        </Button>
      </div>
    </div>
  );
}
