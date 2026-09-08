import { useTranslation } from "react-i18next";
import { AdminConfigEditor } from "@/pages/admin/AdminConfigEditor";
import type { BenchmarkTrendItem } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Muted, RowActions, SectionHead } from "./components/AdminPrimitives";
import { ADMIN_TABLE } from "./components/adminClasses";

interface Props {
  benchmarkTrends: BenchmarkTrendItem[];
  benchmarkRunning: boolean;
  onRefresh: () => void;
  onReloadConfig: () => void;
  onExportAuditReport: () => void;
  onRunBenchmark: () => void;
  formatAuditTime: (ts?: string | null) => string;
}

export function AdminRagSettings({
  benchmarkTrends,
  benchmarkRunning,
  onRefresh,
  onReloadConfig,
  onExportAuditReport,
  onRunBenchmark,
  formatAuditTime,
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <main className="space-y-6">
      <AdminConfigEditor />

      <SectionHead title={t("admin.ui.ragOps")}>
<RowActions>
          <Button variant="secondary" size="xs" onClick={onRefresh}>{t("common.refresh")}</Button>
          <Button variant="secondary" size="xs" onClick={onReloadConfig}>{t("admin.ui.hotReloadConfig")}</Button>
          <Button variant="secondary" size="xs" onClick={onExportAuditReport}>{t("admin.ui.exportAuditReport")}</Button>
        </RowActions></SectionHead>

      <SectionHead title={t("admin.ui.benchmarkTrend")} className="mt-2">
<RowActions>
          <Button variant="secondary" size="xs" disabled={benchmarkRunning} onClick={onRunBenchmark}>
            {benchmarkRunning ? t("admin.ui.running") : t("admin.ui.runBenchmark")}
          </Button>
        </RowActions></SectionHead>
      {benchmarkTrends.length === 0 && <Muted>{t("admin.ui.noTrend")}</Muted>}
      {benchmarkTrends.length > 0 && (
        <table className={ADMIN_TABLE}>
          <thead>
            <tr>
              <th>{t("admin.ui.time")}</th>
              <th>{t("admin.ui.samples")}</th>
              <th>P50(ms)</th>
              <th>P95(ms)</th>
              <th>Grounding(avg)</th>
              <th>Citations(avg)</th>
            </tr>
          </thead>
          <tbody>
            {[...benchmarkTrends].reverse().map((item, index) => (
              <tr key={`${item.created_at}-${index}`}>
                <td>{formatAuditTime(item.created_at)}</td>
                <td>{item.num_queries}</td>
                <td>{item.latency_ms?.p50 ?? "-"}</td>
                <td>{item.latency_ms?.p95 ?? "-"}</td>
                <td>{item.grounding_support_ratio?.avg ?? "-"}</td>
                <td>{item.citations?.avg ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
