import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "react-i18next";
import { DataFlowVisualization } from "@/components/DataFlowVisualization";
import { LanguageToggle } from "@/components/LanguageToggle";

type Props = {
  isLoggedIn: boolean;
};

/* The six sections whose content is a flat string list. `keyEndpoints` is
   not among them -- it is one pre-formatted block, rendered separately. */
const LIST_SECTIONS = ["coreMethods", "database", "security", "modelBackends", "operations", "frontend"] as const;

export function ArchitecturePage({ isLoggedIn }: Readonly<Props>) {
  const { t } = useTranslation();
  const heroSectionKeys = [
    "dataFlow",
    "coreMethods",
    "database",
    "security",
    "keyEndpoints",
    "modelBackends",
    "operations",
    "frontend",
  ] as const;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="glass-panel flex flex-wrap items-start justify-between gap-4 border-x-0 border-t-0 p-4 sm:p-6">
        <div className="min-w-0 space-y-2">
          <Badge variant="brand" size="pill" className="uppercase tracking-wider">
            {t("nav.dataFlow")}
          </Badge>
          <h2 className="text-xl font-bold tracking-tight text-ink">{t("dataFlow.title")}</h2>
          <p className="max-w-2xl text-xs text-ink-muted">{t("dataFlow.description")}</p>
          <div className="flex flex-wrap gap-1" aria-label={t("dataFlow.title")}>
            {heroSectionKeys.map((key) => (
              <Badge key={key} variant="neutral" size="pill">
                {t(`architecture.sections.${key}`)}
              </Badge>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <LanguageToggle />
          <Button asChild variant="secondary" size="sm">
            <Link to={isLoggedIn ? "/app" : "/app/login"}>{isLoggedIn ? t("nav.home") : t("auth.login")}</Link>
          </Button>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl space-y-4 p-4 sm:p-6">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{t("architecture.sections.dataFlow")}</CardTitle>
          </CardHeader>
          <DataFlowVisualization />
        </Card>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {LIST_SECTIONS.map((key) => (
            <Card key={key}>
              <CardHeader>
                <CardTitle>{t(`architecture.sections.${key}`)}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {(t(`architecture.content.${key}`, { returnObjects: true }) as string[]).map((item) => (
                    <li key={item} className="flex gap-1.5 text-[11px] leading-relaxed text-ink-muted">
                      <span className="mt-1 size-1 shrink-0 rounded-pill bg-brand-accent" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardHeader>
              <CardTitle>{t("architecture.sections.keyEndpoints")}</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded-control border border-line bg-surface-muted p-2.5 font-mono text-[10px] leading-relaxed text-ink select-text">
                {t("architecture.apiEndpoints", {
                  returnObjects: false,
                  interpolation: { escapeValue: false },
                })}
              </pre>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
