import type { AdminModelSettingsView } from "@/types/api";
import { useTranslation } from "react-i18next";
import { AdminFormField, AdminFormSelect } from "@/components/AdminFormField";

type ModelProvider = "local" | "ollama" | "openai" | "deepseek" | "anthropic" | "custom";

const MODEL_PROVIDERS: ModelProvider[] = ["local", "ollama", "openai", "deepseek", "anthropic", "custom"];
const MODEL_DEFAULTS: Record<ModelProvider, Pick<AdminModelSettingsView, "base_url" | "chat_model" | "reasoning_model" | "embedding_model">> = {
  local: { base_url: "", chat_model: "local-evidence", reasoning_model: "local-evidence", embedding_model: "local-hash-384" },
  ollama: { base_url: "http://localhost:11434", chat_model: "qwen2.5:7b-instruct", reasoning_model: "qwen2.5:7b-instruct", embedding_model: "nomic-embed-text" },
  openai: { base_url: "https://api.openai.com/v1", chat_model: "gpt-5.4-codex", reasoning_model: "gpt-5.4-codex", embedding_model: "text-embedding-3-small" },
  deepseek: { base_url: "https://api.deepseek.com/v1", chat_model: "deepseek-chat", reasoning_model: "deepseek-reasoner", embedding_model: "text-embedding-3-small" },
  anthropic: { base_url: "https://api.anthropic.com", chat_model: "claude-sonnet-4-6", reasoning_model: "claude-sonnet-4-6", embedding_model: "" },
  custom: { base_url: "", chat_model: "", reasoning_model: "", embedding_model: "" },
};

interface Props {
  modelSettings: AdminModelSettingsView | null;
  modelLoading: boolean;
  modelSaving: boolean;
  modelTesting: boolean;
  modelTestResult: { type: "success" | "error"; message: string } | null;
  onRefresh: () => void;
  onSave: () => void;
  onTest: () => void;
  onPatch: (patch: Partial<AdminModelSettingsView>) => void;
  modelApiKey: string;
  onApiKeyChange: (key: string) => void;
}

