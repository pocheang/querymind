import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
};

export function AdminOpsDiagnostics({ ops }: Props) {
  const { t } = useTranslation();

  return (
    <>
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>{t("admin.ui.diagnostics")}</strong>
      </div>
      <p className="muted" style={{ marginTop: -2, marginBottom: 8 }}>
        {t("admin.ui.diagnosticsHint")}
      </p>
      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>{t("admin.ui.environmentModels")}</strong>
          <div className="ops-diagnostic-list">
            <div><span>Python</span><code>{ops.diagnostics?.python_executable || "-"}</code></div>
            <div><span>{t("admin.ui.pythonVersion")}</span><code>{ops.diagnostics?.python_version || "-"}</code></div>
            <div><span>{t("admin.ui.condaEnv")}</span><code>{ops.diagnostics?.conda_env || "-"}</code></div>
            <div><span>Conda Prefix</span><code>{ops.diagnostics?.conda_prefix || "-"}</code></div>
            <div><span>{t("admin.ui.modelBackend")}</span><code>{ops.diagnostics?.model_backend || "-"}</code></div>
            <div><span>{t("admin.ui.reasoningBackend")}</span><code>{ops.diagnostics?.reasoning_model_backend || "-"}</code></div>
            <div><span>Ollama URL</span><code>{ops.diagnostics?.ollama_base_url || "-"}</code></div>
            <div><span>{t("admin.ui.chatModel")}</span><code>{ops.diagnostics?.ollama_chat_model || "-"}</code></div>
            <div><span>Embedding</span><code>{ops.diagnostics?.ollama_embed_model || "-"}</code></div>
          </div>
        </div>
        <div className="ops-trend-list">
          <strong>{t("admin.ui.keyServiceDetails")}</strong>
          <div className="ops-diagnostic-list">
            {Object.entries(ops.services || {}).map(([name, service]) => (
              <div key={`svc-detail-${name}`}>
                <span>{name}</span>
                <code>
                  {service.ok ? "ok" : `error=${service.error || "unknown"}`}
                  {service.path ? ` | ${service.path}` : ""}
                  {service.models && service.models.length > 0 ? ` | models=${service.models.join(", ")}` : ""}
                </code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
