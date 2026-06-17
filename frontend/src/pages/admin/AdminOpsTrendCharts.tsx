import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
  actionMax: number;
  resourceMax: number;
  errorMax: number;
  hourlyMax: number;
};

export function AdminOpsTrendCharts({ ops, actionMax, resourceMax, errorMax, hourlyMax }: Props) {
  const { t } = useTranslation();

  return (
    <>
      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>{t("admin.ui.topActions")}</strong>
          {ops.top_actions.map((item) => (
            <div key={item.action} className="ops-trend-row">
              <span>{item.action}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (item.count / actionMax) * 100)}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
        <div className="ops-trend-list">
          <strong>{t("admin.ui.topResources")}</strong>
          {ops.top_resource_types.map((item) => (
            <div key={item.resource_type} className="ops-trend-row">
              <span>{item.resource_type}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (item.count / resourceMax) * 100)}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>{t("admin.ui.topErrors")}</strong>
          {ops.top_error_reasons.map((item) => (
            <div key={item.reason} className="ops-trend-row">
              <span title={item.reason}>{item.reason.slice(0, 18)}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (item.count / errorMax) * 100)}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
        <div className="ops-trend-list">
          <strong>{t("admin.ui.serviceHealth")}</strong>
          {Object.entries(ops.services || {}).map(([name, service]) => (
            <div key={name} className="ops-trend-row">
              <span>{name}</span>
              <strong>
                {service.ok
                  ? t("admin.ui.healthy", { latency: service.latency_ms ?? 0 })
                  : t("admin.ui.unhealthy", { error: service.error || "unknown" })}
              </strong>
            </div>
          ))}
        </div>
      </div>

      <div className="ops-trend-list">
        <strong>{t("admin.ui.hourlyTrend")}</strong>
        {ops.hourly.map((item) => (
          <div key={item.bucket} className="ops-trend-row">
            <span>{item.bucket.slice(11, 16)}</span>
            <div className="ops-trend-bar">
              <div className="ops-trend-fill" style={{ width: `${Math.max(4, (item.count / hourlyMax) * 100)}%` }} />
            </div>
            <strong>
              {item.count}/{item.errors}
            </strong>
          </div>
        ))}
      </div>
    </>
  );
}
