import { useTranslation } from "react-i18next";
import { KpiCard, KpiGrid } from "./AdminPrimitives";

interface Stats {
  total_searches: number;
  success_rate: number;
  unique_users: number;
  unique_websites: number;
  avg_query_length: number;
  avg_search_time: number;
}

interface Props {
  stats: Stats;
}

export function WebActivityKpiCards({ stats }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <KpiGrid cols={6}>
      <KpiCard label={t("admin.webActivity.totalSearches", "Total Searches")} value={stats.total_searches} />
      <KpiCard
        label={t("admin.webActivity.successRate", "Success Rate")}
        value={`${(stats.success_rate * 100).toFixed(1)}%`}
      />
      <KpiCard label={t("admin.webActivity.uniqueUsers", "Unique Users")} value={stats.unique_users} />
      <KpiCard label={t("admin.webActivity.uniqueWebsites", "Unique Websites")} value={stats.unique_websites} />
      <KpiCard
        label={t("admin.webActivity.avgQueryLength", "Avg Query Length")}
        value={stats.avg_query_length.toFixed(0)}
      />
      <KpiCard
        label={t("admin.webActivity.avgSearchTime", "Avg Search Time")}
        value={`${stats.avg_search_time.toFixed(2)}s`}
      />
    </KpiGrid>
  );
}
