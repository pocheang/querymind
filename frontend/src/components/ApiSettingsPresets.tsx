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

export function ApiSettingsPresets({ presets, activeProvider, activeModel, onApplyPreset }: Props) {
  return (
    <section className="settings-section">
      <label className="section-label">Quick Presets</label>
      <div className="preset-grid">
        {presets.map((preset) => (
          <button
            key={preset.name}
            type="button"
            className={`preset-card ${activeProvider === preset.provider && activeModel === preset.model ? "active" : ""}`}
            onClick={() => onApplyPreset(preset)}
          >
            <span className="preset-icon">{preset.mark}</span>
            <span className="preset-name">{preset.name}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
