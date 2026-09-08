import { useTranslation } from "react-i18next";

interface ThinkingIndicatorProps {
  elapsedSeconds?: number;
}

/**
 * The live affordance while the pipeline runs and no text has arrived yet.
 *
 * The label used to be a hardcoded Chinese string in an app whose whole point
 * is that it works in both languages; it goes through `t()` now. The elapsed
 * count was also accepted and thrown away -- it is rendered.
 */
export function ThinkingIndicator({ elapsedSeconds = 0 }: Readonly<ThinkingIndicatorProps>) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2 text-[11px] text-ink-muted" role="status">
      <span className="flex items-center gap-1" aria-hidden="true">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="size-1.5 animate-pulse rounded-pill bg-brand-accent"
            style={{ animationDelay: `${dot * 150}ms` }}
          />
        ))}
      </span>
      <span className="font-medium">{t("components.messages.processing", "Thinking")}</span>
      {elapsedSeconds > 0 && <span className="font-mono text-ink-faint">{elapsedSeconds}s</span>}
    </div>
  );
}
