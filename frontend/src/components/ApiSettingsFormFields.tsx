import { useTranslation } from "react-i18next";

import { normalizeModelTemperature } from "@/lib/model-temperature";
import type { ApiConfig } from "./apiSettingsConstants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = {
  config: ApiConfig;
  selectedModels: string[];
  requiresApiKey: boolean;
  requiresBaseUrl: boolean;
  showApiKey: boolean;
  onShowApiKeyToggle: () => void;
  onConfigChange: (patch: Partial<ApiConfig>) => void;
};

const SLIDER =
  "w-full cursor-pointer accent-[var(--brand)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]";

/** Label plus the live value, the design's slider header. */
function ValueLabel({ htmlFor, children, value }: Readonly<{ htmlFor: string; children: string; value: string }>) {
  return (
    <Label htmlFor={htmlFor} className="flex items-center justify-between gap-2">
      <span>{children}</span>
      <span className="font-mono normal-case tracking-normal text-brand-text">{value}</span>
    </Label>
  );
}

function SliderScale({ marks }: Readonly<{ marks: string[] }>) {
  return (
    <div className="flex items-center justify-between font-mono text-[10px] text-ink-faint">
      {marks.map((mark) => (
        <span key={mark}>{mark}</span>
      ))}
    </div>
  );
}

export function ApiSettingsFormFields({
  config,
  selectedModels,
  requiresApiKey,
  requiresBaseUrl,
  showApiKey,
  onShowApiKeyToggle,
  onConfigChange,
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <>
      <p className="rounded-control border border-brand-border bg-brand-surface/60 px-2.5 py-2 text-[11px] leading-relaxed text-ink-muted">
        {t("components.apiSettings.note")}
      </p>

      {requiresApiKey && (
        <section className="space-y-1.5">
          <Label htmlFor="api-key-input">{t("components.apiSettings.apiKey")}</Label>
          <div className="flex items-center gap-1.5">
            <Input
              id="api-key-input"
              type={showApiKey ? "text" : "password"}
              className="font-mono"
              placeholder={
                config.apiKeyMasked ? t("components.apiSettings.saved", { value: config.apiKeyMasked }) : "sk-..."
              }
              value={config.apiKey}
              onChange={(e) => onConfigChange({ apiKey: e.target.value, apiKeyMasked: "" })}
            />
            <Button variant="secondary" size="sm" onClick={onShowApiKeyToggle}>
              {showApiKey ? t("components.apiSettings.hide") : t("components.apiSettings.show")}
            </Button>
          </div>
        </section>
      )}

      {requiresBaseUrl && (
        <section className="space-y-1.5">
          <Label htmlFor="base-url-input">{t("components.apiSettings.baseUrl")}</Label>
          <Input
            id="base-url-input"
            type="text"
            className="font-mono"
            placeholder="https://api.example.com/v1"
            value={config.baseUrl}
            onChange={(e) => onConfigChange({ baseUrl: e.target.value })}
          />
        </section>
      )}

      <section className="space-y-1.5">
        <Label htmlFor="model-input">{t("components.apiSettings.model")}</Label>
        {selectedModels.length > 0 ? (
          <select
            id="model-input"
            value={config.model}
            onChange={(e) => onConfigChange({ model: e.target.value })}
            className="h-8 w-full rounded-control border border-brand-border bg-surface px-2 font-mono text-xs text-ink transition-colors focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
          >
            {selectedModels.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        ) : (
          <Input
            id="model-input"
            type="text"
            className="font-mono"
            placeholder="model-name"
            value={config.model}
            onChange={(e) => onConfigChange({ model: e.target.value })}
          />
        )}
      </section>

      <section className="space-y-1.5">
        <ValueLabel htmlFor="temperature-input" value={Number(config.temperature).toFixed(1)}>
          {t("components.apiSettings.temperature")}
        </ValueLabel>
        <input
          id="temperature-input"
          type="range"
          className={SLIDER}
          min="0"
          max="1"
          step="0.1"
          value={config.temperature}
          onChange={(e) =>
            onConfigChange({
              temperature: normalizeModelTemperature(Number(e.target.value), config.temperature),
            })
          }
        />
        <SliderScale
          marks={[
            t("components.apiSettings.stable"),
            t("components.apiSettings.balanced"),
            t("components.apiSettings.creative"),
          ]}
        />
      </section>

      <section className="space-y-1.5">
        <ValueLabel htmlFor="max-tokens-input" value={String(config.maxTokens)}>
          {t("components.apiSettings.maxTokens")}
        </ValueLabel>
        <input
          id="max-tokens-input"
          type="range"
          className={SLIDER}
          min="256"
          max="131072"
          step="1024"
          value={config.maxTokens}
          onChange={(e) => onConfigChange({ maxTokens: Number(e.target.value) })}
        />
        <SliderScale marks={["256", "65536", "131072"]} />
      </section>
    </>
  );
}
