import { useTranslation } from "react-i18next";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { AdminBlock, TwoCol } from "./AdminPrimitives";
import { CHART_AXIS, CHART_GRID, CHART_TOOLTIP } from "./adminClasses";

interface ChartData {
  hourlyData: Array<{ hour: string; searches: number }>;
  websitesData: Array<{ domain: string; visit_count: number; avg_trust_score: number }>;
}

interface Props {
  data: ChartData;
}

export function WebActivityCharts({ data }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <TwoCol className="mt-6">
      <AdminBlock titleAs="h3" title={t("admin.webActivity.hourlyDistribution", "24-Hour Activity Distribution")}>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data.hourlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
            <XAxis dataKey="hour" stroke={CHART_AXIS} fontSize={12} />
            <YAxis stroke={CHART_AXIS} fontSize={12} />
            <Tooltip contentStyle={CHART_TOOLTIP} />
            <Bar dataKey="searches" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </AdminBlock>

      <AdminBlock titleAs="h3" title={t("admin.webActivity.topWebsites", "Top 10 Websites")}>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data.websitesData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
            <XAxis type="number" stroke={CHART_AXIS} fontSize={12} />
            <YAxis dataKey="domain" type="category" stroke={CHART_AXIS} fontSize={11} width={120} />
            <Tooltip contentStyle={CHART_TOOLTIP} />
            <Bar dataKey="visit_count" fill="var(--info)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </AdminBlock>
    </TwoCol>
  );
}
