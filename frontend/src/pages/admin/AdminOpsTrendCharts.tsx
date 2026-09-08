import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";
import { AdminBlock, TrendRow, TwoCol } from "./components/AdminPrimitives";

type Props = {
  ops: OpsOverview;
  actionMax: number;
  resourceMax: number;
  errorMax: number;
  hourlyMax: number;
};

const share = (count: number, max: number) => Math.max(4, (count / max) * 100);

export function AdminOpsTrendCharts({ ops, actionMax, resourceMax, errorMax, hourlyMax }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <>
      <TwoCol>
        <AdminBlock title={t("admin.ui.topActions")} titleAs="strong">
          {ops.top_actions.map((item) => (
            <TrendRow key={item.action} label={item.action} value={item.count} percent={share(item.count, actionMax)} />
          ))}
        </AdminBlock>
        <AdminBlock title={t("admin.ui.topResources")} titleAs="strong">
          {ops.top_resource_types.map((item) => (
            <TrendRow
              key={item.resource_type}
              label={item.resource_type}
              value={item.count}
              percent={share(item.count, resourceMax)}
            />
          ))}
        </AdminBlock>
      </TwoCol>

      <TwoCol>
        <AdminBlock title={t("admin.ui.topErrors")} titleAs="strong">
          {ops.top_error_reasons.map((item) => (
            <TrendRow
              key={item.reason}
              label={item.reason.slice(0, 18)}
              title={item.reason}
              value={item.count}
              percent={share(item.count, errorMax)}
            />
          ))}
        </AdminBlock>
        <AdminBlock title={t("admin.ui.serviceHealth")} titleAs="strong">
          {Object.entries(ops.services || {}).map(([name, service]) => (
            <TrendRow
              key={name}
              label={name}
              value={
                service.ok
                  ? t("admin.ui.healthy", { latency: service.latency_ms ?? 0 })
                  : t("admin.ui.unhealthy", { error: service.error || "unknown" })
              }
            />
          ))}
        </AdminBlock>
      </TwoCol>

      <AdminBlock title={t("admin.ui.hourlyTrend")} titleAs="strong">
        {ops.hourly.map((item) => (
          <TrendRow
            key={item.bucket}
            label={item.bucket.slice(11, 16)}
            value={`${item.count}/${item.errors}`}
            percent={share(item.count, hourlyMax)}
          />
        ))}
      </AdminBlock>
    </>
  );
}
