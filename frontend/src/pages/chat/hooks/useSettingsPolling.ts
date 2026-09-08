import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { appApi } from "@/lib/api";

interface UseSettingsPollingOptions {
  onNotify: (message: string, type: "success" | "error" | "info", duration?: number) => void;
}

export function useSettingsPolling({ onNotify }: UseSettingsPollingOptions) {
  const { t } = useTranslation();
  const lastOverrideStateRef = useRef<{
    enabled: boolean;
    provider: string;
    model: string;
  } | null>(null);

  useEffect(() => {
    // Initial fetch
    void (async () => {
      try {
        const res = await appApi.getUserApiSettings();
        if (res.ok && res.settings) {
          lastOverrideStateRef.current = {
            enabled: !!res.settings.global_override_enabled,
            provider: res.settings.global_provider || "",
            model: res.settings.global_model || "",
          };
        }
      } catch {
        // The first read only seeds the comparison baseline; failing it means
        // the next poll reports no change, which is the right answer when we
        // never learned what the previous state was.
      }
    })();

    // Polling
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const res = await appApi.getUserApiSettings();
          if (res.ok && res.settings) {
            const enabled = !!res.settings.global_override_enabled;
            const provider = res.settings.global_provider || "";
            const model = res.settings.global_model || "";

            if (lastOverrideStateRef.current !== null) {
              const prev = lastOverrideStateRef.current;
              if (prev.enabled !== enabled || prev.provider !== provider || prev.model !== model) {
                if (enabled) {
                  const desc = t("components.apiSettings.globalOverrideDesc", { provider, model });
                  onNotify(`${t("components.apiSettings.globalOverrideNotice")}: ${desc}`, "info", 4000);
                } else if (prev.enabled) {
                  onNotify(t("components.apiSettings.globalOverrideDisabledNotice"), "info", 4000);
                }
              }
            }
            lastOverrideStateRef.current = { enabled, provider, model };
          }
        } catch {
          // A missed poll costs one notice about an admin changing the global
          // model override. Surfacing it every 25s would be worse than the
          // thing it reports.
        }
      })();
    }, 25000);

    return () => window.clearInterval(timer);
  }, [onNotify, t]);
}
