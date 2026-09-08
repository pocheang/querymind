import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AdminFormField, AdminFormSelect } from "@/components/AdminFormField";
import { appApi } from "@/lib/api";
import { normalizeModelTemperature } from "@/lib/model-temperature";
import { effectiveRow, effectiveStatusPill } from "./effectiveComponentVariants";
import type {
  AdminModelSettingsView,
  EffectiveModelComponent,
  ModelCatalogItem,
  ModelCatalogResponse,
  ModelProvider,
  ProviderCatalogEntry,
} from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  AdminBlock,
  AdminField,
  AdminSkeleton,
  KpiCard,
  KpiGrid,
  Muted,
  RowActions,
  SectionHead,
  StatePanel,
  TwoCol,
} from "./components/AdminPrimitives";
import { cn } from "@/lib/utils";

/**
 * The notice above the form. Its two variants differ only in accent, so they
 * share one box: a `--warning` variant emitted by the component but never
 * declared renders as the ordinary informational banner, which is the
 * class-name drift this project has already shipped once.
 */
const BANNER = "mt-5 flex items-start gap-3 rounded-card border border-line border-l-[3px] p-4";
const BANNER_MARK =
  "flex-none rounded border px-[7px] py-1 font-mono text-[11px] font-extrabold tracking-[0.12em]";

const PROVIDERS: ModelProvider[] = ["local", "ollama", "openai", "deepseek", "anthropic", "custom"];

const FALLBACK_DEFAULTS: Record<
  ModelProvider,
  Pick<AdminModelSettingsView, "base_url" | "chat_model" | "reasoning_model" | "embedding_model">
