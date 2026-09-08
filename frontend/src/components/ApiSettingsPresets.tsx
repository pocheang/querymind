import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

type Provider = "local" | "openai" | "anthropic" | "deepseek" | "ollama" | "custom";

type Preset = {
  name: string;
  provider: Provider;
  model: string;
  mark: string;
};

type Props = {
  presets: Preset[];
  activeProvider: Provider;
  activeModel: string;
  onApplyPreset: (preset: Preset) => void;
};

export function ApiSettingsPresets({ presets, activeProvider, activeModel, onApplyPreset }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <section className="space-y-1.5">
      <Label>{t("components.apiSettings.quickPresets")}</Label>
      <div className="grid grid-cols-2 gap-1.5">
        {presets.map((preset) => {
          const active = activeProvider === preset.provider && activeModel === preset.model;
          return (
            <button
              key={preset.name}
              type="button"
              /* Not the Button primitive: a preset is a two-line selectable
                 tile, and `aria-pressed` is what carries the selection --
                 the border and tint alone would leave it unannounced. */
              aria-pressed={active}
              onClick={() => onApplyPreset(preset)}
              className={cn(
                "flex items-center gap-2 rounded-control border p-2 text-left text-[11px] transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                active
                  ? "border-brand-border-strong bg-brand-surface font-semibold text-brand-text-strong shadow-elev-1"
                  : "border-line bg-surface text-ink hover:border-brand-border hover:bg-brand-surface/60"
              )}
            >
              <span className="shrink-0 text-sm" aria-hidden="true">
                {preset.mark}
              </span>
              <span className="min-w-0 truncate">{preset.name}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
