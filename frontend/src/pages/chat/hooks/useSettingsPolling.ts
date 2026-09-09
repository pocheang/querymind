import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { appApi } from "@/lib/api";

interface UseSettingsPollingOptions {
  onNotify: (message: string, type: "success" | "error" | "info", duration?: number) => void;
}

/**
 * Tell a reader when an administrator changes the model answering their
 * questions.
 *
 * Worth a notice precisely because they cannot change it back: model
 * configuration is an administrator's and applies to everyone.
 */
export function useSettingsPolling({ onNotify }: UseSettingsPollingOptions) {
  const { t } = useTranslation();
  const lastModelRef = useRef<{ managedByAdmin: boolean; provider: string; model: string } | null>(null);
  // Held in refs so the effect below can depend on NOTHING. Keyed on
  // `[onNotify, t]` it re-ran on most renders -- react-i18next hands back a
  // fresh `t` and the notifier is a new closure each time -- and each re-run
  // repeated the seeding fetch. Measured on an idle page: 3 requests per 30s
  // against the one the 25s interval intends, and far worse while an answer
  // streams, because that re-renders continuously.
  const onNotifyRef = useRef(onNotify);
  const tRef = useRef(t);
  onNotifyRef.current = onNotify;
  tRef.current = t;

  useEffect(() => {
    const read = async () => {
      const res = await appApi.getActiveModel();
      if (!res.ok) return null;
      return {
        managedByAdmin: !!res.managed_by_admin,
        provider: res.provider || "",
        model: res.model || "",
      };
    };

    // Initial fetch
    void (async () => {
      try {
        lastModelRef.current = await read();
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
          const next = await read();
          if (!next) return;
          const prev = lastModelRef.current;
          if (
            prev !== null &&
            (prev.managedByAdmin !== next.managedByAdmin ||
              prev.provider !== next.provider ||
              prev.model !== next.model)
          ) {
            onNotifyRef.current(
              next.managedByAdmin
                ? tRef.current("components.settings.modelChanged", { provider: next.provider, model: next.model })
                : tRef.current("components.settings.modelChangedToDefault"),
              "info",
              4000
            );
          }
          lastModelRef.current = next;
        } catch {
          // A missed poll costs one notice about an administrator changing the
          // model; the next poll reports the difference just the same.
        }
      })();
    }, 25000);

    return () => window.clearInterval(timer);
  }, []);
}
