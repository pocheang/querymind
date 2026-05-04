import { useEffect, useMemo, useState } from "react";
import { appApi } from "@/lib/api";
import { ApiSettingsFormFields } from "./ApiSettingsFormFields";
import { ApiSettingsPresets } from "./ApiSettingsPresets";
import { ApiSettingsProviderTabs } from "./ApiSettingsProviderTabs";
import {
  type Provider,
  type ApiConfig,
  PROVIDER_MODELS,
  QUICK_PRESETS,
  PROVIDERS,
  DEFAULT_CONFIG,
} from "./apiSettingsConstants";
import {
  requiresApiKey,
  requiresBaseUrl,
  validateConfig,
  buildApiPayload,
  applyProviderDefaults,
  parseApiResponse,
} from "./apiSettingsUtils";

// Lazy-load modal CSS only when component is used
let modalStylesLoaded = false;
async function loadModalStyles() {
  if (!modalStylesLoaded) {
    await import("@/styles/components/modals.css");
    modalStylesLoaded = true;
  }
}

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function ApiSettings({ isOpen, onClose }: Props) {
  const [config, setConfig] = useState<ApiConfig>(DEFAULT_CONFIG);
  const [showApiKey, setShowApiKey] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Load modal CSS when component opens
  useEffect(() => {
    if (isOpen) {
      loadModalStyles();
      void loadSettings();
    }
  }, [isOpen]);

  const selectedModels = useMemo(() => PROVIDER_MODELS[config.provider] || [], [config.provider]);
  const needsApiKey = requiresApiKey(config.provider);
  const needsBaseUrl = requiresBaseUrl(config.provider);

  const loadSettings = async () => {
    setIsLoading(true);
    setResult(null);
    try {
      const response = await appApi.getUserApiSettings();
      if (response.ok && response.settings) {
        setConfig(parseApiResponse(response.settings));
      }
    } catch (error) {
      setResult({ type: "error", message: error instanceof Error ? error.message : "Failed to load settings" });
    } finally {
      setIsLoading(false);
    }
  };

  const patchConfig = (patch: Partial<ApiConfig>) => {
    setConfig((prev) => ({ ...prev, ...patch }));
    setResult(null);
  };

  const changeProvider = (provider: Provider) => {
    patchConfig(applyProviderDefaults(provider));
  };

  const applyPreset = (preset: typeof QUICK_PRESETS[number]) => {
    const defaults = applyProviderDefaults(preset.provider);
    patchConfig({ ...defaults, model: preset.model });
  };

  const handleCheck = async () => {
    setIsChecking(true);
    setResult(null);
    try {
      const message = validateConfig(config);
      if (message) throw new Error(message);
      const payload = buildApiPayload(config);
      const probe = await appApi.testUserApiSettings(payload);
      if (probe.ok && probe.reachable) {
        const previewSuffix = probe.preview ? ` | Preview: ${probe.preview}` : "";
        setResult({
          type: "success",
          message: `Connection succeeded (${probe.latency_ms}ms)${previewSuffix}`,
        });
      } else {
        setResult({
          type: "error",
          message: probe.message || "Connection failed, check Base URL / API Key / Model",
        });
      }
    } catch (error) {
      setResult({ type: "error", message: error instanceof Error ? error.message : "Config check failed" });
    } finally {
      setIsChecking(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setResult(null);
    try {
      const message = validateConfig(config);
      if (message) throw new Error(message);
      const payload = buildApiPayload(config);
      const saved = await appApi.saveUserApiSettings(payload);
      setConfig((prev) => ({
        ...prev,
        apiKey: "",
        apiKeyMasked: saved.settings?.api_key_masked || prev.apiKeyMasked,
      }));
      setResult({ type: "success", message: "Settings saved. New queries will use this model config." });
      window.setTimeout(onClose, 900);
    } catch (error) {
      setResult({ type: "error", message: error instanceof Error ? error.message : "Save failed" });
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <button type="button" className="api-settings-overlay" onClick={onClose} aria-label="Close settings" />
      <aside className="api-settings-panel" role="dialog" aria-modal="true" aria-labelledby="api-settings-title">
        <header className="settings-header">
          <div className="settings-header-content">
            <div className="settings-icon" aria-hidden="true">API</div>
            <div>
              <h2 id="api-settings-title" className="settings-title">Model API Settings</h2>
              <p className="settings-subtitle">Chat provider, key, model, and generation params</p>
            </div>
          </div>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close settings">
            <span aria-hidden="true">x</span>
          </button>
        </header>

        <div className="settings-content">
          {isLoading ? (
            <div className="settings-loading">Loading settings...</div>
          ) : (
            <>
              <ApiSettingsPresets
                presets={QUICK_PRESETS}
                activeProvider={config.provider}
                activeModel={config.model}
                onApplyPreset={applyPreset}
              />

              <ApiSettingsProviderTabs
                providers={PROVIDERS}
                activeProvider={config.provider}
                onChangeProvider={changeProvider}
              />

              <ApiSettingsFormFields
                config={config}
                selectedModels={selectedModels}
                requiresApiKey={needsApiKey}
                requiresBaseUrl={needsBaseUrl}
                showApiKey={showApiKey}
                onShowApiKeyToggle={() => setShowApiKey((v) => !v)}
                onConfigChange={patchConfig}
              />

              {result && <div className={`test-result ${result.type}`}>{result.message}</div>}
            </>
          )}
        </div>

        <footer className="settings-footer">
          <button type="button" className="api-btn secondary" onClick={handleCheck} disabled={isChecking || isSaving}>
            {isChecking ? "Checking..." : "Check Config"}
          </button>
          <button type="button" className="api-btn primary" onClick={handleSave} disabled={isSaving || isChecking}>
            {isSaving ? "Saving..." : "Save Settings"}
          </button>
        </footer>
      </aside>
    </>
  );
}