export function AdminModelSettings({
  modelSettings,
  modelLoading,
  modelSaving,
  modelTesting,
  modelTestResult,
  onRefresh,
  onSave,
  onTest,
  onPatch,
  modelApiKey,
  onApiKeyChange,
}: Props) {
  const { t } = useTranslation();

  const changeModelProvider = (provider: ModelProvider) => {
    const defaults = MODEL_DEFAULTS[provider];
    onPatch({
      provider,
      api_key_masked: "",
      base_url: defaults.base_url,
      chat_model: defaults.chat_model,
      reasoning_model: defaults.reasoning_model,
      embedding_model: defaults.embedding_model,
    });
    onApiKeyChange("");
  };

  return (
    <main className="panel ops-wrap">
      <div className="section-head">
        <strong>{t("admin.ui.globalModelConfig")}</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>{t("common.refresh")}</button>
          <button type="button" className="secondary tiny-btn" onClick={onTest} disabled={modelTesting || modelSaving}>
            {modelTesting ? t("admin.ui.testing") : t("admin.ui.connectionTest")}
          </button>
          <button type="button" className="tiny-btn" onClick={onSave} disabled={modelSaving || modelTesting}>
            {modelSaving ? t("admin.ui.saving") : t("admin.ui.saveConfig")}
          </button>
        </div>
      </div>
      <p className="muted">{t("admin.ui.modelConfigHint")}</p>
      {modelLoading && <div className="skeleton-list" />}
      {!modelLoading && modelSettings && <>
        <div className="ops-kpi-grid ops-kpi-grid-secondary">
          <div className="ops-kpi-card"><span>{t("admin.ui.globalOverride")}</span><strong>{modelSettings.enabled ? t("admin.ui.enabled") : t("admin.ui.disabled")}</strong></div>
          <div className="ops-kpi-card"><span>{t("admin.ui.backend")}</span><strong>{modelSettings.provider}</strong></div>
          <div className="ops-kpi-card"><span>{t("admin.ui.chatModel")}</span><strong>{modelSettings.chat_model || "-"}</strong></div>
          <div className="ops-kpi-card"><span>{t("admin.ui.embeddingModel")}</span><strong>{modelSettings.embedding_model || t("admin.ui.useEnv")}</strong></div>
        </div>

        <div className="section-head" style={{ marginTop: 6 }}>
          <strong>{t("admin.ui.runtimeSwitch")}</strong>
        </div>
        <div className="ops-two-col">
          <label className="ops-auto-refresh">
            <input type="checkbox" checked={Boolean(modelSettings.enabled)} onChange={(e) => onPatch({ enabled: e.target.checked })} />
            <span>{t("admin.ui.enableGlobalModelOverride")}</span>
          </label>
          <AdminFormSelect
            label={t("admin.ui.backendType")}
            value={modelSettings.provider}
            onChange={(value) => changeModelProvider(value as ModelProvider)}
            options={MODEL_PROVIDERS}
          />
        </div>

        {modelSettings.provider !== "local" && <div className="ops-two-col">
          <AdminFormField
            label="Base URL"
            value={modelSettings.base_url}
            onChange={(value) => onPatch({ base_url: value })}
            placeholder="https://api.example.com/v1"
          />
          <AdminFormField
            label="API Key"
            type="password"
            value={modelApiKey}
            onChange={onApiKeyChange}
            placeholder={modelSettings.api_key_masked ? t("admin.ui.apiKeySaved", { value: modelSettings.api_key_masked }) : modelSettings.provider === "ollama" ? t("admin.ui.ollamaBlank") : t("admin.ui.encryptedSave")}
          />
        </div>}

        <div className="ops-two-col">
          <AdminFormField
            label={t("admin.ui.chatModel")}
            value={modelSettings.chat_model}
            onChange={(value) => onPatch({ chat_model: value })}
            placeholder="chat model"
          />
          <AdminFormField
            label={t("admin.ui.reasoningModel")}
            value={modelSettings.reasoning_model}
            onChange={(value) => onPatch({ reasoning_model: value })}
            placeholder="reasoning model"
          />
        </div>

        <div className="ops-two-col">
          <AdminFormField
            label={t("admin.ui.embeddingModel")}
            value={modelSettings.embedding_model}
            onChange={(value) => onPatch({ embedding_model: value })}
            placeholder={modelSettings.provider === "anthropic" ? t("admin.ui.anthropicEmbeddingHint") : "embedding model"}
          />
          <AdminFormField
            label="Max Tokens"
            type="number"
            value={String(modelSettings.max_tokens)}
            onChange={(value) => onPatch({ max_tokens: Number(value) || 2048 })}
          />
        </div>

        <div className="section-head" style={{ marginTop: 6 }}>
          <strong>{t("admin.ui.generationParams")}</strong>
        </div>
        <label className="admin-field">
          <span>Temperature：{Number(modelSettings.temperature || 0).toFixed(1)}</span>
          <input type="range" min={0} max={2} step={0.1} value={modelSettings.temperature} onChange={(e) => onPatch({ temperature: Number(e.target.value) })} />
        </label>

        {modelTestResult && <div className={`status ${modelTestResult.type === "error" ? "error" : ""}`}>{modelTestResult.message}</div>}

        <div className="ops-trend-list">
          <strong>{t("admin.ui.securityBoundary")}</strong>
          <div className="ops-diagnostic-list">
            <div><span>{t("admin.ui.keyEcho")}</span><code>{t("admin.ui.keyEchoDesc")}</code></div>
            <div><span>{t("admin.ui.privateUrl")}</span><code>{t("admin.ui.privateUrlDesc")}</code></div>
            <div><span>{t("admin.ui.personalSettings")}</span><code>{t("admin.ui.personalSettingsDesc")}</code></div>
          </div>
        </div>
      </>}
    </main>
  );
}
