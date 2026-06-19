export type Provider = "local" | "openai" | "anthropic" | "deepseek" | "ollama" | "custom";

export type ApiConfig = {
  provider: Provider;
  apiKey: string;
  apiKeyMasked: string;
  baseUrl: string;
  model: string;
  temperature: number;
  maxTokens: number;
};

export const PROVIDER_MODELS: Record<Provider, string[]> = {
  local: ["local-evidence"],
  openai: ["gpt-5.4-codex", "gpt-5.2", "gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-sonnet-4-6", "claude-opus-4-8", "claude-opus-4-7", "claude-3-5-sonnet-20241022"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
  ollama: ["qwen2.5:7b", "qwen2.5:7b-instruct", "llama3.2", "mistral", "phi3"],
  custom: [],
};

export const PROVIDER_DEFAULTS: Record<Provider, Pick<ApiConfig, "baseUrl" | "model">> = {
  local: { baseUrl: "", model: "local-evidence" },
  openai: { baseUrl: "https://api.openai.com/v1", model: "gpt-5.4-codex" },
  anthropic: { baseUrl: "https://api.anthropic.com", model: "claude-sonnet-4-6" },
  deepseek: { baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  ollama: { baseUrl: "http://localhost:11434", model: "qwen2.5:7b-instruct" },
  custom: { baseUrl: "", model: "" },
};

export const QUICK_PRESETS = [
  { name: "Local Evidence", provider: "local" as Provider, model: "local-evidence", mark: "LC" },
  { name: "Ollama Local", provider: "ollama" as Provider, model: "qwen2.5:7b-instruct", mark: "OL" },
  { name: "OpenAI GPT", provider: "openai" as Provider, model: "gpt-5.4-codex", mark: "OA" },
  { name: "DeepSeek", provider: "deepseek" as Provider, model: "deepseek-chat", mark: "DS" },
  { name: "Claude", provider: "anthropic" as Provider, model: "claude-sonnet-4-6", mark: "CL" },
];

export const PROVIDERS: Provider[] = ["local", "ollama", "openai", "deepseek", "anthropic", "custom"];

export const DEFAULT_CONFIG: ApiConfig = {
  provider: "local",
  apiKey: "",
  apiKeyMasked: "",
  baseUrl: "",
  model: "local-evidence",
  temperature: 0.7,
  maxTokens: 2048,
};
