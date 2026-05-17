import "../../../styles/components/welcome-screen.css";

type Props = {
  documentsCount?: number;
  sessionsCount?: number;
  onCreateSession?: () => void;
  onNavigateToArchitecture?: () => void;
};

export function WelcomeScreen({
  documentsCount = 0,
  sessionsCount = 0,
  onCreateSession,
  onNavigateToArchitecture
}: Props) {
  return (
    <div className="welcome-screen">
      <div className="welcome-header">
        <span className="welcome-badge">Console Ready</span>
        <h2 className="welcome-title">多智能体 RAG 系统</h2>
        <p className="welcome-subtitle">
          基于证据链的智能问答系统，支持多模态文档处理、知识图谱检索和 Web 研究
        </p>
      </div>

      <div className="welcome-stats">
        <div className="stat-card">
          <div className="stat-icon">📚</div>
          <div className="stat-content">
            <div className="stat-value">{documentsCount}</div>
            <div className="stat-label">知识库文档</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-content">
            <div className="stat-value">{sessionsCount}</div>
            <div className="stat-label">历史会话</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🤖</div>
          <div className="stat-content">
            <div className="stat-value">4</div>
            <div className="stat-label">智能体模式</div>
          </div>
        </div>
      </div>

      <div className="welcome-actions">
        <button
          type="button"
          className="welcome-action-btn primary"
          onClick={onCreateSession}
        >
          <span className="action-icon">✨</span>
          <span className="action-text">开始新对话</span>
        </button>

        <button
          type="button"
          className="welcome-action-btn secondary"
          onClick={onNavigateToArchitecture}
        >
          <span className="action-icon">🏗️</span>
          <span className="action-text">查看系统架构</span>
        </button>
      </div>

      <div className="welcome-features">
        <div className="feature-card">
          <div className="feature-icon">🔍</div>
          <h4 className="feature-title">智能检索</h4>
          <p className="feature-desc">向量检索、图谱检索、BM25 混合检索，多策略融合</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🌐</div>
          <h4 className="feature-title">Web 研究</h4>
          <p className="feature-desc">实时网络搜索，获取最新信息和外部知识</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">📄</div>
          <h4 className="feature-title">多模态处理</h4>
          <p className="feature-desc">支持 PDF、图片、图表批量提取和流式加载</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🔗</div>
          <h4 className="feature-title">证据链追踪</h4>
          <p className="feature-desc">完整展示路由决策、检索来源和推理过程</p>
        </div>
      </div>

      <div className="welcome-tips">
        <div className="tip-item">
          <span className="tip-icon">💡</span>
          <span className="tip-text">使用 <kbd>Ctrl+Enter</kbd> 快速发送消息</span>
        </div>
        <div className="tip-item">
          <span className="tip-icon">📎</span>
          <span className="tip-text">拖拽文件到输入框或侧边栏快速上传</span>
        </div>
        <div className="tip-item">
          <span className="tip-icon">🎯</span>
          <span className="tip-text">选择不同的 Agent 模式以获得最佳回答</span>
        </div>
      </div>
    </div>
  );
}
