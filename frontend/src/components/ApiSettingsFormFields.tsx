type Provider = "local" | "openai" | "anthropic" | "deepseek" | "ollama" | "custom";

type ApiConfig = {
  provider: Provider;
  apiKey: string;
  apiKeyMasked: string;
  baseUrl: string;
  model: string;
  temperature: number;
  maxTokens: number;
};

type Props = {
  config: ApiConfig;
  selectedModels: string[];
  requiresApiKey: boolean;
  requiresBaseUrl: boolean;
  showApiKey: boolean;
  onShowApiKeyToggle: () => void;
  onConfigChange: (patch: Partial<ApiConfig>) => void;
};

export function ApiSettingsFormFields({
  config,
  selectedModels,
  requiresApiKey,
  requiresBaseUrl,
  showApiKey,
  onShowApiKeyToggle,
  onConfigChange,
}: Props) {
  return (
    <>
      <section className="settings-section">
        <div className="settings-note">
          These settings apply to chat and reasoning calls. Embeddings are configured globally by an admin so the vector index stays consistent.
        </div>
      </section>

      {requiresApiKey && (
        <section className="settings-section">
          <label className="section-label" htmlFor="api-key-input">API Key</label>
          <div className="input-with-action">
            <input
              id="api-key-input"
              type={showApiKey ? "text" : "password"}
              className="api-input-field"
              placeholder={config.apiKeyMasked ? `Saved: ${config.apiKeyMasked}` : "sk-..."}
              value={config.apiKey}
              onChange={(e) => onConfigChange({ apiKey: e.target.value, apiKeyMasked: "" })}
            />
            <button type="button" className="input-action-btn" onClick={onShowApiKeyToggle}>
              {showApiKey ? "Hide" : "Show"}
            </button>
          </div>
        </section>
      )}

      {requiresBaseUrl && (
        <section className="settings-section">
          <label className="section-label" htmlFor="base-url-input">Base URL</label>
          <input
            id="base-url-input"
            type="text"
            className="api-input-field"
            placeholder="https://api.example.com/v1"
            value={config.baseUrl}
            onChange={(e) => onConfigChange({ baseUrl: e.target.value })}
          />
        </section>
      )}

      <section className="settings-section">
        <label className="section-label" htmlFor="model-input">Model</label>
        {selectedModels.length > 0 ? (
          <select
            id="model-input"
            className="api-select"
            value={config.model}
            onChange={(e) => onConfigChange({ model: e.target.value })}
          >
            {selectedModels.map((model) => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        ) : (
          <input
            id="model-input"
            type="text"
            className="api-input-field"
            placeholder="model-name"
            value={config.model}
            onChange={(e) => onConfigChange({ model: e.target.value })}
          />
        )}
      </section>

      <section className="settings-section">
        <label className="section-label" htmlFor="temperature-input">
          Temperature
          <span className="label-value">{Number(config.temperature).toFixed(1)}</span>
        </label>
        <input
          id="temperature-input"
          type="range"
          className="api-slider"
          min="0"
          max="2"
          step="0.1"
          value={config.temperature}
          onChange={(e) => onConfigChange({ temperature: Number(e.target.value) })}
        />
        <div className="slider-labels">
          <span>Stable</span>
          <span>Balanced</span>
          <span>Creative</span>
        </div>
      </section>

      <section className="settings-section">
        <label className="section-label" htmlFor="max-tokens-input">
          Max Tokens
          <span className="label-value">{config.maxTokens}</span>
        </label>
        <input
          id="max-tokens-input"
          type="range"
          className="api-slider"
          min="256"
          max="8192"
          step="256"
          value={config.maxTokens}
          onChange={(e) => onConfigChange({ maxTokens: Number(e.target.value) })}
        />
        <div className="slider-labels">
          <span>256</span>
          <span>4096</span>
          <span>8192</span>
        </div>
      </section>
    </>
  );
}
