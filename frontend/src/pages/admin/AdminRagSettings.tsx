import { useTranslation } from "react-i18next";
import type { BenchmarkTrendItem, RetrievalProfileState } from "@/types/api";

interface Props {
  profileState: RetrievalProfileState | null;
  benchmarkTrends: BenchmarkTrendItem[];
  benchmarkRunning: boolean;
  canaryEnabled: boolean;
  canaryBaseline: number;
  canarySafe: number;
  canarySeed: string;
  onCanaryEnabledChange: (enabled: boolean) => void;
  onCanaryBaselineChange: (value: number) => void;
  onCanarySafeChange: (value: number) => void;
  onCanarySeedChange: (seed: string) => void;
  onRefresh: () => void;
  onReloadConfig: () => void;
  onRollback: () => void;
  onExportAuditReport: () => void;
  onSetProfile: (profile: string, followDefault?: boolean) => void;
  onSaveCanary: () => void;
  onRunBenchmark: () => void;
  formatAuditTime: (ts?: string | null) => string;
}

export function AdminRagSettings({
  profileState,
  benchmarkTrends,
  benchmarkRunning,
  canaryEnabled,
  canaryBaseline,
  canarySafe,
  canarySeed,
  onCanaryEnabledChange,
  onCanaryBaselineChange,
  onCanarySafeChange,
  onCanarySeedChange,
  onRefresh,
  onReloadConfig,
  onRollback,
  onExportAuditReport,
  onSetProfile,
  onSaveCanary,
  onRunBenchmark,
  formatAuditTime,
}: Props) {
  const { t } = useTranslation();

  return (
    <main className="panel ops-wrap">
      <div className="section-head">
        <strong>{t("admin.ui.ragOps")}</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>{t("common.refresh")}</button>
          <button type="button" className="secondary tiny-btn" onClick={onReloadConfig}>{t("admin.ui.hotReloadConfig")}</button>
          <button type="button" className="secondary tiny-btn" onClick={onRollback}>{t("admin.ui.rollback")}</button>
          <button type="button" className="secondary tiny-btn" onClick={onExportAuditReport}>{t("admin.ui.exportAuditReport")}</button>
        </div>
      </div>

      <p className="muted">{t("admin.ui.ragOpsHint")}</p>
      <div className="ops-kpi-grid ops-kpi-grid-secondary">
        <div className="ops-kpi-card"><span>{t("admin.ui.activeProfile")}</span><strong>{profileState?.active_profile || "-"}</strong></div>
        <div className="ops-kpi-card"><span>{t("admin.ui.configDefault")}</span><strong>{profileState?.config_default_profile || "-"}</strong></div>
        <div className="ops-kpi-card"><span>{t("admin.ui.followConfig")}</span><strong>{profileState?.follow_config_default ? t("common.yes") : t("common.no")}</strong></div>
        <div className="ops-kpi-card"><span>{t("admin.ui.lastUpdated")}</span><strong>{profileState?.updated_at ? formatAuditTime(profileState.updated_at) : "-"}</strong></div>
      </div>

      <div className="section-head" style={{ marginTop: 6 }}>
        <strong>{t("admin.ui.strategyConfig")}</strong>
      </div>
      <div className="row-actions wrap">
        <button type="button" className="primary-action-btn" onClick={() => onSetProfile("advanced")}>{t("admin.ui.switchAdvanced")}</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("baseline")}>{t("admin.ui.switchBaseline")}</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("safe")}>{t("admin.ui.switchSafe")}</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("advanced", true)}>{t("admin.ui.followConfigDefault")}</button>
      </div>

      <div className="section-head" style={{ marginTop: 8 }}>
        <strong>{t("admin.ui.canary")}</strong>
      </div>
      <div className="ops-two-col">
        <label className="ops-auto-refresh">
          <input type="checkbox" checked={canaryEnabled} onChange={(event) => onCanaryEnabledChange(event.target.checked)} />
          <span>{t("admin.ui.enableCanary")}</span>
        </label>
        <input placeholder="seed" value={canarySeed} onChange={(event) => onCanarySeedChange(event.target.value)} />
      </div>
      <div className="ops-two-col">
        <label className="admin-field">
          <span>{t("admin.ui.baselinePercent")}</span>
          <input type="number" min={0} max={100} value={canaryBaseline} onChange={(event) => onCanaryBaselineChange(Number(event.target.value) || 0)} />
        </label>
        <label className="admin-field">
          <span>{t("admin.ui.safePercent")}</span>
          <input type="number" min={0} max={100} value={canarySafe} onChange={(event) => onCanarySafeChange(Number(event.target.value) || 0)} />
        </label>
      </div>
      <div className="row-actions">
        <button type="button" className="primary-action-btn" onClick={onSaveCanary}>{t("admin.ui.saveCanary")}</button>
      </div>

      <div className="section-head" style={{ marginTop: 8 }}>
        <strong>{t("admin.ui.benchmarkTrend")}</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" disabled={benchmarkRunning} onClick={onRunBenchmark}>
            {benchmarkRunning ? t("admin.ui.running") : t("admin.ui.runBenchmark")}
          </button>
        </div>
      </div>
      {benchmarkTrends.length === 0 && <p className="muted">{t("admin.ui.noTrend")}</p>}
      {benchmarkTrends.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>{t("admin.ui.time")}</th>
              <th>{t("admin.ui.strategy")}</th>
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
                <td>{item.strategy}</td>
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
