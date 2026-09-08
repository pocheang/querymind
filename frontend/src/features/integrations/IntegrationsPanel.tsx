import { type ComponentProps, type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plug } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createConnector, listConnectors, setConnectorEnabled, testConnector, type ConnectorView } from "./api";

/**
 * Governed connectors, in the settings drawer beside long-term memory.
 *
 * The rendering was left behind by the 2026-09-07 stylesheet purge: this
 * carried `integrations-panel` and `runtime-panel-empty`, and neither name has
 * had a rule since the sheets that defined them were deleted -- so every field,
 * list and heading here rendered as raw browser defaults inside an otherwise
 * finished drawer. Nothing reported it, because a class name that matches no
 * rule is invisible to lint, to types and to the tests.
 *
 * Its five fields also carried the same 200-character class string copied
 * inline, which had already drifted from `components/ui/input.tsx` -- `focus:`
 * where the primitive uses `focus-visible:`, and no height. Two copies of a
 * control's appearance is how the two stop matching.
 */

const STATUS_TONE: Record<string, "success" | "neutral"> = { enabled: "success", disabled: "neutral" };
const TEST_TONE: Record<string, "success" | "danger" | "neutral"> = {
  passed: "success",
  failed: "danger",
  not_tested: "neutral",
};

type Draft = {
  connector_id: string;
  name: string;
  base_url: string;
  allowed_hosts: string;
  secret: string;
};

const EMPTY_DRAFT: Draft = {
  connector_id: "",
  name: "",
  base_url: "",
  allowed_hosts: "",
  secret: "",
};

