import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useDismissable } from "@/hooks/useDismissable";
import { SHORTCUTS, type ShortcutSpec } from "@/components/keyboardShortcuts";

/**
 * The shortcut sheet.
 *
 * Controlled, and mounted by `AppShell` -- it used to hold its own `isOpen`
 * and its own key listener, which meant `?` worked on the chat page and
 * nowhere else, and nothing but a keystroke could ever open it. The listener
 * lives in `useAppShortcuts` now, beside the handlers for the shortcuts this
 * sheet describes, so the documentation and the behaviour are edited together.
 *
 * **Every row below is implemented.** The list used to carry `Ctrl+K`,
 * `Ctrl+N`, `Ctrl+B`, `Ctrl+W` and `Ctrl+R` against an app whose only handler
 * was the one that opened this sheet. Three are real now; the two the browser
 * owns are gone rather than faked, and their toggles live in the composer and
 * the command palette.
 */
type Row = ShortcutSpec & { description: string; category: string };

export function KeyboardHelp({ open, onClose }: Readonly<{ open: boolean; onClose: () => void }>) {
  const { t } = useTranslation();
  useDismissable(open, onClose);
  const shortcuts = useMemo<Row[]>(
    () => SHORTCUTS.map((spec) => ({ ...spec, description: t(spec.descriptionKey), category: t(spec.categoryKey) })),
    [t]
  );

  const groupedShortcuts = useMemo(() => {
    return shortcuts.reduce(
      (acc, shortcut) => {
        if (!acc[shortcut.category]) acc[shortcut.category] = [];
        acc[shortcut.category].push(shortcut);
        return acc;
      },
      {} as Record<string, Row[]>
    );
  }, [shortcuts]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="glass-panel fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col rounded-panel border-brand-border-strong shadow-elev-3 animate-in fade-in-0 zoom-in-95"
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-help-title"
      >
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-line-subtle p-4">
          <h2 id="keyboard-help-title" className="text-sm font-bold text-ink">
            {t("components.keyboard.title")}
          </h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label={t("components.keyboard.close")}
          >
            <X aria-hidden="true" />
          </Button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {Object.entries(groupedShortcuts).map(([category, items]) => (
            <section key={category} className="space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">{category}</h3>
              <dl className="space-y-1">
                {items.map((shortcut) => (
                  <div
                    key={`${category}-${shortcut.keys.join("-")}-${shortcut.description}`}
                    className="flex items-center justify-between gap-3 rounded-control border border-line bg-surface px-2.5 py-1.5"
                  >
                    <dt className="flex shrink-0 items-center gap-1">
                      {shortcut.keys.map((key: string, index: number) => (
                        <span key={key} className="flex items-center gap-1">
                          <kbd className="rounded border border-line-strong bg-surface-muted px-2 py-0.5 font-mono text-xs font-semibold text-ink">
                            {key}
                          </kbd>
                          {index < shortcut.keys.length - 1 && (
                            <span className="text-xs text-ink/60" aria-hidden="true">
                              +
                            </span>
                          )}
                        </span>
                      ))}
                    </dt>
                    <dd className="min-w-0 flex-1 text-right text-xs sm:text-sm font-medium text-ink/80">{shortcut.description}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>

        <div className="shrink-0 border-t border-line-subtle p-3">
          <p className="text-center text-xs text-ink/75">{t("components.keyboard.footer")}</p>
        </div>
      </div>
    </>
  );
}
