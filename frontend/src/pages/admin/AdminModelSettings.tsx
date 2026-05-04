import type { AdminModelSettingsView } from "@/types/api";

type ModelProvider = "local" | "ollama" | "openai" | "deepseek" | "anthropic" | "custom";

const MODEL_PROVIDERS: ModelProvider[] = ["local", "ollama", "openai", "deepseek", "anthropic", "custom"];
const MODEL_DEFAULTS: Record<ModelProvider, Pick<AdminModelSettingsView, "base_url" | "chat_model" | "reasoning_model" | "embedding_model">> = {
  local: { base_url: "", chat_model: "local-evidence", reasoning_model: "local-evidence", embedding_model: "local-hash-384" },
  ollama: { base_url: "http://localhost:11434", chat_model: "qwen2.5:7b-instruct", reasoning_model: "qwen2.5:7b-instruct", embedding_model: "nomic-embed-text" },
  openai: { base_url: "https://api.openai.com/v1", chat_model: "gpt-5.4-codex", reasoning_model: "gpt-5.4-codex", embedding_model: "text-embedding-3-small" },
  deepseek: { base_url: "https://api.deepseek.com/v1", chat_model: "deepseek-chat", reasoning_model: "deepseek-reasoner", embedding_model: "text-embedding-3-small" },
  anthropic: { base_url: "https://api.anthropic.com/v1", chat_model: "claude-sonnet-4-6", reasoning_model: "claude-sonnet-4-6", embedding_model: "" },
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
        <strong>全局模型配置</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>刷新</button>
          <button type="button" className="secondary tiny-btn" onClick={onTest} disabled={modelTesting || modelSaving}>
            {modelTesting ? "测试中..." : "连接测试"}
          </button>
          <button type="button" className="tiny-btn" onClick={onSave} disabled={modelSaving || modelTesting}>
            {modelSaving ? "保存中..." : "保存配置"}
          </button>
        </div>
      </div>
      <p className="muted">
        生效顺序：用户个人模型设置优先，其次使用这里的全局配置，最后回退到后端 .env。Embedding 模型变更后需要重建索引，避免新旧向量维度不一致。
      </p>
      {modelLoading && <div className="skeleton-list" />}
      {!modelLoading && modelSettings && <>
        <div className="ops-kpi-grid ops-kpi-grid-secondary">
          <div className="ops-kpi-card"><span>全局覆盖</span><strong>{modelSettings.enabled ? "启用" : "停用"}</strong></div>
          <div className="ops-kpi-card"><span>后端</span><strong>{modelSettings.provider}</strong></div>
          <div className="ops-kpi-card"><span>聊天模型</span><strong>{modelSettings.chat_model || "-"}</strong></div>
          <div className="ops-kpi-card"><span>Embedding</span><strong>{modelSettings.embedding_model || "沿用 .env"}</strong></div>
        </div>

        <div className="section-head" style={{ marginTop: 6 }}>
          <strong>运行开关</strong>
        </div>
        <div className="ops-two-col">
          <label className="ops-auto-refresh">
            <input type="checkbox" checked={Boolean(modelSettings.enabled)} onChange={(e) => onPatch({ enabled: e.target.checked })} />
            <span>启用全局模型覆盖</span>
          </label>
          <label className="admin-field">
            <span>后端类型</span>
            <select value={modelSettings.provider} onChange={(e) => changeModelProvider(e.target.value as ModelProvider)}>
              {MODEL_PROVIDERS.map((provider) => <option key={provider} value={provider}>{provider}</option>)}
            </select>
          </label>
        </div>

        {modelSettings.provider !== "local" && <div className="ops-two-col">
          <label className="admin-field">
            <span>Base URL</span>
            <input placeholder="https://api.example.com/v1" value={modelSettings.base_url} onChange={(e) => onPatch({ base_url: e.target.value })} />
          </label>
          <label className="admin-field">
            <span>API Key</span>
            <input
              type="password"
              placeholder={modelSettings.api_key_masked ? `已保存：${modelSettings.api_key_masked}` : modelSettings.provider === "ollama" ? "Ollama 通常留空" : "输入后本地加密保存"}
              value={modelApiKey}
              onChange={(e) => onApiKeyChange(e.target.value)}
            />
          </label>
        </div>}

        <div className="ops-two-col">
          <label className="admin-field">
            <span>聊天模型</span>
            <input placeholder="chat model" value={modelSettings.chat_model} onChange={(e) => onPatch({ chat_model: e.target.value })} />
          </label>
          <label className="admin-field">
            <span>推理模型</span>
            <input placeholder="reasoning model" value={modelSettings.reasoning_model} onChange={(e) => onPatch({ reasoning_model: e.target.value })} />
          </label>
        </div>

        <div className="ops-two-col">
          <label className="admin-field">
            <span>Embedding 模型</span>
            <input
              placeholder={modelSettings.provider === "anthropic" ? "Anthropic 不提供 Embedding，留空沿用 .env" : "embedding model"}
              value={modelSettings.embedding_model}
              onChange={(e) => onPatch({ embedding_model: e.target.value })}
            />
          </label>
          <label className="admin-field">
            <span>Max Tokens</span>
            <input type="number" min={256} max={8192} step={256} value={modelSettings.max_tokens} onChange={(e) => onPatch({ max_tokens: Number(e.target.value) || 2048 })} />
          </label>
        </div>

        <div className="section-head" style={{ marginTop: 6 }}>
          <strong>生成参数</strong>
        </div>
        <label className="admin-field">
          <span>Temperature：{Number(modelSettings.temperature || 0).toFixed(1)}</span>
          <input type="range" min={0} max={2} step={0.1} value={modelSettings.temperature} onChange={(e) => onPatch({ temperature: Number(e.target.value) })} />
        </label>

        {modelTestResult && <div className={`status ${modelTestResult.type === "error" ? "error" : ""}`}>{modelTestResult.message}</div>}

        <div className="ops-trend-list">
          <strong>当前安全边界</strong>
          <div className="ops-diagnostic-list">
            <div><span>密钥回显</span><code>仅显示掩码，不返回明文</code></div>
            <div><span>私网 URL</span><code>默认拦截；Ollama 本地地址例外</code></div>
            <div><span>个人设置</span><code>用户保存的模型配置优先于全局配置</code></div>
          </div>
        </div>
      </>}
    </main>
  );
}
