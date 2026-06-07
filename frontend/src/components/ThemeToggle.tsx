import { getThemeIcon } from "@/lib/theme";

interface ThemeToggleProps {
  themeLabel: string;
  onThemeToggle: () => void;
  className?: string;
}

export function ThemeToggle({ themeLabel, onThemeToggle, className = "theme-toggle" }: ThemeToggleProps) {
  const themeIcon = getThemeIcon(themeLabel);

  return (
    <button
      type="button"
      className={className}
      onClick={onThemeToggle}
    >
      {themeIcon} {themeLabel}
    </button>
  );
}
