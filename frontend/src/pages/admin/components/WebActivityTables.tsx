// Web activity detail tables.
import { useTranslation } from "react-i18next";
import { SectionBlock, SubTitle } from "./AdminPrimitives";
import { ADMIN_TABLE, ADMIN_TABLE_WRAP } from "./adminClasses";

interface User {
  user_id: string;
  search_count: number;
}

interface Website {
  domain: string;
  visit_count: number;
  avg_trust_score: number;
}

interface Alert {
  timestamp: string;
  rule_name: string;
  level: string;
  message: string;
  metric_value: number;
  threshold: number;
}

interface Props {
  usersData: User[];
  websitesData: Website[];
  alerts: Alert[];
}

function formatAlertTime(timestamp: string) {
  return new Date(timestamp).toLocaleString(undefined, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** A threshold ladder reads as a ladder; nested ternaries do not. */
function trustTone(score: number): "success" | "warning" | "danger" {
  if (score >= 0.8) return "success";
  if (score >= 0.5) return "warning";
  return "danger";
}

export function WebActivityTables({ usersData, websitesData, alerts }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <>
      {usersData.length > 0 && (
        <SectionBlock>
          <SubTitle>
            {t("admin.webActivity.topUsers", "Top Active Users")}
          </SubTitle>
          <div className={ADMIN_TABLE_WRAP}>
            <table className={ADMIN_TABLE}>
              <thead>
                <tr>
                  <th className="w-[60px] text-center">#</th>
                  <th>{t("admin.webActivity.userId", "User ID")}</th>
                  <th className="w-[120px] text-right">
                    {t("admin.webActivity.searchCount", "Searches")}
                  </th>
                  <th className="w-[100px] text-center">
                    {t("admin.webActivity.activity", "Status")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {usersData.map((user, index) => (
                  <tr key={user.user_id}>
                    <td className="text-center font-semibold text-ink-muted">
                      {index + 1}
                    </td>
                    <td className="font-mono">{user.user_id}</td>
                    <td className="text-right font-semibold">{user.search_count}</td>
                    <td className="text-center">
                      <span className={`badge badge-${user.search_count > 5 ? "success" : "warning"}`}>
                        {user.search_count > 5
                          ? t("admin.webActivity.active", "Active")
                          : t("admin.webActivity.low", "Low")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionBlock>
      )}

      {websitesData.length > 0 && (
        <SectionBlock>
          <SubTitle>
            {t("admin.webActivity.websiteDetails", "Website Access Details")}
          </SubTitle>
          <div className={ADMIN_TABLE_WRAP}>
            <table className={ADMIN_TABLE}>
              <thead>
                <tr>
                  <th className="w-[60px] text-center">#</th>
                  <th>{t("admin.webActivity.domain", "Domain")}</th>
                  <th className="w-[100px] text-right">
                    {t("admin.webActivity.visitCount", "Visits")}
                  </th>
                  <th className="w-[120px] text-center">
                    {t("admin.webActivity.trustScore", "Trust")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {websitesData.map((website, index) => {
                  const trustLevel = trustTone(website.avg_trust_score);

                  return (
                    <tr key={website.domain}>
                      <td className="text-center font-semibold text-ink-muted">
                        {index + 1}
                      </td>
                      <td>
                        <a
                          href={`https://${website.domain}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-xs text-brand-text no-underline hover:underline"
                        >
                          {website.domain}
                        </a>
                      </td>
                      <td className="text-right font-semibold">{website.visit_count}</td>
                      <td className="text-center">
                        <span className={`badge badge-${trustLevel}`}>
                          {(website.avg_trust_score * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionBlock>
      )}

      {alerts.length > 0 && (
        <SectionBlock>
          <SubTitle>
            {t("admin.webActivity.securityAlerts", "Security Alerts (24h)")}
          </SubTitle>
          <div className={ADMIN_TABLE_WRAP}>
            <table className={ADMIN_TABLE}>
              <thead>
                <tr>
                  <th className="w-40">{t("admin.webActivity.time", "Time")}</th>
                  <th className="w-20 text-center">
                    {t("admin.webActivity.level", "Level")}
                  </th>
                  <th className="w-[180px]">{t("admin.webActivity.rule", "Rule")}</th>
                  <th>{t("admin.webActivity.message", "Message")}</th>
                  <th className="w-[120px] text-right">
                    {t("admin.webActivity.value", "Value")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={`${alert.timestamp}-${alert.rule_name}`}>
                    <td className="font-mono text-xs">
                      {formatAlertTime(alert.timestamp)}
                    </td>
                    <td className="text-center">
                      <span className={`badge badge-${alert.level === "critical" ? "danger" : alert.level}`}>
                        {alert.level.toUpperCase()}
                      </span>
                    </td>
                    <td>{alert.rule_name}</td>
                    <td>{alert.message}</td>
                    <td className="text-right font-mono">
                      {alert.metric_value} / {alert.threshold}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionBlock>
      )}
    </>
  );
}
