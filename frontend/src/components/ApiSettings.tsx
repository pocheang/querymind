import { useEffect, useMemo, useState } from "react";
import { Info, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { IntegrationsPanel } from "@/features/integrations/IntegrationsPanel";
import { MemoryPanel } from "@/features/memory/MemoryPanel";
import { appApi } from "@/lib/api";
import type { ModelCatalogResponse } from "@/types/api";
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
import { Button } from "@/components/ui/button";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function ApiSettings({ isOpen, onClose }: Readonly<Props>) {
  const { t } = useTranslation();
  const [config, setConfig] = useState<ApiConfig>(DEFAULT_CONFIG);
  const [showApiKey, setShowApiKey] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(isOpen);
  const [catalog, setCatalog] = useState<ModelCatalogResponse | null>(null);

  const selectedModels = useMemo(() => {
    const catalogModels = catalog?.providers?.[config.provider]?.models
      .filter((model) => model.roles.includes("chat") || model.roles.includes("reasoning"))
      .map((model) => model.id);
    return catalogModels?.length ? catalogModels : PROVIDER_MODELS[config.provider] || [];
  }, [catalog, config.provider]);
  const needsApiKey = requiresApiKey(config.provider);
  const needsBaseUrl = requiresBaseUrl(config.provider);

  const loadSettings = async () => {
    setIsLoading(true);
    setResult(null);
    try {
      const [response, catalogResponse] = await Promise.all([
        appApi.getUserApiSettings(),
        appApi.modelCatalog().catch(() => null),
      ]);
      if (catalogResponse) setCatalog(catalogResponse);
      if (response.ok && response.settings) {
        setConfig(parseApiResponse(response.settings));
      }
    } catch (error) {
      setResult({
        type: "error",
        message: error instanceof Error ? error.message : t("components.apiSettings.loadFailed"),
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      void loadSettings();
    } else {
      setIsLoading(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const patchConfig = (patch: Partial<ApiConfig>) => {
    setConfig((prev) => ({ ...prev, ...patch }));
    setResult(null);
  };

  const changeProvider = (provider: Provider) => {
    patchConfig(applyProviderDefaults(provider, catalog?.providers?.[provider]));
  };

  const applyPreset = (preset: (typeof QUICK_PRESETS)[number]) => {
    const defaults = applyProviderDefaults(preset.provider, catalog?.providers?.[preset.provider]);
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
        const previewSuffix = probe.preview ? t("components.apiSettings.preview", { preview: probe.preview }) : "";
        setResult({
          type: "success",
          message: t("components.apiSettings.connectionSuccess", {
            latency: probe.latency_ms,
            preview: previewSuffix,
          }),
        });
      } else {
        setResult({
          type: "error",
          message: probe.message || t("components.apiSettings.connectionFailed"),
        });
      }
    } catch (error) {
      setResult({
        type: "error",
        message: error instanceof Error ? error.message : t("components.apiSettings.checkFailed"),
      });
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
      setResult({ type: "success", message: t("components.apiSettings.saveSuccess") });
      window.setTimeout(onClose, 900);
    } catch (error) {
      setResult({
        type: "error",
        message: error instanceof Error ? error.message : t("components.apiSettings.saveFailed"),
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Scenery. A button rather than a div so the drawer is dismissible by
          pointer without a keyboard trap; Escape and the header's close button
          are the keyboard routes. */}
      <button
        type="button"
        className="fixed inset-0 z-40 bg-stone-900/40 backdrop-blur-sm"
        onClick={onClose}
        aria-label={t("components.apiSettings.close")}
      />
      <aside
        className="glass-panel fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-y-0 border-r-0 shadow-elev-3 animate-in slide-in-from-right duration-300"
        role="dialog"
        aria-modal="true"
        aria-labelledby="api-settings-title"
      >
        <header className="flex shrink-0 items-start justify-between gap-2 border-b border-line-subtle p-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="flex size-9 shrink-0 items-center justify-center rounded-card bg-[image:var(--brand-gradient)] font-mono text-[10px] font-bold text-white shadow-elev-1"
              aria-hidden="true"
            >
              API
            </span>
            <div className="min-w-0">
              <h2 id="api-settings-title" className="text-sm font-bold text-ink">
                {t("components.apiSettings.title")}
              </h2>
              <p className="truncate text-[11px] text-ink-muted">{t("components.apiSettings.subtitle")}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label={t("components.apiSettings.close")}>
            <X aria-hidden="true" />
          </Button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {isLoading ? (
            <p className="py-8 text-center text-xs text-ink-muted">{t("components.apiSettings.loading")}</p>
          ) : (
            <>
              {config.globalOverrideEnabled && (
                <div className="flex gap-2 rounded-card border border-warning-border bg-warning-surface p-2.5">
                  <Info className="mt-0.5 size-3.5 shrink-0 text-warning" aria-hidden="true" />
                  <div className="min-w-0 space-y-1 text-[11px]">
                    <strong className="block text-ink">{t("components.apiSettings.globalOverrideNotice")}</strong>
                    <p className="text-ink-muted">
                      {t("components.apiSettings.globalOverrideDesc", {
                        provider: config.globalProvider,
                        model: config.globalModel,
                      })}
                    </p>
                    <p className="text-ink-muted">{t("components.apiSettings.globalOverrideHint")}</p>
                  </div>
                </div>
              )}

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

              <IntegrationsPanel />

              <MemoryPanel />

              {result && (
                <p
                  role="status"
                  className={cn(
                    "rounded-control border px-2.5 py-1.5 text-[11px]",
                    result.type === "success"
                      ? "border-success-border bg-success-surface text-success"
                      : "border-danger-border bg-danger-surface text-danger"
                  )}
                >
                  {result.message}
                </p>
              )}
            </>
          )}
        </div>

        <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-line-subtle p-4">
          <Button variant="secondary" size="sm" onClick={handleCheck} disabled={isChecking || isSaving}>
            {isChecking ? t("components.apiSettings.checking") : t("components.apiSettings.check")}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={isSaving || isChecking}>
            {isSaving ? t("components.apiSettings.saving") : t("components.apiSettings.save")}
          </Button>
        </footer>
      </aside>
    </>
  );
}
