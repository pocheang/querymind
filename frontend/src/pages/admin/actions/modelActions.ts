import { appApi } from "@/lib/api";
import type { AdminModelSettingsView } from "@/types/api";
import type { AdminActionsParams, ErrorHandler } from "./types";

export function createModelActions(params: AdminActionsParams, errorHandler: ErrorHandler) {
  const {
    modelSettings,
    modelApiKey,
    isAdmin,
    setModelSettings,
    setError,
    setModelLoading,
    setModelSaving,
    setModelTesting,
    setModelApiKey,
    setModelTestResult,
    setOps,
  } = params;

  const { handleApiError } = errorHandler;

  const loadModelSettings = async () => {
    if (!isAdmin) return;
    setModelLoading(true);
    try {
      const res = await appApi.adminModelSettings();
      setModelSettings(res.settings);
      setModelApiKey("");
      setModelTestResult(null);
      setError("");
    } catch (e) {
      await handleApiError(e, "加载模型配置失败");
    } finally {
      setModelLoading(false);
    }
  };

  const patchModelSettings = (patch: Partial<AdminModelSettingsView>) => {
    setModelSettings((prev) => ({ ...(prev || {
      enabled: false,
      provider: "local",
      api_key_masked: "",
      base_url: "",
      chat_model: "local-evidence",
      reasoning_model: "local-evidence",
      embedding_model: "local-hash-384",
      temperature: 0.7,
      max_tokens: 2048,
    }), ...patch }));
    setModelTestResult(null);
  };

  const modelPayload = () => {
    const settings = modelSettings || {
      enabled: false,
      provider: "local",
      api_key_masked: "",
      base_url: "",
      chat_model: "local-evidence",
      reasoning_model: "local-evidence",
      embedding_model: "local-hash-384",
      temperature: 0.7,
      max_tokens: 2048,
    };
    return {
      enabled: Boolean(settings.enabled),
      provider: settings.provider,
      api_key: modelApiKey.trim(),
      base_url: settings.base_url.trim(),
      chat_model: settings.chat_model.trim(),
      reasoning_model: (settings.reasoning_model || settings.chat_model).trim(),
      embedding_model: settings.embedding_model.trim(),
      temperature: Math.min(2, Math.max(0, Number(settings.temperature || 0.7))),
      max_tokens: Math.min(8192, Math.max(256, Number(settings.max_tokens || 2048))),
    };
  };

  const validateModelSettings = () => {
    const payload = modelPayload();
    if (!payload.provider) return "请选择模型后端";
    if (payload.provider !== "local" && !payload.base_url) return "Base URL 不能为空";
    if (!payload.chat_model) return "聊天模型不能为空";
    if (payload.provider !== "anthropic" && !payload.embedding_model) return "Embedding 模型不能为空";
    if (!["local", "ollama"].includes(payload.provider) && !payload.api_key && !modelSettings?.api_key_masked) return "云端/API 后端需要 API Key";
    return "";
  };

  const saveModelSettings = async () => {
    const message = validateModelSettings();
    if (message) return setModelTestResult({ type: "error", message });
    setModelSaving(true);
    try {
      const saved = await appApi.adminSaveModelSettings(modelPayload());
      setModelSettings(saved.settings);
      setModelApiKey("");
      setModelTestResult({ type: "success", message: "全局模型配置已保存，新请求将按优先级生效。" });
      setError("");
      await loadOps();
    } catch (e) {
      await handleApiError(e, "保存模型配置失败");
    } finally {
      setModelSaving(false);
    }
  };

  const testModelSettings = async () => {
    const message = validateModelSettings();
    if (message) return setModelTestResult({ type: "error", message });
    setModelTesting(true);
    try {
      const res = await appApi.adminTestModelSettings(modelPayload());
      setModelTestResult({
        type: res.reachable ? "success" : "error",
        message: res.reachable ? `连接成功 (${res.latency_ms}ms)${res.preview ? ` | ${res.preview}` : ""}` : res.message || "连接失败",
      });
      setError("");
    } catch (e) {
      await handleApiError(e, "测试模型配置失败");
    } finally {
      setModelTesting(false);
    }
  };

  const loadOps = async () => {
    if (!isAdmin) return;
    try {
      setOps(await appApi.adminOpsOverview({
        hours: params.opsHours,
        actorUserId: undefined,
        actionKeyword: undefined,
      }));
    } catch (e) {
      await handleApiError(e, "加载运维指标失败");
    }
  };

  return {
    loadModelSettings,
    patchModelSettings,
    saveModelSettings,
    testModelSettings,
  };
}
