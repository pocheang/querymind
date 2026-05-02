import { appApi } from "@/lib/api";
import type { AdminActionsParams, ErrorHandler } from "./types";

export function createOpsActions(params: AdminActionsParams, errorHandler: ErrorHandler) {
  const {
    users,
    opsHours,
    opsActorUserId,
    opsActionKeyword,
    canaryEnabled,
    canaryBaseline,
    canarySafe,
    canarySeed,
    profileState,
    isAdmin,
    setOps,
    setProfileState,
    setBenchmarkTrends,
    setError,
    setStatusText,
    setLoadingOps,
    setBenchmarkRunning,
    setCanaryEnabled,
    setCanaryBaseline,
    setCanarySafe,
    setCanarySeed,
  } = params;

  const { handleApiError } = errorHandler;

  const resolveActorUserId = (raw: string) => {
    const value = raw.trim();
    if (!value) return undefined;
    const exactId = users.find((u) => u.user_id === value);
    if (exactId) return exactId.user_id;
    const byUsername = users.find((u) => (u.username || "").toLowerCase() === value.toLowerCase());
    if (byUsername) return byUsername.user_id;
    const fuzzy = users.filter((u) => (u.username || "").toLowerCase().includes(value.toLowerCase()));
    if (fuzzy.length === 1) return fuzzy[0].user_id;
    return value;
  };

  const loadOps = async () => {
    if (!isAdmin) return;
    setLoadingOps(true);
    try {
      setOps(await appApi.adminOpsOverview({
        hours: opsHours,
        actorUserId: resolveActorUserId(opsActorUserId),
        actionKeyword: opsActionKeyword.trim() || undefined,
      }));
      setError("");
    } catch (e) {
      await handleApiError(e, "加载运维指标失败");
    } finally {
      setLoadingOps(false);
    }
  };

  const loadRagOps = async () => {
    if (!isAdmin) return;
    try {
      const state = await appApi.adminOpsRetrievalProfile();
      setProfileState(state);
      setCanaryEnabled(Boolean(state.canary?.enabled));
      setCanaryBaseline(Number(state.canary?.baseline_percent || 0));
      setCanarySafe(Number(state.canary?.safe_percent || 0));
      setCanarySeed(String(state.canary?.seed || "default"));
      const trends = await appApi.adminBenchmarkTrends({ limit: 30 });
      setBenchmarkTrends(trends.items || []);
      setError("");
    } catch (e) {
      await handleApiError(e, "加载 RAG 运维配置失败");
    }
  };

  const exportOpsCsv = async () => {
    try {
      const csv = await appApi.adminOpsExportCsv({
        hours: opsHours,
        actorUserId: resolveActorUserId(opsActorUserId),
        actionKeyword: opsActionKeyword.trim() || undefined,
      });
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ops_report_${new Date().toISOString().replace(/[:.]/g, "-")}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatusText("运维报表导出成功");
    } catch (e) {
      await handleApiError(e, "导出失败");
    }
  };

  const setRetrievalProfile = async (profile: string, followDefault = false) => {
    try {
      const next = await appApi.adminOpsSetRetrievalProfile({ profile, followConfigDefault: followDefault });
      setProfileState(next);
      setStatusText(`已切换检索策略为 ${next.active_profile}`);
      setError("");
    } catch (e) {
      await handleApiError(e, "切换策略失败");
    }
  };

  const saveCanary = async () => {
    try {
      const next = await appApi.adminOpsSetCanary({
        enabled: canaryEnabled,
        baselinePercent: canaryBaseline,
        safePercent: canarySafe,
        seed: canarySeed.trim() || "default",
      });
      setProfileState(next);
      setStatusText("灰度发布配置已保存");
      setError("");
    } catch (e) {
      await handleApiError(e, "保存灰度配置失败");
    }
  };

  const runBenchmark = async () => {
    setBenchmarkRunning(true);
    try {
      const strategy = profileState?.active_profile || "advanced";
      await appApi.adminRunBenchmark({ maxQueries: 20, strategy });
      const trends = await appApi.adminBenchmarkTrends({ limit: 30 });
      setBenchmarkTrends(trends.items || []);
      setStatusText("基准任务完成，趋势已更新");
    } catch (e) {
      await handleApiError(e, "运行基准失败");
    } finally {
      setBenchmarkRunning(false);
    }
  };

  const reloadConfig = async () => {
    try {
      await appApi.adminReloadConfig();
      await loadRagOps();
      setStatusText("配置热加载成功");
    } catch (e) {
      await handleApiError(e, "配置热加载失败");
    }
  };

  const rollbackRuntime = async () => {
    try {
      const res = await appApi.adminOpsRollback();
      setProfileState(res.state);
      setCanaryEnabled(false);
      setCanaryBaseline(0);
      setCanarySafe(0);
      setStatusText("已执行一键回滚（baseline）");
    } catch (e) {
      await handleApiError(e, "回滚失败");
    }
  };

  const exportAuditReportMd = async () => {
    try {
      const text = await appApi.adminOpsExportAuditReportMd({ hours: opsHours });
      const blob = new Blob([text], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ops_audit_report_${new Date().toISOString().replace(/[:.]/g, "-")}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatusText("审计 Markdown 报告导出成功");
    } catch (e) {
      await handleApiError(e, "导出审计报告失败");
    }
  };

  return {
    loadOps,
    loadRagOps,
    exportOpsCsv,
    setRetrievalProfile,
    saveCanary,
    runBenchmark,
    reloadConfig,
    rollbackRuntime,
    exportAuditReportMd,
  };
}
