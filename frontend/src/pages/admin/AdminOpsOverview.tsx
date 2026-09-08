import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";
import { AdminOpsKpiCards } from "./AdminOpsKpiCards";
import { AdminOpsDiagnostics } from "./AdminOpsDiagnostics";
import { AdminOpsTrendCharts } from "./AdminOpsTrendCharts";
import { AdminOpsDataTables } from "./AdminOpsDataTables";
import { Button } from "@/components/ui/button";
import {
  AdminSkeleton,
  ControlsRow,
  FilterRow,
  Muted,
  RowActions,
  SectionHead,
} from "./components/AdminPrimitives";
import { ADMIN_FIELD } from "./components/adminClasses";
import { cn } from "@/lib/utils";

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
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <main className="space-y-6">
      <SectionHead title={t("admin.ui.opsMonitor")}>
<RowActions>
          <Button variant="secondary" size="xs" onClick={onRefresh}>
            {t("common.refresh")}
          </Button>
          <Button variant="secondary" size="xs" onClick={onExportCsv}>
            {t("admin.ui.exportCsv")}
          </Button>
        </RowActions></SectionHead>
      <ControlsRow>
        <select
          className={cn(ADMIN_FIELD, "w-auto min-w-36 font-mono")}
          value={opsHours}
          onChange={(event) => onOpsHoursChange(Number(event.target.value) || 24)}
        >
          <option value={1}>{t("admin.ui.hour1")}</option>
          <option value={6}>{t("admin.ui.hour6")}</option>
          <option value={24}>{t("admin.ui.hour24")}</option>
          <option value={72}>{t("admin.ui.hour72")}</option>
          <option value={168}>{t("admin.ui.days7")}</option>
        </select>
        <label className="flex shrink-0 cursor-pointer select-none items-center gap-2 whitespace-nowrap rounded-control border border-transparent px-3 py-2 transition-colors hover:border-brand-border hover:bg-brand-surface">
          <input
            className="size-4 shrink-0 accent-[var(--brand)]"
            type="checkbox"
            checked={opsAutoRefresh}
            onChange={(event) => onOpsAutoRefreshChange(event.target.checked)}
          />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            {t("admin.ui.autoRefresh30")}
          </span>
        </label>
      </ControlsRow>
      <FilterRow>
        <input
          className={ADMIN_FIELD}
          list="actor-user-options"
          placeholder={t("admin.ui.actorOptional")}
          value={opsActorUserId}
          onChange={(event) => onOpsActorUserIdChange(event.target.value)}
        />
        <select
          className={ADMIN_FIELD}
          value={opsActionKeyword}
          onChange={(event) => onOpsActionKeywordChange(event.target.value)}
        >
          <option value="">{t("admin.ui.allActions")}</option>
          {actionKeywordOptions.map((option) => (
            <option key={`ops-${option}`} value={option}>
              {option}
            </option>
          ))}
        </select>
      </FilterRow>
      <Muted className="-mt-0.5">{t("admin.ui.filterHelp")}</Muted>
      {loading && <AdminSkeleton />}
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
