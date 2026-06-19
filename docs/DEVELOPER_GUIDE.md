# 开发者指南 (Developer Guide)

本文档是 Multi-Agent Local RAG 项目的完整开发指南，涵盖从环境搭建到高级开发的所有内容。

## 文档导航

### 📚 快速开始

1. ✅ **[环境搭建指南](./guides/development/SETUP_GUIDE.md)** - 开发环境配置和依赖安装
2. ✅ **[快速启动](./guides/startup-guide.md)** - 快速运行项目的步骤
3. ✅ **[项目结构](./guides/development/PROJECT_STRUCTURE.md)** - 代码组织和目录结构详解

### 🏗️ 架构和设计

4. ✅ **[系统架构](./guides/development/ARCHITECTURE.md)** - 整体架构设计和技术选型
5. ✅ **[多智能体系统](./guides/development/MULTI_AGENT_SYSTEM.md)** - LangGraph 工作流和智能体协同
6. ✅ **[检索系统](./guides/development/RETRIEVAL_SYSTEM.md)** - 混合检索、向量搜索和 BM25
7. ✅ **[数据存储](./guides/development/DATA_STORAGE.md)** - ChromaDB、Neo4j 和 SQLite 使用

### 💻 开发实践

8. ✅ **[开发流程](./guides/development/DEVELOPMENT_WORKFLOW.md)** - Git 工作流、代码规范和 PR 流程
9. ✅ **[代码规范](./guides/development/CODE_STANDARDS.md)** - Python 和 TypeScript 编码标准
10. 🚧 **[测试指南](./guides/development/TESTING_GUIDE.md)** - 单元测试、集成测试和 E2E 测试（待创建）
11. 🚧 **[调试技巧](./guides/development/DEBUGGING.md)** - 常见问题排查和调试工具（待创建）

### 🔌 API 和集成

12. ✅ **[API 开发](./guides/development/API_DEVELOPMENT.md)** - FastAPI 路由开发和文档生成
13. ✅ **[前端开发](./guides/development/FRONTEND_DEVELOPMENT.md)** - React 组件开发和状态管理
14. 🚧 **[模型集成](./guides/development/MODEL_INTEGRATION.md)** - 添加新的 LLM 提供商（待创建）
15. 🚧 **[工具扩展](./guides/development/TOOL_EXTENSION.md)** - 开发自定义工具和智能体（待创建）

### 🚀 部署和运维

16. 🚧 **[本地部署](./guides/development/LOCAL_DEPLOYMENT.md)** - 生产环境配置（待创建）
17. ✅ **[性能优化](./guides/PERFORMANCE_OPTIMIZATION.md)** - 性能调优和监控
18. ✅ **[安全最佳实践](./project/SECURITY.md)** - 安全配置和审计

### 📖 参考文档

19. ✅ **[配置参考](./guides/development/CONFIGURATION_REFERENCE.md)** - 所有环境变量和配置选项
20. 🚧 **[API 参考](./guides/development/API_REFERENCE.md)** - 完整的 REST API 文档（待创建）
21. ✅ **[故障排查](./guides/troubleshooting-black-screen.md)** - 常见问题和解决方案

## 文档完成度

```
总进度: 11/21 (52%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░

快速开始:    3/3  (100%) ✅
架构设计:    4/4  (100%) ✅
开发实践:    2/4  (50%)  🔄
API 集成:    1/4  (25%)  🔄
部署运维:    1/3  (33%)  🔄
```

## 版本信息

- **当前版本**: v0.4.4
- **Python 版本**: 3.11+
- **Node.js 版本**: 18+
- **文档更新日期**: 2026-06-19
- **总字数**: ~95,000 字
- **代码示例**: 320+
- **已完成文档**: 12/21 (57%)

## 贡献指南

我们欢迎所有形式的贡献！在提交 PR 之前，请确保：

- ✅ 阅读并遵循[开发流程](./guides/development/DEVELOPMENT_WORKFLOW.md)
- ✅ 所有测试通过
- ✅ 代码符合[代码规范](./guides/development/CODE_STANDARDS.md)
- ✅ 更新相关文档
- ✅ 运行 CI 质量检查

## 获取帮助

- **问题反馈**: 在 GitHub Issues 中提交
- **文档问题**: 参考 [文档政策](./project/policies/DOCUMENTATION_POLICY.md)
- **快速参考**: 查看 [快速参考卡](./guides/quick-reference.md)

## 许可证

MIT License - 详见 [LICENSE](../LICENSE)

---

**Made with ❤️ by the Bronit Team**
