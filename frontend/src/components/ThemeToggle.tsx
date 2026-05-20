import { getThemeIcon, getThemeDisplay } from "@/lib/theme";

interface ThemeToggleProps {
  themeLabel: string;
  onThemeToggle: () => void;
  className?: string;
}

export function ThemeToggle({ themeLabel, onThemeToggle, className = "theme-toggle" }: ThemeToggleProps) {
  const themeIcon = getThemeIcon(themeLabel);
  const themeDisplay = getThemeDisplay(themeLabel);

  return (
    <button type="button" className={className} onClick={onThemeToggle}>
      {themeIcon} {themeDisplay}
    </button>
  );
}
