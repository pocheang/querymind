import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { adminConfigApi } from "@/services/api/admin";
import type { ConfigField } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Muted, RowActions, SectionHead } from "./components/AdminPrimitives";
import { ADMIN_TABLE } from "./components/adminClasses";

/**
 * The configuration page, generated from the server's schema.
 *
 * Not a hand-written form: `Settings` has 236 fields and the editable subset is
 * an allowlist that will move, so a form written field by field would drift out
 * of agreement with the server the first time that list changed. The server
 * sends type, current value, default and group; this renders whatever it is
 * given.
 *
 * The column that matters is `layer`. A value pinned in the process environment
 * outranks the configuration centre, so editing it here would look like it
 * worked and change nothing -- those inputs are disabled and labelled, and the
 * server refuses the write as well. Two independent refusals, because this one
 * is only a convenience: the browser is not where that rule can be enforced.
 */

/**
 * Measured in the browser rather than chosen by eye. `--text-tertiary` on
 * `--bg-tertiary` is 2.56:1 -- below the 4.5:1 small text needs -- and
 * `--bg-tertiary` is pure white in the light theme, so the pill was invisible
 * against the row. This column is the reason the page exists; it cannot be the
 * hardest thing on it to read.
 */
const LAYER_STYLES: Record<ConfigField["layer"], string> = {
  environment: "bg-warning-surface text-warning",
  "config-centre": "bg-brand-surface text-brand-text",
  "runtime-file": "bg-surface-muted text-ink-muted border border-line",
  default: "bg-surface-muted text-ink-muted border border-line",
};

function asInputValue(value: ConfigField["value"]): string {
  return typeof value === "boolean" ? String(value) : String(value ?? "");
}

export function AdminConfigEditor() {
  const { t } = useTranslation();
  const [fields, setFields] = useState<ConfigField[]>([]);
  const [centreEnabled, setCentreEnabled] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const body = await adminConfigApi.configSchema();
      setFields(body.fields);
      setCentreEnabled(body.config_centre_enabled);
      setEdits({});
    } catch (error) {
      setMessage({ kind: "error", text: error instanceof Error ? error.message : String(error) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const groups = useMemo(() => {
    const byGroup = new Map<string, ConfigField[]>();
    for (const field of fields) {
      const bucket = byGroup.get(field.group) ?? [];
      bucket.push(field);
      byGroup.set(field.group, bucket);
    }
    return [...byGroup.entries()];
  }, [fields]);

  const dirty = Object.keys(edits).length > 0;

  const save = useCallback(async () => {
    setSaving(true);
    setMessage(null);
    try {
      const body = await adminConfigApi.saveConfig(edits);
      setFields(body.fields);
      setEdits({});
      setMessage({ kind: "ok", text: t("admin.config.saved", { count: body.changed.length }) });
    } catch (error) {
      setMessage({ kind: "error", text: error instanceof Error ? error.message : String(error) });
    } finally {
      setSaving(false);
    }
  }, [edits, t]);

  return (
    <section className="rounded-panel shadow-elev-1 bg-surface p-4">
      <SectionHead title={t("admin.config.title")}>
<RowActions>
          <Button variant="secondary" size="xs" onClick={() => void load()} disabled={loading}>
            {t("common.refresh")}
          </Button>
          <Button size="xs" onClick={() => void save()} disabled={!dirty || saving}>
            {saving ? t("admin.ui.running") : t("admin.config.save", { count: Object.keys(edits).length })}
          </Button>
        </RowActions></SectionHead>

      {!centreEnabled && <Muted>{t("admin.config.noCentre")}</Muted>}
      {message && (
        <p className={message.kind === "error" ? "text-danger" : "text-success"} role="status">
          {message.text}
        </p>
      )}

      {groups.map(([group, groupFields]) => (
        <div key={group} className="mt-4">
          <h4 className="text-ink-muted text-sm uppercase">{t(`admin.config.group.${group}`, group)}</h4>
          <table className={ADMIN_TABLE}>
            <tbody>
              {groupFields.map((field) => {
                const editable = field.editable_here && centreEnabled;
                const current = edits[field.alias] ?? asInputValue(field.value);
                return (
                  <tr key={field.alias}>
                    <td>
                      <code>{field.alias}</code>
                      <Muted>{field.summary}</Muted>
                    </td>
                    <td>
                      <span className={`rounded-pill px-2 py-0.5 text-xs ${LAYER_STYLES[field.layer]}`}>
                        {field.layer}
                      </span>
                      {field.requires_restart && <Muted> {t("admin.config.needsRestart")}</Muted>}
                    </td>
                    <td>
                      {field.type === "bool" ? (
                        <input className="size-3.5 shrink-0 accent-[var(--brand)]"
                          type="checkbox"
                          aria-label={field.alias}
                          disabled={!editable}
                          checked={current === "true" || current === "True"}
                          onChange={(event) =>
                            setEdits((prev) => ({ ...prev, [field.alias]: String(event.target.checked) }))
                          }
                        />
                      ) : (
                        <input
                          type="text"
                          aria-label={field.alias}
                          className="rounded-control"
                          disabled={!editable}
                          value={current}
                          onChange={(event) =>
                            setEdits((prev) => ({ ...prev, [field.alias]: event.target.value }))
                          }
                        />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
}
