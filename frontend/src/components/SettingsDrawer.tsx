import { useEffect, useState } from "react";
import { Info, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { IntegrationsPanel } from "@/features/integrations/IntegrationsPanel";
import { MemoryPanel } from "@/features/memory/MemoryPanel";
import { Button } from "@/components/ui/button";
import { appApi } from "@/lib/api";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

type ActiveModel = {
  managedByAdmin: boolean;
  provider: string;
  model: string;
};

/**
 * The settings drawer: integrations, long-term memory, and a read-only line
 * saying which model is answering.
 *
 * It used to be `ApiSettings`, a per-user model configuration form -- provider,
 * key, model, temperature, a Save and a Test. That was removed on 2026-09-08.
 * Models are configured by an administrator and that configuration applies to
 * every user, so a form here could only ever collect a third-party credential
 * and a preference that nothing would read; the Test button returned a green
 * success because it probed the posted values directly, which made the promise
 * look kept.
 */
export function SettingsDrawer({ isOpen, onClose }: Readonly<Props>) {
  const { t } = useTranslation();
  const [activeModel, setActiveModel] = useState<ActiveModel | null>(null);
  const [modelUnavailable, setModelUnavailable] = useState(false);

  // Deliberately not keyed on `t`: react-i18next hands back a new `t` on every
  // language change, and a fetch that re-runs for that reason is at best a
  // wasted request and at worst an unbounded render loop.
  useEffect(() => {
    if (!isOpen) return undefined;
    let cancelled = false;
    setModelUnavailable(false);
    void (async () => {
      try {
        const res = await appApi.getActiveModel();
        if (cancelled) return;
        if (res.ok) {
          setActiveModel({
            managedByAdmin: !!res.managed_by_admin,
            provider: res.provider || "",
            model: res.model || "",
          });
        } else {
          setModelUnavailable(true);
        }
      } catch {
        // A read-only courtesy must not take the drawer down: integrations and
        // memory are what it opens for.
        if (!cancelled) setModelUnavailable(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Scenery. A button rather than a div so the drawer is dismissible by
          pointer without a keyboard trap; Escape and the header's close button
          are the keyboard routes. */}
      <button
        type="button"
        className="fixed inset-0 z-40 bg-stone-900/40 backdrop-blur-sm"
        onClick={onClose}
        aria-label={t("components.settings.close")}
      />
      <aside
        className="glass-panel fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-y-0 border-r-0 shadow-elev-3 animate-in slide-in-from-right duration-300"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-drawer-title"
      >
        <header className="flex shrink-0 items-start justify-between gap-2 border-b border-line-subtle p-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="flex size-9 shrink-0 items-center justify-center rounded-card bg-[image:var(--brand-gradient)] font-mono text-xs font-bold text-white shadow-elev-1"
              aria-hidden="true"
            >
              SET
            </span>
            <div className="min-w-0">
              <h2 id="settings-drawer-title" className="text-base font-bold text-ink">
                {t("components.settings.title")}
              </h2>
              <p className="truncate text-xs sm:text-sm text-ink/75">{t("components.settings.subtitle")}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label={t("components.settings.close")}>
            <X aria-hidden="true" />
          </Button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <section aria-labelledby="settings-model-heading" className="space-y-2">
            <h3
              id="settings-model-heading"
              className="text-xs font-bold uppercase tracking-wider text-ink/80"
            >
              {t("components.settings.modelHeading")}
            </h3>
            <div className="flex gap-2.5 rounded-card border border-line-subtle bg-surface-muted p-3">
              <Info className="mt-0.5 size-4 shrink-0 text-brand-accent" aria-hidden="true" />
              <div className="min-w-0 space-y-1 text-xs sm:text-sm">
                {activeModel?.managedByAdmin ? (
                  <>
                    <strong className="block break-words font-mono text-ink">
                      {activeModel.provider} / {activeModel.model}
                    </strong>
                    <p className="font-medium text-ink/80">{t("components.settings.managedByAdmin")}</p>
                  </>
                ) : (
                  <p className="font-medium text-ink/80">
                    {modelUnavailable
                      ? t("components.settings.modelUnavailable")
                      : t("components.settings.deploymentDefault")}
                  </p>
                )}
              </div>
            </div>
          </section>

          <IntegrationsPanel />

          <MemoryPanel />
        </div>
      </aside>
    </>
  );
}
