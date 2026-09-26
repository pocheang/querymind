# QueryMind 文档中心

QueryMind（智询）企业级私有知识库 Agentic RAG 系统的文档入口。

**状态：** v0.7 正式就绪（生产环境标准）· **维护者：** QueryMind maintainers

## 说明

QueryMind 现已正式发布 **v0.7** 版本，包含交互式系统全景架构（五重视角动态切换）、LangGraph 实时执行轨迹调试面板、着陆页核心能力交互弹窗，以及全套性能优化。
最新补丁 **v0.7.0.3** 升级了动态双轨制澄清 Agent（静态规则快速通道 + 真实 LLM 动态反问）、全面对标 Codex/Claude Code 规范化交互提问风格（首选方案置顶推荐 + 自定义补充选项），并彻底解决 SonarQube / SonarCloud 质量门禁全量问题（0 缺陷 / 0 漏洞 / 0 代码异味）。

## 核心文档入口

- [项目 README](../README.md) — 项目核心特性与快速启动指南
- [领域智能体与插件化工具架构设计](superpowers/specs/domain-specialist-and-plugin-tools-architecture.md) — 领域专家 Agent 与插件化受控工具分层解耦体系
- [垂直领域扩展与插件开发实战指南](development/domain-extension-quickstart.md) — 5 分钟构建垂直领域 Agent 与工具包标准范式
- [v0.7.0.3 发布说明](releases/v0.7.0.3-release-notes.md) — 最新补丁：动态双轨澄清 Agent、Codex 交互提问规范与 Sonar 门禁全通
- [v0.7.0.2 发布说明](releases/v0.7.0.2-release-notes.md) — SonarQube 质量门禁 100% 清零、重复代码归零与模块化解耦
- [v0.7.0.1 发布说明](releases/v0.7.0.1-release-notes.md) — 表格与 SQL 分析、图谱社区、多搜索源、注入防护及升级说明
- [v0.7.0 发布说明](releases/v0.7.0-release-notes.md) — v0.7.0 架构升级、执行跟踪与性能优化详细说明
- [版本发布总览](releases/README.md) — 历史版本发布说明总览
- [变更日志](../CHANGELOG.md) — 完整版本变更日志与升级记录


内部专用内容（历史归档、设计记录、模板、安全审计）不发布，保留在本地 `docs/archive/`、
`docs/design/`、`docs/templates/`、`docs/security/`（均在 `.gitignore` 中）。
开发日志（`docs/development/daily-logs/`）、实施计划（`docs/superpowers/`）、
深度解析与问题清单（`docs/querymind-deep-dive/`）和 `CLAUDE.md` 同样只保留在本地。
