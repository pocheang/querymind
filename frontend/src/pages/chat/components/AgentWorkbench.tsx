type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type AgentMode = {
  key: AgentClassHint;
  title: string;
  desc: string;
};

type Props = {
  agentClassHint: AgentClassHint;
  agentModes: AgentMode[];
  agentDistribution: Array<{ agent: string; count: number }>;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
};

export function AgentWorkbench({
  agentClassHint,
  agentModes,
  agentDistribution,
  onSwitchAgentMode,
}: Props) {
  return (
    <section className="panel">
      <div className="section-head">
        <strong>Agent Workbench</strong>
        <small className="muted">current: {agentClassHint || "auto"}</small>
      </div>
      <div className="agent-mode-grid">
        {agentModes.map((mode) => (
          <button
            key={mode.title}
            type="button"
            className={`agent-mode-card ${agentClassHint === mode.key ? "active" : ""}`}
            onClick={() => onSwitchAgentMode(mode.key)}
          >
            <strong>{mode.title}</strong>
            <span>{mode.desc}</span>
          </button>
        ))}
      </div>
      <div className="agent-stats">
        {agentDistribution.length === 0 && <span className="muted">No indexed docs yet</span>}
        {agentDistribution.map((item) => (
          <span key={item.agent} className="chip">
            {item.agent}: {item.count}
          </span>
        ))}
      </div>
    </section>
  );
}
