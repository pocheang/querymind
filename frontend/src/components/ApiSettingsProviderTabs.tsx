import { useTranslation } from "react-i18next";

type Provider = "local" | "openai" | "anthropic" | "deepseek" | "ollama" | "custom";

type Props = {
  providers: Provider[];
  activeProvider: Provider;
  onChangeProvider: (provider: Provider) => void;
};

export function ApiSettingsProviderTabs({ providers, activeProvider, onChangeProvider }: Props) {
  const { t } = useTranslation();

  return (
    <section className="settings-section">
      <label className="section-label">{t("components.apiSettings.provider")}</label>
      <div className="provider-tabs">
        {providers.map((provider) => (
          <button
            key={provider}
            type="button"
            className={`provider-tab ${activeProvider === provider ? "active" : ""}`}
            onClick={() => onChangeProvider(provider)}
          >
            {provider}
          </button>
        ))}
      </div>
    </section>
  );
}
