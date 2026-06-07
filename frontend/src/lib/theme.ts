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

export function getThemeIcon(themeLabel: string): string {
  // 支持中英文判断：包含"暗"或"Dark"返回月亮，否则返回太阳
  return themeLabel.includes("暗") || themeLabel.toLowerCase().includes("dark") ? "🌙" : "☀️";
}

