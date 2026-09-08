import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Brain, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useConfirmDialog } from "@/hooks/useConfirmDialog";
import { cn } from "@/lib/utils";
import { forgetAllMemories, forgetMemory, listMemories, type MemoryKind, type StoredMemory } from "./api";

/**
 * What the system remembers about you, and the two ways to undo it.
 *
 * This is the reader-facing half of a gap: `_promote_long_term_memory` runs on
 * every answered query and `build_memory_context` feeds the result into the
 * next one, so memories accumulate and shape later answers -- and until this
 * panel there was no screen anywhere that named them.
 *
 * Lives in the settings drawer beside Integrations rather than being its own
 * destination, for the reason the top bar's Integrations button was dropped: a
 * second name for a place the app already has costs more than it gives.
 */

/** Colour says what kind of thing it is; nothing here is a status. */
const KIND_TONE: Record<string, "brand" | "info" | "warning" | "neutral"> = {
  explicit_remember: "brand",
  preference: "info",
  task: "warning",
  stable_fact: "neutral",
};

export function MemoryPanel() {
  const { t, i18n } = useTranslation();
  const [memories, setMemories] = useState<readonly StoredMemory[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  // Tone travels with the text. Keeping a separate `failed` flag meant a delete
  // that errored after a clean load rendered its message in success green.
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  // The load failure is its own state, holding the server's message or "" when
  // there was none, because the effect below must not close over `t`.
  const [loadError, setLoadError] = useState<string | null>(null);
  const confirmDialog = useConfirmDialog();

  // Loads once. `t` is deliberately not a dependency and not used inside:
  // react-i18next hands back a new `t` whenever the language changes, so a
  // fetch keyed on it re-runs for a reason that has nothing to do with the
  // data -- and under any `useTranslation` that does not memoize, that is an
  // unbounded render loop rather than an extra request. The fallback wording
  // is resolved at render time instead, where it belongs.
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const items = await listMemories(controller.signal);
        if (!controller.signal.aborted) setMemories(items);
      } catch (error) {
        if (controller.signal.aborted) return;
        setLoadError(error instanceof Error ? error.message : "");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  // The kind is rendered through a switch of literal keys rather than an
  // interpolated one, so `i18n/locales.test.ts` -- which scans for literal
  // `t("...")` calls -- can see all five and fail when a locale is missing one.
  const kindLabel = (kind: MemoryKind): string => {
    switch (kind) {
      case "preference":
        return t("features.memory.kind.preference");
      case "stable_fact":
        return t("features.memory.kind.stableFact");
      case "task":
        return t("features.memory.kind.task");
      case "explicit_remember":
        return t("features.memory.kind.explicitRemember");
      default:
        return t("features.memory.kind.other");
    }
  };

  const formatDate = (value: string | null): string => {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? ""
      : date.toLocaleDateString(i18n.language, { year: "numeric", month: "short", day: "numeric" });
  };

  const shownNotice =
    loadError === null ? notice : { tone: "error" as const, text: loadError || t("features.memory.loadError") };

  const forgetOne = async (memory: StoredMemory) => {
    setBusyId(memory.memory_id);
    setNotice(null);
    try {
      await forgetMemory(memory.memory_id);
      setMemories((items) => items.filter((item) => item.memory_id !== memory.memory_id));
      setNotice({ tone: "success", text: t("features.memory.forgotten") });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : t("features.memory.forgetError") });
    } finally {
      setBusyId(null);
    }
  };

  const forgetEverything = async () => {
    // Irreversible and about the caller's own stored data, so it asks first.
    // A single row does not: it is one item, named, under its own button.
    const confirmed = await confirmDialog.confirm({
      title: t("features.memory.forgetAllTitle"),
      message: t("features.memory.forgetAllPrompt", { count: memories.length }),
      confirmText: t("features.memory.forgetAllConfirm"),
      isDanger: true,
    });
    if (!confirmed) return;

    setBusyId("all");
    setNotice(null);
    try {
      const result = await forgetAllMemories();
      setMemories([]);
      setNotice({ tone: "success", text: t("features.memory.forgotAll", { count: result.forgotten }) });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : t("features.memory.forgetError") });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section aria-label={t("features.memory.ariaLabel")}>
      {/* Opaque, not `bg-surface-muted/60`. An alpha tint has no fixed
          contrast: what shows through is whatever is behind it, here a
          `glass-panel` over the aurora gradient -- so the audit could not
          resolve a background for the description text and skipped it
          entirely. Same reason `--success-surface` exists as an opaque token
          rather than a `color-mix` of `--success`. */}
      <details className="group rounded-card border border-line-subtle bg-surface-muted">
        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-card px-3 py-2 text-xs font-bold text-ink hover:bg-brand-surface">
          <Brain className="size-3.5 text-brand-accent" aria-hidden="true" />
          <span className="flex-1">{t("features.memory.title")}</span>
          {!loading && loadError === null && (
            <Badge variant={memories.length ? "brand" : "neutral"} size="sm" mono>
              {memories.length}
            </Badge>
          )}
        </summary>

        <div className="space-y-2.5 border-t border-line-subtle p-3">
          <p className="text-[11px] leading-relaxed text-ink-muted">{t("features.memory.description")}</p>

          {loading && (
            <p aria-live="polite" className="py-3 text-center text-[11px] text-ink-muted">
              {t("features.memory.loading")}
            </p>
          )}

          {!loading && loadError === null && memories.length === 0 && (
            <p className="rounded-control border border-dashed border-line px-3 py-4 text-center text-[11px] text-ink-muted">
              {t("features.memory.empty")}
            </p>
          )}

          {memories.length > 0 && (
            <ul className="list-none space-y-1.5">
              {memories.map((memory) => (
                <li
                  key={memory.memory_id}
                  // An expired row is de-emphasised by its GROUND, never by
                  // opacity. `opacity` composites the whole subtree, and it is
                  // not in `getComputedStyle().color`, so a contrast audit
                  // walks straight past it: measured, `--text-muted` at
                  // `opacity-70` drops from 5.56 to 2.97 and fails AA, which
                  // would have cost the kind label, the expiry badge and the
                  // date on every expired row. A tinted background moves
                  // nothing -- 5.28 on `--surface-muted`. The badge below is
                  // the signal that actually reaches a screen reader.
                  className={cn(
                    "flex items-start gap-2 rounded-control border border-line-subtle p-2.5",
                    memory.active ? "bg-surface" : "bg-surface-muted"
                  )}
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="break-words text-[11px] leading-relaxed text-ink">{memory.content}</p>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant={KIND_TONE[memory.kind] ?? "neutral"} size="xs">
                        {kindLabel(memory.kind)}
                      </Badge>
                      {/* Stored but no longer reaching the model. Saying so is
                          the point: it is still here, and still deletable. */}
                      {!memory.active && (
                        <Badge variant="neutral" size="xs">
                          {t("features.memory.expired")}
                        </Badge>
                      )}
                      {memory.created_at && (
                        <span className="font-mono text-[9px] text-ink-muted">{formatDate(memory.created_at)}</span>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="destructive-ghost"
                    size="icon-sm"
                    onClick={() => void forgetOne(memory)}
                    disabled={busyId !== null}
                    aria-label={t("features.memory.forgetOne", { content: memory.content })}
                  >
                    <Trash2 aria-hidden="true" />
                  </Button>
                </li>
              ))}
            </ul>
          )}

          {memories.length > 0 && (
            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="xs"
                onClick={() => void forgetEverything()}
                disabled={busyId !== null}
              >
                {busyId === "all" ? t("features.memory.forgettingAll") : t("features.memory.forgetAll")}
              </Button>
            </div>
          )}

          {shownNotice && (
            <p
              role="status"
              aria-live="polite"
              className={cn(
                "rounded-control border px-2.5 py-1.5 text-[11px]",
                shownNotice.tone === "error"
                  ? "border-danger-border bg-danger-surface text-danger"
                  : "border-success-border bg-success-surface text-success"
              )}
            >
              {shownNotice.text}
            </p>
          )}
        </div>
      </details>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.options?.title ?? ""}
        message={confirmDialog.options?.message ?? ""}
        confirmText={confirmDialog.options?.confirmText}
        isDanger={confirmDialog.options?.isDanger}
        onConfirm={confirmDialog.handleConfirm}
        onCancel={confirmDialog.handleCancel}
      />
    </section>
  );
}
