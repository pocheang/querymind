import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";
import { AdminOpsKpiCards } from "./AdminOpsKpiCards";
import { AdminOpsDiagnostics } from "./AdminOpsDiagnostics";
import { AdminOpsTrendCharts } from "./AdminOpsTrendCharts";
import { AdminOpsDataTables } from "./AdminOpsDataTables";

type Props = {
  ops: OpsOverview | null;
  loading: boolean;
  opsHours: number;
  opsAutoRefresh: boolean;
  opsActorUserId: string;
  opsActionKeyword: string;
  actionKeywordOptions: string[];
  actionMax: number;
  resourceMax: number;
  errorMax: number;
  hourlyMax: number;
  formatAuditTime: (ts?: string | null) => string;
  onRefresh: () => void;
  onExportCsv: () => void;
  onOpsHoursChange: (hours: number) => void;
  onOpsAutoRefreshChange: (enabled: boolean) => void;
  onOpsActorUserIdChange: (userId: string) => void;
  onOpsActionKeywordChange: (keyword: string) => void;
};

export function AdminOpsOverview({
  ops,
  loading,
  opsHours,
  opsAutoRefresh,
  opsActorUserId,
  opsActionKeyword,
  actionKeywordOptions,
  actionMax,
  resourceMax,
  errorMax,
  hourlyMax,
  formatAuditTime,
  onRefresh,
  onExportCsv,
  onOpsHoursChange,
  onOpsAutoRefreshChange,
  onOpsActorUserIdChange,
  onOpsActionKeywordChange,
}: Props) {
  const { t } = useTranslation();

  return (
    <main className="panel ops-wrap">
      <div className="section-head">
        <strong>{t("admin.ui.opsMonitor")}</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>
            {t("common.refresh")}
          </button>
          <button type="button" className="secondary tiny-btn" onClick={onExportCsv}>
            {t("admin.ui.exportCsv")}
          </button>
        </div>
      </div>
      <div className="ops-controls-row">
        <select value={opsHours} onChange={(event) => onOpsHoursChange(Number(event.target.value) || 24)}>
          <option value={1}>{t("admin.ui.hour1")}</option>
          <option value={6}>{t("admin.ui.hour6")}</option>
          <option value={24}>{t("admin.ui.hour24")}</option>
          <option value={72}>{t("admin.ui.hour72")}</option>
          <option value={168}>{t("admin.ui.days7")}</option>
        </select>
        <label className="ops-auto-refresh">
          <input type="checkbox" checked={opsAutoRefresh} onChange={(event) => onOpsAutoRefreshChange(event.target.checked)} />
          <span>{t("admin.ui.autoRefresh30")}</span>
        </label>
      </div>
      <div className="ops-two-col ops-filter-row">
        <input
          list="actor-user-options"
          placeholder={t("admin.ui.actorOptional")}
          value={opsActorUserId}
          onChange={(event) => onOpsActorUserIdChange(event.target.value)}
        />
        <select value={opsActionKeyword} onChange={(event) => onOpsActionKeywordChange(event.target.value)}>
          <option value="">{t("admin.ui.allActions")}</option>
          {actionKeywordOptions.map((option) => (
            <option key={`ops-${option}`} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      <p className="muted" style={{ marginTop: -2 }}>{t("admin.ui.filterHelp")}</p>
      {loading && <div className="skeleton-list" />}
      {!loading && ops && (
        <>
          <AdminOpsKpiCards ops={ops} />
          <AdminOpsTrendCharts ops={ops} actionMax={actionMax} resourceMax={resourceMax} errorMax={errorMax} hourlyMax={hourlyMax} />
          <AdminOpsDiagnostics ops={ops} />
          <AdminOpsDataTables ops={ops} formatAuditTime={formatAuditTime} />
        </>
      )}
    </main>
  );
}
