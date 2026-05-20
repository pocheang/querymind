import type { SessionMessage } from "@/types/api";
import { EMPTY_METADATA } from "@/pages/chat/constants";
import { MarkdownBlock } from "@/pages/chat/components/MarkdownBlock";
import { CollapsibleSection } from "@/pages/chat/components/CollapsibleSection";
import { MetadataBadges } from "@/pages/chat/components/MetadataBadges";

type Props = {
  message: SessionMessage;
  onEditMessage: (msg: SessionMessage) => Promise<void>;
  onRemoveMessage: (msg: SessionMessage) => Promise<void>;
};

export function MessageCard({ message, onEditMessage, onRemoveMessage }: Props) {
  const isAssistant = message.role === "assistant";
  const metadata = message.metadata || EMPTY_METADATA;

  return (
    <article
      className={`bubble ${isAssistant ? "assistant" : "user"}`}
      role="article"
      aria-label={isAssistant ? "助手回复" : "用户消息"}
    >
      <div className="message-head">
        <div className="message-identity">
          <span className="message-avatar" aria-hidden="true">
            {isAssistant ? "🤖" : "👤"}
          </span>
          <span className="message-role">{isAssistant ? "助手" : "你"}</span>
        </div>
        {message.message_id.startsWith("local-") ? null : (
          <div className="row-actions">
            <button
              type="button"
              className="secondary tiny-btn"
              onClick={() => void onEditMessage(message)}
              aria-label="修改此消息"
            >
              修改
            </button>
            <button
              type="button"
              className="danger tiny-btn"
              onClick={() => {
                if (window.confirm("确定删除这条消息吗？此操作无法撤销。")) {
                  void onRemoveMessage(message);
                }
              }}
              aria-label="删除此消息"
            >
              删除
            </button>
          </div>
        )}
      </div>

      <div className="markdown">
        <MarkdownBlock text={message.content || ""} />
      </div>

      {isAssistant && (
        <>
          <MetadataBadges metadata={metadata} />

          {(metadata.execution_steps || []).length > 0 && (
            <CollapsibleSection
              open={message.message_id === "local-assistant-stream"}
              className="process-panel"
              title="执行过程"
              ariaLabel="展开或收起执行过程"
            >
              <div className="process-timeline">
                {(metadata.execution_steps || []).map((step, index) => (
                  <div key={`${message.message_id}-step-${index}`} className="process-step">
                    <div className="process-step-head">
                      <span className={`process-kind kind-${step.kind || "default"}`}>
                        {step.kind || "step"}
                      </span>
                      <strong>{step.label || "处理中"}</strong>
                      <span className="process-time">
                        {step.at ? new Date(step.at).toLocaleTimeString("zh-CN", { hour12: false }) : ""}
                      </span>
                    </div>
                    {step.detail && <div className="process-detail">{step.detail}</div>}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {(metadata.thoughts || []).length > 0 && (
            <CollapsibleSection title="思考摘要" ariaLabel="展开或收起思考摘要">
              <ul className="compact-list">
                {(metadata.thoughts || []).slice(-8).map((thought, index) => (
                  <li key={`${message.message_id}-thought-${index}`}>{thought}</li>
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {(metadata.citations || []).length > 0 && (
            <CollapsibleSection title="引用证据" ariaLabel="展开或收起引用证据">
              <div className="citation-grid">
                {(metadata.citations || []).slice(0, 8).map((citation, index) => (
                  <div key={`${message.message_id}-cit-${index}`} className="citation-card">
                    <strong>{citation.source || "unknown"}</strong>
                    <MarkdownBlock text={citation.content || ""} />
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {metadata.graph_result &&
            (metadata.graph_result.neighbors.length > 0 || metadata.graph_result.paths.length > 0) && (
              <CollapsibleSection title="图谱关系" ariaLabel="展开或收起图谱关系">
                <div className="graph-result-panel">
                  {metadata.graph_result.neighbors.length > 0 && (
                    <div className="graph-section">
                      <strong>邻居关系 ({metadata.graph_result.neighbors.length})</strong>
                      <div className="graph-neighbors">
                        {metadata.graph_result.neighbors.slice(0, 10).map((neighbor, index) => (
                          <div key={`${message.message_id}-neighbor-${index}`} className="graph-neighbor-item">
                            <span className="graph-entity">{neighbor.entity}</span>
                            <span className="graph-relation">
                              {neighbor.direction === "out" ? "→" : "←"}
                              <span className="relation-label">{neighbor.relation}</span>
                              {neighbor.direction === "out" ? "→" : "←"}
                            </span>
                            <span className="graph-target">目标实体</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.graph_result.paths.length > 0 && (
                    <div className="graph-section">
                      <strong>推理路径 ({metadata.graph_result.paths.length})</strong>
                      <div className="graph-paths">
                        {metadata.graph_result.paths.slice(0, 5).map((path, index) => {
                          // 处理两种数据格式：
                          // 1. 新格式: {entities: [...], relations: [...]}
                          // 2. 旧格式: {source, rel1, middle, rel2, target}
                          const hasNewFormat = 'entities' in path && Array.isArray(path.entities);
                          const hasOldFormat = 'source' in path && 'middle' in path && 'target' in path;

                          if (hasNewFormat) {
                            return (
                              <div key={`${message.message_id}-path-${index}`} className="graph-path-item">
                                {path.entities.map((entity, entityIndex) => (
                                  <span key={entityIndex} className="path-segment">
                                    <span className="path-entity">{entity}</span>
                                    {entityIndex < (path.relations?.length || 0) && (
                                      <span className="path-arrow">
                                        → <span className="path-relation">{path.relations[entityIndex]}</span> →
                                      </span>
                                    )}
                                  </span>
                                ))}
                              </div>
                            );
                          } else if (hasOldFormat) {
                            return (
                              <div key={`${message.message_id}-path-${index}`} className="graph-path-item">
                                <span className="path-segment">
                                  <span className="path-entity">{path.source}</span>
                                  <span className="path-arrow">
                                    → <span className="path-relation">{path.rel1 || 'RELATED'}</span> →
                                  </span>
                                </span>
                                <span className="path-segment">
                                  <span className="path-entity">{path.middle}</span>
                                  <span className="path-arrow">
                                    → <span className="path-relation">{path.rel2 || 'RELATED'}</span> →
                                  </span>
                                </span>
                                <span className="path-segment">
                                  <span className="path-entity">{path.target}</span>
                                </span>
                              </div>
                            );
                          } else {
                            return (
                              <div key={`${message.message_id}-path-${index}`} className="graph-path-item">
                                <span className="path-error">路径数据不完整</span>
                              </div>
                            );
                          }
                        })}
                      </div>
                    </div>
                  )}
                  {metadata.graph_result.context && (
                    <div className="graph-section">
                      <strong>图谱上下文</strong>
                      <pre className="graph-context">{metadata.graph_result.context}</pre>
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            )}
        </>
      )}
    </article>
  );
}