export function IntegrationsPanel() {
  const { t } = useTranslation();
  const [connectors, setConnectors] = useState<readonly ConnectorView[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Loads once. `t` is deliberately absent from the dependency list and from
  // the body: react-i18next returns a new `t` when the language changes, so a
  // fetch keyed on it re-runs for a reason unrelated to the data -- and under a
  // `useTranslation` that does not memoize it is an unbounded render loop.
  // The same trap cost three vitest workers 3GB in the memory panel next door.
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const items = await listConnectors(controller.signal);
        if (!controller.signal.aborted) setConnectors(items);
      } catch (error) {
        if (controller.signal.aborted) return;
        setLoadError(error instanceof Error ? error.message : "");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  const shownNotice =
    loadError === null ? notice : { tone: "error" as const, text: loadError || t("features.integrations.loadError") };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNotice(null);
    setBusyId("create");
    try {
      const created = await createConnector({
        connector_id: draft.connector_id.trim(),
        name: draft.name.trim(),
        base_url: draft.base_url.trim(),
        allowed_hosts: draft.allowed_hosts
          .split(",")
          .map((host) => host.trim())
          .filter(Boolean),
        secret: draft.secret,
      });
      setConnectors((items) => [...items, created].sort((left, right) => left.name.localeCompare(right.name)));
      setDraft(EMPTY_DRAFT);
      setNotice({ tone: "success", text: t("features.integrations.connected") });
    } catch (error) {
      setNotice({
        tone: "error",
        text: error instanceof Error ? error.message : t("features.integrations.connectError"),
      });
    } finally {
      setBusyId(null);
    }
  };

  const toggle = async (connector: ConnectorView) => {
    setBusyId(connector.connector_id);
    setNotice(null);
    try {
      const updated = await setConnectorEnabled(connector.connector_id, connector.status === "disabled");
      setConnectors((items) => items.map((item) => (item.connector_id === updated.connector_id ? updated : item)));
    } catch (error) {
      setNotice({
        tone: "error",
        text: error instanceof Error ? error.message : t("features.integrations.updateError"),
      });
    } finally {
      setBusyId(null);
    }
  };

  const probe = async (connector: ConnectorView) => {
    setBusyId(connector.connector_id);
    setNotice(null);
    try {
      const result = await testConnector(connector.connector_id);
      setConnectors((items) =>
        items.map((item) =>
          item.connector_id === connector.connector_id ? { ...item, test_status: result.status } : item
        )
      );
      setNotice({ tone: result.status === "passed" ? "success" : "error", text: result.message });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : t("features.integrations.testError") });
    } finally {
      setBusyId(null);
    }
  };

  const field = (key: keyof Draft, label: string, extra: ComponentProps<typeof Input> = {}) => (
    <div className="space-y-1">
      <Label htmlFor={`connector-${key}`}>{label}</Label>
      <Input
        id={`connector-${key}`}
        value={draft[key]}
        onChange={(event) => setDraft({ ...draft, [key]: event.target.value })}
        disabled={busyId !== null}
        {...extra}
      />
    </div>
  );

  return (
    <section aria-label={t("features.integrations.ariaLabel")}>
      <details className="group rounded-card border border-line-subtle bg-surface-muted">
        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-card px-3 py-2 text-xs font-bold text-ink hover:bg-brand-surface">
          <Plug className="size-3.5 text-brand-accent" aria-hidden="true" />
          <span className="flex-1">{t("features.integrations.title")}</span>
          {!loading && loadError === null && (
            <Badge variant={connectors.length ? "brand" : "neutral"} size="sm" mono>
              {connectors.length}
            </Badge>
          )}
        </summary>

        <div className="space-y-2.5 border-t border-line-subtle p-3">
          <p className="text-[11px] leading-relaxed text-ink-muted">{t("features.integrations.description")}</p>

          {loading && (
            <p aria-live="polite" className="py-3 text-center text-[11px] text-ink-muted">
              {t("features.integrations.loading")}
            </p>
          )}

          {!loading && loadError === null && connectors.length === 0 && (
            <p className="rounded-control border border-dashed border-line px-3 py-4 text-center text-[11px] text-ink-muted">
              {t("features.integrations.empty")}
            </p>
          )}

          {connectors.length > 0 && (
            <ul className="list-none space-y-1.5">
              {connectors.map((connector) => (
                <li
                  key={connector.connector_id}
                  className="space-y-1.5 rounded-control border border-line-subtle bg-surface p-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 space-y-1">
                      <p className="truncate text-[11px] font-semibold text-ink">{connector.name}</p>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant={STATUS_TONE[connector.status] ?? "neutral"} size="xs">
                          {t(`features.integrations.status.${connector.status}`)}
                        </Badge>
                        <Badge variant={TEST_TONE[connector.test_status] ?? "neutral"} size="xs">
                          {t(`features.integrations.testStatus.${connector.test_status}`)}
                        </Badge>
                        <span className="truncate font-mono text-[9px] text-ink-muted">{connector.connector_id}</span>
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button variant="secondary" size="xs" onClick={() => void toggle(connector)} disabled={busyId !== null}>
                        {connector.status === "enabled"
                          ? t("features.integrations.disable")
                          : t("features.integrations.enable")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => void probe(connector)}
                        disabled={busyId !== null || connector.status !== "enabled"}
                      >
                        {t("features.integrations.test")}
                      </Button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <form className="space-y-2 rounded-control border border-line-subtle bg-surface p-2.5" onSubmit={(event) => void submit(event)}>
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-ink">
              {t("features.integrations.connectTitle")}
            </h3>
            {field("connector_id", t("features.integrations.integrationId"), {
              required: true,
              pattern: "[a-z][a-z0-9_-]{0,63}",
            })}
            {field("name", t("features.integrations.name"), { required: true, maxLength: 120 })}
            {field("base_url", t("features.integrations.baseUrl"), { required: true, type: "url" })}
            {field("allowed_hosts", t("features.integrations.allowedHosts"), {
              required: true,
              placeholder: t("features.integrations.allowedHostsPlaceholder"),
            })}
            {field("secret", t("features.integrations.accessSecret"), {
              required: true,
              type: "password",
              autoComplete: "new-password",
            })}
            <Button size="sm" type="submit" disabled={busyId !== null} className="w-full">
              {busyId === "create" ? t("features.integrations.connecting") : t("features.integrations.addConnector")}
            </Button>
          </form>

          {shownNotice && (
            <p
              role="status"
              aria-live="polite"
              className={
                shownNotice.tone === "error"
                  ? "rounded-control border border-danger-border bg-danger-surface px-2.5 py-1.5 text-[11px] text-danger"
                  : "rounded-control border border-success-border bg-success-surface px-2.5 py-1.5 text-[11px] text-success"
              }
            >
              {shownNotice.text}
            </p>
          )}
        </div>
      </details>
    </section>
  );
}
