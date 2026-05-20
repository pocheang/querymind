import { Link } from "react-router-dom";
import "../styles/pages/architecture.css";
import { DataFlowVisualization } from "../components/DataFlowVisualization";
import { getThemeIcon } from "@/lib/theme";

type Props = {
  isLoggedIn: boolean;
  themeLabel: string;
  onThemeToggle: () => void;
};

export function ArchitecturePage({ isLoggedIn, themeLabel, onThemeToggle }: Props) {
  const themeIcon = getThemeIcon(themeLabel);

  return (
    <div className="admin-shell architecture-shell">
      <header className="topbar">
        <div>
          <h2>CyberSec RAG Architecture</h2>
          <p className="muted">前端、鉴权、检索编排、存储和流式响应的全链路总览。</p>
        </div>
        <div className="top-actions">
          <button type="button" className="secondary" onClick={onThemeToggle}>
            {themeIcon} {themeLabel}
          </button>
          <Link className="secondary link-btn" to={isLoggedIn ? "/app" : "/app/login"}>
            {isLoggedIn ? "返回系统" : "去登录"}
          </Link>
        </div>
      </header>

      <section className="panel">
        <div className="section-head">
          <strong>1. 全链路数据流</strong>
        </div>
        <DataFlowVisualization />
      </section>

      <section className="architecture-grid">
        <article className="panel">
          <div className="section-head">
            <strong>2. 核心方法</strong>
          </div>
          <ul className="compact-list">
            <li>混合检索：Vector + BM25 + RRF + Rerank (BGE-reranker-v2-m3)</li>
            <li>图谱检索：实体匹配 + 邻居关系 + APOC 插件</li>
            <li>多智能体编排：LangGraph 工作流 + 条件路由</li>
            <li>分层执行：Fast/Balanced/Deep 三档 + 负载降级</li>
            <li>父子分块策略：平衡精度与上下文 (parent 1500 / child 600 tokens)</li>
            <li>查询重写：去重优化减少 10-30% 冗余 LLM 调用</li>
            <li>中文NLP优化：分词 + 同义词扩展 + 查询预处理</li>
            <li>高级RAG：查询分解 + Self-RAG 评估</li>
            <li>流式生成：SSE 按 chunk 返回 + 心跳保活</li>
            <li>流式PDF处理：真实流式 + 70% 内存优化</li>
            <li>批量图表提取：并行处理 + 吞吐量优化</li>
            <li>OCR 支持：Tesseract (eng+chi_sim) + 图像预处理</li>
            <li>图像字幕：AI 驱动的视觉内容描述</li>
            <li>Prompt 管理：版本控制 + 审批流 + 回滚</li>
            <li>性能对比：基线系统 + 综合评估指标</li>
            <li>Agent 可视化：实时追踪 + SSE 流式更新</li>
            <li>CI/CD 质门：自动化 RAG 评估 + 性能基准测试</li>
          </ul>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>3. 数据库与存储</strong>
          </div>
          <ul className="compact-list">
            <li>SQLite：用户、会话、审计日志、Prompt版本、API设置加密存储</li>
            <li>ChromaDB：向量索引 (持久化到 data/chroma)</li>
            <li>Neo4j 5.26：关系图谱 + APOC 插件</li>
            <li>JSONL：BM25 语料 (chunks.jsonl + parents.jsonl)</li>
            <li>JSON：多会话历史（按用户隔离 sessions/user_*/*.json）</li>
            <li>文件系统：上传文档 (uploads/user_*/) + OCR 缓存</li>
            <li>内存缓存：检索配置 + 运行时状态</li>
          </ul>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>4. 安全能力</strong>
          </div>
          <ul className="compact-list">
            <li>密码策略：PBKDF2 哈希 + salt + 12-128字符 + 特殊字符要求</li>
            <li>JWT 鉴权：Bearer token + HttpOnly Cookie + 过期机制</li>
            <li>Cookie 安全：Secure + SameSite=Strict + HttpOnly</li>
            <li>RBAC 权限：用户/管理员角色 + 资源隔离</li>
            <li>审批令牌：单次使用 + 常量时间比较防时序攻击</li>
            <li>速率限制：管理员操作 1-5 req/hour + 查询配额</li>
            <li>输入验证：安全检查 + 危险指令拦截 + SQL注入防护</li>
            <li>会话隔离：按用户隔离上传目录、会话文件、文档访问</li>
            <li>API密钥加密：AES加密存储 + 白名单URL验证</li>
            <li>审计日志：全量记录敏感操作 + 失败追踪</li>
            <li>熔断器：故障隔离 + 舱壁模式 + 重试逻辑</li>
          </ul>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>5. 关键接口</strong>
          </div>
          <pre className="diagram-block">{`# 认证与用户
POST /auth/register
POST /auth/login
POST /auth/logout
POST /auth/refresh
GET  /auth/me

# 查询与会话
POST /query
POST /query/stream
GET  /sessions
POST /sessions
DELETE /sessions/{id}
PATCH /sessions/{id}/strategy
PATCH /sessions/{id}/messages/{message_id}
GET  /sessions/{id}/memory
POST /sessions/{id}/memory/clear

# 文档管理
GET  /documents
DELETE /documents/{doc_id}
POST /documents/reindex
POST /upload

# Prompt 管理
GET  /prompts
POST /prompts
PUT  /prompts/{id}
POST /prompts/check
POST /prompts/{id}/approve
POST /prompts/{id}/rollback

# 管理员 - 用户管理
GET  /admin/users
POST /admin/users
PATCH /admin/users/{user_id}/role
PATCH /admin/users/{user_id}/status
DELETE /admin/users/{user_id}

# 管理员 - 运维操作
GET  /admin/ops/profiles
POST /admin/ops/profiles
POST /admin/ops/canary
POST /admin/ops/rollback
POST /admin/ops/benchmark
POST /admin/ops/replay
GET  /admin/ops/report

# 管理员 - 模型配置
GET  /admin/model-settings
PUT  /admin/model-settings

# 用户 - API 设置
GET  /user/api-settings
PUT  /user/api-settings

# 评估与追踪
POST /api/evaluation/compare
GET  /api/evaluation/baselines
GET  /api/agent-tracking/executions/{id}
GET  /api/agent-tracking/stream/{id}

# 高级 RAG
POST /api/advanced-rag/decompose
POST /api/advanced-rag/self-rag

# 健康检查
GET  /health
GET  /ready
GET  /metrics`}</pre>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>6. 模型后端支持</strong>
          </div>
          <ul className="compact-list">
            <li>Ollama：本地部署 (qwen2.5, llama3, deepseek 等)</li>
            <li>OpenAI：GPT-4, GPT-3.5 + text-embedding-3</li>
            <li>Anthropic：Claude 3.5 Sonnet + OpenAI embeddings</li>
            <li>混合部署：本地推理 + 云端嵌入</li>
            <li>运行时切换：无需重启动态配置</li>
          </ul>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>7. 运维与治理</strong>
          </div>
          <ul className="compact-list">
            <li>检索配置：baseline/advanced/safe 三档预设</li>
            <li>金丝雀路由：灰度发布 + A/B 测试</li>
            <li>配置回滚：一键恢复上一版本</li>
            <li>基准测试：延迟分析 + 吞吐量测试</li>
            <li>查询重放：历史查询回归测试</li>
            <li>运维报告：系统健康度 + 性能指标</li>
            <li>负载降级：高负载时自动降档 (&gt;80%)</li>
          </ul>
        </article>

        <article className="panel">
          <div className="section-head">
            <strong>8. 前端技术栈</strong>
          </div>
          <ul className="compact-list">
            <li>React 18 + TypeScript：类型安全的组件开发</li>
            <li>Vite 6.4：快速构建 + HMR 热更新</li>
            <li>React Router：SPA 路由管理</li>
            <li>关键CSS提取：86% 体积优化 (99KB → 14KB)</li>
            <li>代码分割：按需加载 + 懒加载优化</li>
            <li>现代CSS架构：模块化 + 主题系统</li>
            <li>SSE 流式渲染：实时消息流展示</li>
            <li>响应式设计：移动端适配</li>
          </ul>
        </article>
      </section>
    </div>
  );
}
