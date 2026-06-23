# 📚 QueryMind 文档中心

<div align="center">

**企业级智能问答引擎完整文档**

[快速开始](#快速入门指南) · [用户手册](#用户手册) · [开发文档](#开发文档) · [API 文档](#api-文档)

</div>

---

## 📖 用户文档

### 🚀 快速入门指南

- **[安装部署指南](../guides/CONFIGURATION_GUIDE.md)** - 系统安装、配置和启动
- **[5分钟快速开始](../guides/startup-guide.md)** - 快速体验 QueryMind
- **[API 配置指南](../guides/API_SETTINGS_GUIDE.md)** - 模型 API 配置教程
- **[常见问题排查](../guides/troubleshooting-black-screen.md)** - 黑屏等常见问题解决

### 📘 用户手册

- **[系统概览](../guides/business/SYSTEM_OVERVIEW.md)** - QueryMind 功能概述
- **[核心功能说明](../guides/business/FEATURES.md)** - 详细功能介绍
- **[工作原理](../guides/business/HOW_IT_WORKS.md)** - 系统运行机制
- **[术语表](../guides/business/GLOSSARY.md)** - 专业术语解释

### ⚙️ 配置说明

- **[系统配置参考](../guides/development/CONFIGURATION_REFERENCE.md)** - 完整配置项说明
- **[性能优化指南](../guides/PDF_PERFORMANCE_TUNING.md)** - 性能调优技巧
- **[数据存储说明](../guides/development/DATA_STORAGE.md)** - 数据管理与备份

---

## 💻 开发文档

### 🏗️ 架构设计

- **[系统架构概览](../guides/development/ARCHITECTURE.md)** - 整体架构设计
- **[多智能体系统](../guides/development/MULTI_AGENT_SYSTEM.md)** - Agent 协作机制
- **[检索系统设计](../guides/development/RETRIEVAL_SYSTEM.md)** - 混合检索架构
- **[LangGraph 状态图设计](../it_ops_langgraph_stategraph_design.md)** - 工作流引擎设计

### 📋 API 文档

- **[API 开发指南](../guides/development/API_DEVELOPMENT.md)** - 后端 API 开发
- **[前端开发指南](../guides/development/FRONTEND_DEVELOPMENT.md)** - React 前端开发
- **[在线 API 文档](http://127.0.0.1:8000/docs)** - FastAPI Swagger 文档（需启动后端）

### 🛠️ 开发指南

- **[环境搭建](../guides/development/SETUP_GUIDE.md)** - 开发环境配置
- **[开发工作流](../guides/development/DEVELOPMENT_WORKFLOW.md)** - 开发流程规范
- **[代码规范](../guides/development/CODE_STANDARDS.md)** - 编码标准
- **[后端最佳实践](../BACKEND_BEST_PRACTICES.md)** - Python/FastAPI 最佳实践

### 🔌 集成指南

- **[Agent 集成指南](../AGENT_INTEGRATION_GUIDE.md)** - 自定义 Agent 开发
- **[React Agent 指南](../REACT_AGENT_GUIDE.md)** - ReAct 模式 Agent
- **[Claude Skills 指南](../guides/claude-skills-guide.md)** - Claude 技能集成

### 🤝 贡献指南

- **[如何贡献](../../CONTRIBUTING.md)** - 贡献代码流程
- **[文档模板](../templates/README.md)** - 文档编写模板
- **[变更政策](../archive/plans/2026-06-02-1730-code-change-policy.md)** - 代码变更规范

---

## 🎨 功能特性

### 🤖 智能体系统

- **[Agent 执行追踪](../features/agents/agent_execution_tracking.md)** - 实时可视化追踪
- **[多智能体协作](../guides/development/MULTI_AGENT_SYSTEM.md)** - Agent 编排机制
- **[Agent 功能概览](../features/agents/README.md)** - Agent 系统介绍

### 🔍 检索增强生成 (RAG)

- **[高级 RAG 技术](../features/rag/advanced_rag_techniques.md)** - 查询分解、Self-RAG
- **[混合检索策略](../features/rag/README.md)** - 向量 + BM25 + 重排序
- **[性能对比框架](../features/rag/performance_comparison_framework.md)** - 检索效果评估

### 📄 PDF 文档处理

- **[PDF 功能概览](../features/pdf/README.md)** - PDF 处理能力介绍
- **[Docling 集成](../features/pdf/docling_integration.md)** - 高级 PDF 解析
- **[图表提取](../features/pdf/chart_extraction.md)** - 图表识别与提取
- **[批量图表提取器](../features/pdf/batch_chart_extractor.md)** - 批量处理工具
- **[PDF 测试指南](../guides/PDF_TESTING_GUIDE.md)** - PDF 功能测试

### 🔤 OCR 与 NLP

- **[OCR 集成](../features/ocr/README.md)** - 图片文字识别
- **[国际化支持](../features/i18n-guide.md)** - 多语言处理

---

## 📦 版本信息

### 📝 更新日志

- **[完整变更日志](../../CHANGELOG.md)** - 所有版本变更记录
- **[版本历史](../history/VERSION_HISTORY.md)** - 版本演进说明

### 🚀 版本历史

- **[v0.5.0 发布说明](../releases/RELEASE_NOTES_v0.5.0.md)** - 最新版本 (2026-06-23)
- **[v0.4.6 发布说明](../releases/RELEASE_NOTES_v0.4.6.md)** - 后端修复版本
- **[v0.4.4 发布说明](../releases/RELEASE_NOTES_v0.4.4.md)** - 代码质量提升
- **[v0.4.0 发布说明](../releases/RELEASE_NOTES_v0.4.0.md)** - 主要功能更新
- **[所有版本](../releases/README.md)** - 完整版本列表

### 🔖 发布说明

- **[v0.5.0 完成报告](../archive/completion-reports/2026-06-23-v0.5.0-summary.md)** - 最新版本总结
- **[v0.4.6 修复说明](../BACKEND_FIXES_v0.4.6.md)** - 后端问题修复
- **[发布历史归档](../archive/completion-reports/)** - 历史发布记录

---

## 🔧 项目管理

### 📊 项目状态

- **[项目运行状态](../PROJECT_RUNNING_STATUS.md)** - 当前项目状态
- **[系统检查清单](../SYSTEM_CHECK_CHECKLIST.md)** - 健康检查列表
- **[完成报告](../COMPLETION_REPORT.md)** - 项目完成情况

### 📐 设计文档

- **[设计文档索引](../design/INDEX.md)** - 所有设计文档
- **[功能设计模板](../templates/FEATURE_DESIGN_TEMPLATE.md)** - 设计文档模板

### 📜 历史归档

- **[归档文档索引](../archive/INDEX.md)** - 历史文档归档
- **[版本计划归档](../archive/plans/)** - 历史版本计划
- **[完成报告归档](../archive/completion-reports/)** - 历史完成报告

---

## 🎯 按角色查找

### 👤 最终用户

<details>
<summary>点击展开</summary>

- [快速开始](../guides/startup-guide.md)
- [系统概览](../guides/business/SYSTEM_OVERVIEW.md)
- [功能说明](../guides/business/FEATURES.md)
- [常见问题](../guides/troubleshooting-black-screen.md)

</details>

### 🔧 系统管理员

<details>
<summary>点击展开</summary>

- [安装部署](../guides/CONFIGURATION_GUIDE.md)
- [API 配置](../guides/API_SETTINGS_GUIDE.md)
- [性能优化](../guides/PDF_PERFORMANCE_TUNING.md)
- [数据存储](../guides/development/DATA_STORAGE.md)
- [系统检查](../SYSTEM_CHECK_CHECKLIST.md)

</details>

### 💻 开发者

<details>
<summary>点击展开</summary>

- [环境搭建](../guides/development/SETUP_GUIDE.md)
- [系统架构](../guides/development/ARCHITECTURE.md)
- [API 开发](../guides/development/API_DEVELOPMENT.md)
- [前端开发](../guides/development/FRONTEND_DEVELOPMENT.md)
- [代码规范](../guides/development/CODE_STANDARDS.md)
- [开发工作流](../guides/development/DEVELOPMENT_WORKFLOW.md)

</details>

### 🎨 架构师

<details>
<summary>点击展开</summary>

- [系统架构](../guides/development/ARCHITECTURE.md)
- [多智能体系统](../guides/development/MULTI_AGENT_SYSTEM.md)
- [检索系统](../guides/development/RETRIEVAL_SYSTEM.md)
- [LangGraph 设计](../it_ops_langgraph_stategraph_design.md)
- [设计文档集](../design/INDEX.md)

</details>

---

## 🔍 快速查找

### 常用链接

| 类型 | 文档 | 说明 |
|------|------|------|
| 🚀 **入门** | [快速开始](../guides/startup-guide.md) | 5分钟快速体验 |
| ⚙️ **配置** | [配置指南](../guides/CONFIGURATION_GUIDE.md) | 完整配置说明 |
| 🏗️ **架构** | [系统架构](../guides/development/ARCHITECTURE.md) | 整体架构设计 |
| 🤖 **Agent** | [Agent 集成](../AGENT_INTEGRATION_GUIDE.md) | Agent 开发指南 |
| 📄 **PDF** | [PDF 处理](../features/pdf/README.md) | PDF 功能说明 |
| 🔍 **RAG** | [RAG 技术](../features/rag/README.md) | 检索增强生成 |
| 📝 **API** | [API 文档](http://127.0.0.1:8000/docs) | 在线 API 文档 |
| 🐛 **问题** | [故障排查](../guides/troubleshooting-black-screen.md) | 常见问题解决 |

### 文档类型

- 📘 **指南文档**: `docs/guides/` - 操作和配置指南
- 🎨 **设计文档**: `docs/design/` - 架构和设计决策
- ✨ **功能文档**: `docs/features/` - 功能特性说明
- 📦 **发布文档**: `docs/releases/` - 版本发布说明
- 📜 **历史文档**: `docs/archive/` - 归档参考资料

---

## 📞 获取帮助

### 🔎 查找信息

1. **使用文档搜索** - 在 GitHub 仓库中搜索关键词
2. **查看索引** - 浏览[完整索引](../INDEX.md)或[文档结构](../README.md)
3. **检查归档** - 历史问题可能在[归档文档](../archive/)中

### 💬 技术支持

- **问题反馈**: 提交 GitHub Issue
- **功能建议**: 通过 Issue 提出改进建议
- **安全问题**: 参考[安全政策](../../SECURITY.md)私密报告

### 🤝 参与贡献

- **文档贡献**: 参考[文档模板](../templates/)编写
- **代码贡献**: 遵循[开发工作流](../guides/development/DEVELOPMENT_WORKFLOW.md)
- **问题修复**: 查看[贡献指南](../../CONTRIBUTING.md)

---

## 📈 文档统计

| 指标 | 数量 | 说明 |
|------|------|------|
| 📄 **总文档数** | 184+ | 包含所有 Markdown 文档 |
| 📘 **指南文档** | 25+ | 用户和开发指南 |
| 🎨 **设计文档** | 15+ | 架构和功能设计 |
| 📦 **发布说明** | 20+ | 版本发布记录 |
| 📜 **归档文档** | 120+ | 历史参考资料 |

**最后更新**: 2026-06-23  
**文档版本**: 3.0  
**项目版本**: v0.5.0

---

## 🌐 其他语言

- [English Documentation](../README.md) - English version
- [中文文档](./INDEX.md) - 当前页面

---

<div align="center">

**QueryMind (智询)** - 企业级智能问答引擎

[GitHub 仓库](https://github.com/pocheang/querymind) · [问题反馈](https://github.com/pocheang/querymind/issues) · [更新日志](../../CHANGELOG.md)

</div>
