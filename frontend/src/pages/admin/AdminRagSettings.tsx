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
  return (
    <main className="panel ops-wrap">
      <div className="section-head">
        <strong>RAG / Agent 策略运营</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>刷新</button>
          <button type="button" className="secondary tiny-btn" onClick={onReloadConfig}>热加载配置</button>
          <button type="button" className="secondary tiny-btn" onClick={onRollback}>一键回滚</button>
          <button type="button" className="secondary tiny-btn" onClick={onExportAuditReport}>导出审计报告(MD)</button>
        </div>
      </div>

      <p className="muted">这里集中管理检索策略、灰度发布和基准趋势。策略默认参考 RAGFlow 的 baseline / advanced / safe。</p>
      <div className="ops-kpi-grid ops-kpi-grid-secondary">
        <div className="ops-kpi-card"><span>当前策略</span><strong>{profileState?.active_profile || "-"}</strong></div>
        <div className="ops-kpi-card"><span>配置默认</span><strong>{profileState?.config_default_profile || "-"}</strong></div>
        <div className="ops-kpi-card"><span>跟随配置</span><strong>{profileState?.follow_config_default ? "是" : "否"}</strong></div>
        <div className="ops-kpi-card"><span>上次更新时间</span><strong>{profileState?.updated_at ? formatAuditTime(profileState.updated_at) : "-"}</strong></div>
      </div>

      <div className="section-head" style={{ marginTop: 6 }}>
        <strong>策略配置</strong>
      </div>
      <div className="row-actions wrap">
        <button type="button" onClick={() => onSetProfile("advanced")}>切换 Advanced</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("baseline")}>切换 Baseline</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("safe")}>切换 Safe</button>
        <button type="button" className="secondary" onClick={() => onSetProfile("advanced", true)}>跟随配置默认</button>
      </div>

      <div className="section-head" style={{ marginTop: 8 }}>
        <strong>灰度发布（Canary）</strong>
      </div>
      <div className="ops-two-col">
        <label className="ops-auto-refresh">
          <input type="checkbox" checked={canaryEnabled} onChange={(e) => onCanaryEnabledChange(e.target.checked)} />
          <span>启用灰度分流</span>
        </label>
        <input placeholder="seed" value={canarySeed} onChange={(e) => onCanarySeedChange(e.target.value)} />
      </div>
      <div className="ops-two-col">
        <label className="admin-field">
          <span>Baseline 百分比</span>
          <input type="number" min={0} max={100} value={canaryBaseline} onChange={(e) => onCanaryBaselineChange(Number(e.target.value) || 0)} />
        </label>
        <label className="admin-field">
          <span>Safe 百分比</span>
          <input type="number" min={0} max={100} value={canarySafe} onChange={(e) => onCanarySafeChange(Number(e.target.value) || 0)} />
        </label>
      </div>
      <div className="row-actions">
        <button type="button" onClick={onSaveCanary}>保存灰度配置</button>
      </div>

      <div className="section-head" style={{ marginTop: 8 }}>
        <strong>真实基准趋势</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" disabled={benchmarkRunning} onClick={onRunBenchmark}>
            {benchmarkRunning ? "运行中..." : "运行基准"}
          </button>
        </div>
      </div>
      {benchmarkTrends.length === 0 && <p className="muted">暂无趋势数据。点击"运行基准"后会自动记录。</p>}
      {benchmarkTrends.length > 0 && (
        <table className="table">
          <thead><tr><th>时间</th><th>策略</th><th>样本数</th><th>P50(ms)</th><th>P95(ms)</th><th>Grounding(avg)</th><th>Citations(avg)</th></tr></thead>
          <tbody>
            {[...benchmarkTrends].reverse().map((x, idx) => (
              <tr key={`${x.created_at}-${idx}`}>
                <td>{formatAuditTime(x.created_at)}</td>
                <td>{x.strategy}</td>
                <td>{x.num_queries}</td>
                <td>{x.latency_ms?.p50 ?? "-"}</td>
                <td>{x.latency_ms?.p95 ?? "-"}</td>
                <td>{x.grounding_support_ratio?.avg ?? "-"}</td>
                <td>{x.citations?.avg ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