> = {
  local: { base_url: "", chat_model: "local-evidence", reasoning_model: "local-evidence", embedding_model: "local-hash-384" },
  ollama: { base_url: import.meta.env.VITE_OLLAMA_BASE_URL || "http://localhost:11434", chat_model: "qwen3:14b", reasoning_model: "deepseek-r1:32b", embedding_model: "nomic-embed-text" },
  openai: { base_url: "https://api.openai.com/v1", chat_model: "gpt-5.5", reasoning_model: "gpt-5.5", embedding_model: "text-embedding-3-small" },
  deepseek: { base_url: "https://api.deepseek.com/v1", chat_model: "deepseek-v4-flash", reasoning_model: "deepseek-v4-pro", embedding_model: "" },
  anthropic: { base_url: "https://api.anthropic.com", chat_model: "claude-sonnet-5", reasoning_model: "claude-fable-5", embedding_model: "" },
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

function optionsForRole(metadata: ProviderCatalogEntry | undefined, role: string) {
  return (metadata?.models || [])
    .filter((model) => model.roles.includes(role))
    .map((model) => ({ value: model.id, label: model.recommended ? `${model.label} - Recommended` : model.label }));
}

function selectedModel(metadata: ProviderCatalogEntry | undefined, id: string): ModelCatalogItem | undefined {
  return metadata?.models.find((model) => model.id === id);
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
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [catalog, setCatalog] = useState<ModelCatalogResponse | null>(null);
  const [effective, setEffective] = useState<EffectiveModelComponent[] | null>(null);

  useEffect(() => {
    let active = true;
    // Probing loads the optional models, so this is fetched once on mount rather
    // than on every patch. A failure leaves the panel out: it is a diagnostic,
    // and it must not stop an admin from saving settings.
    void appApi
      .adminEffectiveModelConfig()
      .then((data) => {
        if (active) setEffective(data.components);
      })
      .catch(() => {
        if (active) setEffective(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    void appApi.modelCatalog().then((data) => {
      if (active) setCatalog(data);
    }).catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const provider = (modelSettings?.provider || "local") as ModelProvider;
  const metadata = catalog?.providers?.[provider];
  const providerOptions = useMemo(
    () => PROVIDERS.map((value) => ({ value, label: catalog?.providers?.[value]?.label || value })),
    [catalog],
  );
  const chatOptions = optionsForRole(metadata, "chat");
  const reasoningOptions = optionsForRole(metadata, "reasoning");
  const embeddingOptions = optionsForRole(metadata, "embedding");
  const requiresApiKey = metadata?.requires_api_key ?? !["local", "ollama"].includes(provider);
  const supportsEmbeddings = metadata?.supports_embeddings ?? !["anthropic", "deepseek"].includes(provider);
  const selected = selectedModel(metadata, modelSettings?.chat_model || "");

  const changeProvider = (nextProvider: ModelProvider) => {
    const next = catalog?.providers?.[nextProvider];
    const fallback = FALLBACK_DEFAULTS[nextProvider];
    onPatch({
      provider: nextProvider,
      api_key_masked: "",
      base_url: next?.base_url ?? fallback.base_url,
      chat_model: next?.default_chat_model ?? fallback.chat_model,
      reasoning_model: next?.default_reasoning_model ?? fallback.reasoning_model,
      embedding_model: next?.default_embedding_model ?? fallback.embedding_model,
    });
    onApiKeyChange("");
  };

  const renderModelField = (
    label: string,
    value: string,
    options: Array<{ value: string; label: string }>,
    onChange: (value: string) => void,
  ) => options.length > 0 ? (
    <AdminFormSelect label={label} value={value} onChange={onChange} options={options} required />
  ) : (
    <AdminFormField label={label} value={value} onChange={onChange} placeholder="model-id" required />
  );

  return (
    <main className="space-y-6">
      <SectionHead
        title={t("admin.ui.globalModelConfig", "Global model configuration")}
        description={
          <span className="font-mono">
            {catalog
              ? `Provider catalog ${catalog.version}`
              : t("admin.ui.catalogFallback", "Using verified fallback catalog")}
          </span>
        }
      >
        <RowActions>
          <Button variant="secondary" size="xs" onClick={onRefresh}>{t("common.refresh", "Refresh")}</Button>
          <Button variant="secondary" size="xs" onClick={onTest} disabled={modelTesting || modelSaving}>
            {modelTesting ? t("admin.ui.testing", "Testing") : t("admin.ui.connectionTest", "Connection test")}
          </Button>
          <Button size="xs" onClick={onSave} disabled={modelSaving || modelTesting}>
            {modelSaving ? t("admin.ui.saving", "Saving") : t("admin.ui.saveConfig", "Save config")}
          </Button>
        </RowActions>
      </SectionHead>

      {modelLoading && <AdminSkeleton />}
      {!modelLoading && !modelSettings && <StatePanel tone="error">Model settings are unavailable.</StatePanel>}

      {!modelLoading && modelSettings && (
        <>
          <KpiGrid cols={5}>
            <KpiCard label="Override" value={modelSettings.enabled ? "Enabled" : "Disabled"} />
            <KpiCard label="Provider" value={metadata?.label || provider} />
            <KpiCard label="Chat" value={<span className="text-sm">{modelSettings.chat_model || "-"}</span>} />
            <KpiCard
              label="Embedding"
              value={
                <span className="text-sm">
                  {supportsEmbeddings ? modelSettings.embedding_model || "-" : "Existing pipeline"}
                </span>
              }
            />
          </KpiGrid>

          {effective && effective.length > 0 && (
            <AdminBlock
              className="mt-5"
              title={
                <>
                  {t("admin.ui.effectiveConfig", "Effective configuration")}
                  <span className="ml-2 font-normal normal-case tracking-normal text-ink-muted">
                    {t(
                      "admin.ui.effectiveConfigNote",
                      "What the next question will actually use, not what is stored.",
                    )}
                  </span>
                </>
              }
            >
              <ul className="grid list-none gap-2 p-0">
                {effective.map((item) => (
                  <li key={item.component} className={effectiveRow({ status: item.status })}>
                    <span className="text-xs font-semibold text-ink">{item.component}</span>
                    <span className={effectiveStatusPill({ status: item.status })}>{item.status}</span>
                    <span className="text-xs text-ink-muted [overflow-wrap:anywhere]">{item.configured}</span>
                    <p className="col-span-full m-0 text-[11px] text-ink-muted">{item.detail}</p>
                  </li>
                ))}
              </ul>
            </AdminBlock>
          )}

          {modelSettings.environment_pinned && (
            <div className={cn(BANNER, "border-l-warning bg-warning-surface")} role="status">
              <span className={cn(BANNER_MARK, "border-warning text-warning")}>!</span>
              <div>
                <strong>
                  {t(
                    "admin.ui.modelSettingsPinned",
                    "These settings are saved but not in effect",
                  )}
                </strong>
                <p>
                  {modelSettings.pinned_reason ||
                    t(
                      "admin.ui.modelSettingsPinnedReason",
                      "The process environment pins the model backend; this configuration takes effect once that is unset.",
                    )}
                </p>
              </div>
            </div>
          )}

          <div className={cn(BANNER, "border-l-info bg-info-surface")}>
            <span className={cn(BANNER_MARK, "border-info text-info")}>API</span>
            <div>
              <strong>{metadata?.note || "Provider settings are validated by the backend before activation."}</strong>
              {selected?.deprecated_after && <p>Deprecated after {new Date(selected.deprecated_after).toLocaleString()}</p>}
            </div>
          </div>

          <TwoCol className="mt-6">
            <label className="flex cursor-pointer select-none items-start gap-2 rounded-control border border-transparent px-3 py-2 transition-colors hover:border-brand-border hover:bg-brand-surface">
              <input
                className="mt-0.5 size-4 shrink-0 accent-[var(--brand)]"
                type="checkbox"
                checked={Boolean(modelSettings.enabled)}
                onChange={(event) => onPatch({ enabled: event.target.checked })}
              />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                {t(
                  "admin.ui.enableGlobalModelOverride",
                  "Enable global model override (replaces every user's own API settings)",
                )}
              </span>
            </label>
            <AdminFormSelect label={t("admin.ui.backendType", "Backend type")} value={provider} onChange={(value) => changeProvider(value as ModelProvider)} options={providerOptions} />
          </TwoCol>

          {provider !== "local" && (
            <TwoCol>
              <AdminFormField label="Base URL" value={modelSettings.base_url} onChange={(value) => onPatch({ base_url: value })} placeholder="https://api.example.com/v1" required />
              <AdminFormField label="API Key" type="password" value={modelApiKey} onChange={onApiKeyChange} placeholder={modelSettings.api_key_masked ? `Saved: ${modelSettings.api_key_masked}` : "Stored securely after save"} required={requiresApiKey} />
            </TwoCol>
          )}

          <TwoCol>
            {renderModelField(t("admin.ui.chatModel", "Chat model"), modelSettings.chat_model, chatOptions, (value) => onPatch({ chat_model: value }))}
            {renderModelField(t("admin.ui.reasoningModel", "Reasoning model"), modelSettings.reasoning_model, reasoningOptions, (value) => onPatch({ reasoning_model: value }))}
          </TwoCol>

          <TwoCol>
            {supportsEmbeddings ? renderModelField(t("admin.ui.embeddingModel", "Embedding model"), modelSettings.embedding_model, embeddingOptions, (value) => onPatch({ embedding_model: value })) : (
              <StatePanel>
                <strong className="text-xs font-bold text-ink">Embedding pipeline unchanged</strong>
                <Muted>This provider has no embedding endpoint. Existing vectors and the configured environment embedding model remain active.</Muted>
              </StatePanel>
            )}
            <AdminFormField label="Max Tokens" type="number" value={String(modelSettings.max_tokens)} onChange={(value) => onPatch({ max_tokens: Number(value) || 2048 })} />
          </TwoCol>

          <AdminField
            className="gap-2.5"
            label={`Temperature ${Number(modelSettings.temperature || 0).toFixed(1)}`}
          >
            <input
              className="w-full accent-[var(--brand)]"
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={modelSettings.temperature}
              onChange={(event) =>
                onPatch({
                  temperature: normalizeModelTemperature(Number(event.target.value), modelSettings.temperature),
                })
              }
            />
          </AdminField>

          {modelTestResult && (
            <StatePanel tone={modelTestResult.type === "error" ? "error" : "success"}>
              {modelTestResult.message}
            </StatePanel>
          )}
        </>
      )}
    </main>
  );
}
