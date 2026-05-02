import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
};

export function AdminOpsDiagnostics({ ops }: Props) {
  return (
    <>
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>运行诊断</strong>
      </div>
      <p className="muted" style={{ marginTop: -2, marginBottom: 8 }}>
        用于排查"后端进程 / 环境 / 连接中断"类问题，直接展示当前解释器、Conda 环境、模型配置和最近错误。
      </p>
      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>环境与模型</strong>
          <div className="ops-diagnostic-list">
            <div>
              <span>Python</span>
              <code>{ops.diagnostics?.python_executable || "-"}</code>
            </div>
            <div>
              <span>Python 版本</span>
              <code>{ops.diagnostics?.python_version || "-"}</code>
            </div>
            <div>
              <span>Conda 环境</span>
              <code>{ops.diagnostics?.conda_env || "-"}</code>
            </div>
            <div>
              <span>Conda Prefix</span>
              <code>{ops.diagnostics?.conda_prefix || "-"}</code>
            </div>
            <div>
              <span>模型后端</span>
              <code>{ops.diagnostics?.model_backend || "-"}</code>
            </div>
            <div>
              <span>推理后端</span>
              <code>{ops.diagnostics?.reasoning_model_backend || "-"}</code>
            </div>
            <div>
              <span>Ollama URL</span>
              <code>{ops.diagnostics?.ollama_base_url || "-"}</code>
            </div>
            <div>
              <span>聊天模型</span>
              <code>{ops.diagnostics?.ollama_chat_model || "-"}</code>
            </div>
            <div>
              <span>Embedding</span>
              <code>{ops.diagnostics?.ollama_embed_model || "-"}</code>
            </div>
          </div>
        </div>
        <div className="ops-trend-list">
          <strong>关键服务细节</strong>
          <div className="ops-diagnostic-list">
            {Object.entries(ops.services || {}).map(([name, svc]) => (
              <div key={`svc-detail-${name}`}>
                <span>{name}</span>
                <code>
                  {svc.ok ? "ok" : `error=${svc.error || "unknown"}`}
                  {svc.path ? ` | ${svc.path}` : ""}
                  {svc.models && svc.models.length > 0 ? ` | models=${svc.models.join(", ")}` : ""}
                </code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
