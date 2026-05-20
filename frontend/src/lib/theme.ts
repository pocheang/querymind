const THEME_KEY = "theme_preference";
export type ThemeMode = "light" | "dark";

export function getSavedTheme(): ThemeMode {
  const raw = localStorage.getItem(THEME_KEY);
  if (raw === "light" || raw === "dark") return raw;
  return "light";
}

export function saveTheme(mode: ThemeMode) {
  localStorage.setItem(THEME_KEY, mode);
}

export function applyTheme(mode: ThemeMode) {
  document.documentElement.setAttribute("data-theme", mode);
}

export function nextTheme(mode: ThemeMode): ThemeMode {
  return mode === "dark" ? "light" : "dark";
}

export const THEME_LABELS = {
  SWITCH_TO_LIGHT: '切换到亮色',
  SWITCH_TO_DARK: '切换到暗色',
} as const;

export function getThemeIcon(themeLabel: string): string {
  return themeLabel.includes("暗") ? "🌙" : "☀️";
}

export function getThemeDisplay(themeLabel: string): string {
  return themeLabel.includes("暗") ? "暗色" : "亮色";
}
