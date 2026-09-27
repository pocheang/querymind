import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { appApi } from "@/lib/api";
import type { ThreatIntelSource, ThreatIntelSourceStatus } from "@/types/api";
import { Muted, RowActions, SectionHead, StatePanel } from "./components/AdminPrimitives";
import { ADMIN_TABLE, ADMIN_TABLE_WRAP } from "./components/adminClasses";

const STATE_VARIANT = { current: "success", stale: "warning", empty: "danger" } as const;

/**
 * The offline threat-intelligence store: how current each source is, and a way
 * to refresh it.
 *
 * Sync is manual by default (decision Q2); this is where an operator sees a
 * source going stale and starts one. The panel fetches its own status rather
 * than riding the ops overview's state: it has its own lifecycle (a sync is
 * queued, then finishes minutes later) and nothing else on the page reads it.
 */
export function AdminThreatIntelPanel() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<ThreatIntelSourceStatus[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await appApi.adminThreatIntelStatus();
      setSources(res.sources);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const sync = async (source: ThreatIntelSource | "all") => {
    try {
      await appApi.adminThreatIntelSync(source);
      setNotice(t("admin.threatIntel.queued"));
    } catch {
      setNotice(t("admin.threatIntel.syncFailed"));
    }
  };

  const stateLabel = (state: ThreatIntelSourceStatus["state"]) => {
    switch (state) {
      case "current":
        return t("admin.threatIntel.states.current");
      case "stale":
        return t("admin.threatIntel.states.stale");
      default:
        return t("admin.threatIntel.states.empty");
    }
  };

  return (
    <section className="space-y-3" aria-label={t("admin.threatIntel.title")}>
      <SectionHead title={t("admin.threatIntel.title")} description={t("admin.threatIntel.description")}>
        <RowActions>
          <Button variant="secondary" size="xs" onClick={() => void refresh()}>
            {t("common.refresh")}
          </Button>
          <Button size="xs" onClick={() => void sync("all")}>
            {t("admin.threatIntel.syncAll")}
          </Button>
        </RowActions>
      </SectionHead>
      {notice && <Muted>{notice}</Muted>}
      {failed && <StatePanel tone="error">{t("admin.threatIntel.loadFailed")}</StatePanel>}
      {sources && (
        <div className={ADMIN_TABLE_WRAP}>
          <table className={ADMIN_TABLE}>
            <thead>
              <tr>
                <th>{t("admin.threatIntel.source")}</th>
                <th>{t("admin.threatIntel.state")}</th>
                <th>{t("admin.threatIntel.records")}</th>
                <th>{t("admin.threatIntel.lastSync")}</th>
                <th>{t("admin.threatIntel.version")}</th>
                <th>{t("admin.threatIntel.lastAttempt")}</th>
                <th>
                  <span className="sr-only">{t("admin.threatIntel.sync")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sources.map((row) => (
                <tr key={row.source}>
                  <td className="font-mono font-semibold">{row.source}</td>
                  <td>
                    <Badge variant={STATE_VARIANT[row.state]} size="xs">
                      {stateLabel(row.state)}
                    </Badge>
                  </td>
                  <td className="font-mono">{row.records.toLocaleString()}</td>
                  <td className="font-mono">
                    {row.age_days === null
                      ? t("admin.threatIntel.never")
                      : t("admin.threatIntel.ageDays", { days: row.age_days, limit: row.stale_after_days })}
                  </td>
                  <td className="font-mono">{row.data_version || "-"}</td>
                  <td className="max-w-64 truncate" title={row.last_attempt_detail}>
                    {row.last_attempt_status || "-"}
                    {row.last_attempt_status === "failed" && row.last_attempt_detail
                      ? `: ${row.last_attempt_detail}`
                      : ""}
                  </td>
                  <td>
                    <Button variant="ghost" size="xs" onClick={() => void sync(row.source)}>
                      {t("admin.threatIntel.sync")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
