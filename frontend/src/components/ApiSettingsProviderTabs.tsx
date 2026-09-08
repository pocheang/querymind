import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

type Provider = "local" | "openai" | "anthropic" | "deepseek" | "ollama" | "custom";

type Props = {
  providers: Provider[];
  activeProvider: Provider;
  onChangeProvider: (provider: Provider) => void;
};

/**
 * The provider picker: a segmented control, the design's most repeated
 * interactive shape -- a recessed rail whose selected item raises to white.
 *
 * A real `tablist` rather than a row of buttons, because exactly one provider
 * is in effect at a time and `aria-selected` is what says which.
 */
export function ApiSettingsProviderTabs({ providers, activeProvider, onChangeProvider }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <section className="space-y-1.5">
      <Label id="provider-label">{t("components.apiSettings.provider")}</Label>
      <div
        role="tablist"
        aria-labelledby="provider-label"
        className="flex flex-wrap items-center gap-0.5 rounded-control border border-line bg-surface-muted p-1"
      >
        {providers.map((provider) => {
          const active = activeProvider === provider;
          return (
            <button
              key={provider}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChangeProvider(provider)}
              className={cn(
                "rounded-control px-2.5 py-1 text-[11px] font-medium capitalize transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                active
                  ? "bg-surface font-bold text-brand-text-strong shadow-elev-1"
                  : "text-ink-muted hover:text-brand-text"
              )}
            >
              {provider}
            </button>
          );
        })}
      </div>
    </section>
  );
}
