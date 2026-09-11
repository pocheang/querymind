import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { AdminBlock, Muted, SectionHead, TwoCol } from "./components/AdminPrimitives";

type Props = {
  ops: OpsOverview;
};

/** One `label -> value` line in the environment list. */
function DiagRow({ label, value, fallback }: Readonly<{ label: string; value?: string | null; fallback: string }>) {
  const missing = !value || value === "null" || value === "undefined";
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2 last:border-b-0">
      <span className="shrink-0 font-medium text-ink">{label}</span>
      {missing ? (
        <span className="italic text-ink-muted">{fallback}</span>
      ) : (
        <code className="min-w-0 truncate font-mono text-xs text-ink/75" title={value}>
          {value}
        </code>
      )}
    </div>
  );
}

function ServiceStatus({ ok, error }: Readonly<{ ok: boolean; error?: string }>): ReactNode {
  if (ok) return <Badge variant="success">✓ OK</Badge>;
  return (
    <Badge variant="danger" title={error || "Unknown error"}>
      ✗ {error || "Error"}
    </Badge>
  );
}

export function AdminOpsDiagnostics({ ops }: Readonly<Props>) {
  const { t } = useTranslation();
  const services = Object.entries(ops.services || {});

  return (
    <>
      <SectionHead title={t("admin.ui.diagnostics", "System Diagnostics")} className="mt-4" />
      <Muted className="-mt-0.5 mb-4">
        {t("admin.ui.diagnosticsHint", "System environment, model configuration, and service status")}
      </Muted>

      <TwoCol>
        <AdminBlock titleAs="strong" title={t("admin.ui.environmentModels", "Environment & Models")}>
          <div className="text-xs sm:text-sm">
            <DiagRow label="Python" value={ops.diagnostics?.python_executable} fallback="Not configured" />
            <DiagRow
              label={t("admin.ui.pythonVersion", "Python Version")}
              value={ops.diagnostics?.python_version}
              fallback="Unknown"
            />
            <DiagRow
              label={t("admin.ui.condaEnv", "Conda Environment")}
              value={ops.diagnostics?.conda_env}
              fallback="Not using Conda"
            />
            <DiagRow label="Conda Prefix" value={ops.diagnostics?.conda_prefix} fallback="N/A" />
            <DiagRow
              label={t("admin.ui.modelBackend", "Model Backend")}
              value={ops.diagnostics?.model_backend}
              fallback="Not configured"
            />
            <DiagRow
              label={t("admin.ui.reasoningBackend", "Reasoning Backend")}
              value={ops.diagnostics?.reasoning_model_backend}
              fallback="Same as model backend"
            />
            <DiagRow label="Ollama URL" value={ops.diagnostics?.ollama_base_url} fallback="Not configured" />
            <DiagRow
              label={t("admin.ui.chatModel", "Chat Model")}
              value={ops.diagnostics?.ollama_chat_model}
              fallback="Default model"
            />
            <DiagRow label="Embedding Model" value={ops.diagnostics?.ollama_embed_model} fallback="Default embedding" />
          </div>
        </AdminBlock>

        <AdminBlock titleAs="strong" title={t("admin.ui.keyServiceDetails", "Service Status & Details")}>
          {services.length === 0 ? (
            <p className="p-6 text-center italic text-ink-muted">
              {t("admin.ui.noServiceData", "No service data available")}
            </p>
          ) : (
            services.map(([name, service]) => (
              <div
                key={`svc-detail-${name}`}
                className={`mb-2 rounded-control border bg-surface-hover p-3 ${
                  service.ok ? "border-success-border" : "border-danger-border"
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-ink">{name}</span>
                  <ServiceStatus ok={service.ok} error={service.error} />
                </div>
                {service.path && (
                  <p className="mt-1 truncate text-xs text-ink/80">
                    <strong className="font-semibold">Path:</strong>{" "}
                    <code className="font-mono">{service.path}</code>
                  </p>
                )}
                {service.models && service.models.length > 0 && (
                  <p className="mt-1 flex flex-wrap items-center gap-1 text-xs text-ink/80">
                    <strong className="font-semibold">Models:</strong>
                    {service.models.map((model) => (
                      <Badge key={model} variant="info" size="xs" mono>
                        {model}
                      </Badge>
                    ))}
                  </p>
                )}
              </div>
            ))
          )}
        </AdminBlock>
      </TwoCol>
    </>
  );
}
