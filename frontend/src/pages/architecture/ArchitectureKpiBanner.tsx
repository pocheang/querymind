import { useTranslation } from "react-i18next";
import { KPI_ITEMS } from "./types";

export function ArchitectureKpiBanner() {
  const { t } = useTranslation();

  return (
    <section aria-label="System Performance KPIs" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {KPI_ITEMS.map((kpi) => (
        <div
          key={kpi.valueKey}
          className="rounded-card border border-line bg-surface p-4 shadow-elev-1 transition-all hover:border-brand-border hover:shadow-elev-2"
        >
          <div className="font-mono text-2xl font-extrabold tracking-tight text-brand-text sm:text-3xl">
            {t(kpi.valueKey)}
          </div>
          <div className="mt-1.5 text-sm font-semibold text-ink">{t(kpi.labelKey)}</div>
          <div className="mt-1 text-xs text-ink-muted leading-relaxed">{t(kpi.descKey)}</div>
        </div>
      ))}
    </section>
  );
}
