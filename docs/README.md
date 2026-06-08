# 多智能体RAG系统文档

**项目版本**: v0.4.4  
**文档更新**: 2026-06-08  
**状态**: 活跃维护

---

## 📚 快速导航

### 🚀 快速开始
- [项目README](../README.md) - 项目概述、安装和使用
- [CHANGELOG](../CHANGELOG.md) - 版本更新日志
- [配置指南](guides/CONFIGURATION_GUIDE.md) - 系统配置指南

### 📖 操作指南
- [API配置指南](guides/API_SETTINGS_GUIDE.md) - API和模型配置
- [性能优化指南](guides/PERFORMANCE_OPTIMIZATION.md) - 性能调优
- [PDF性能调优](guides/PDF_PERFORMANCE_TUNING.md) - PDF处理优化
- [PDF测试指南](guides/PDF_TESTING_GUIDE.md) - PDF测试流程
- [Claude技能指南](guides/claude-skills-guide.md) - Claude Code技能使用

### ✨ 功能文档
- [RAG功能](features/rag/) - 检索增强生成功能
- [Agent系统](features/agents/) - 多智能体编排
- [PDF处理](features/pdf/) - PDF文档处理
- [OCR集成](features/ocr/) - 光学字符识别

### 🔧 项目管理
- [项目分析报告](project/PROJECT_ANALYSIS.md) - 完整项目分析
- [代码变更政策](project/CODE_CHANGE_POLICY.md) - 代码变更规范
- [文档政策](project/policies/DOCUMENTATION_POLICY.md) - 文档管理规范
- [安全政策](project/SECURITY.md) - 安全披露政策

### 🚀 版本发布
- [v0.4.4 实现指南](releases/v0.4.4-implementation-guide.md)
- [v0.4.4 快速参考](releases/v0.4.4-quick-reference.md)
- [历史发布说明](releases/) - 所有版本发布说明

---

## 📁 文档组织

我们的文档按照以下结构组织：

```
docs/
├── guides/          # 📖 操作和配置指南
├── features/        # ✨ 功能文档和说明
├── project/         # 🔧 项目管理和政策
├── releases/        # 🚀 版本发布说明
├── design/          # 🎨 架构和设计文档
├── history/         # 📜 版本和优化历史
├── templates/       # 📝 文档模板
├── visualizations/  # 📊 项目可视化
├── images/          # 🖼️ 图片和图表
└── archive/         # 📦 历史归档
```

详细的结构说明请参考 [STRUCTURE.md](STRUCTURE.md)

---

## 🔍 查找文档

### 按主题查找
- **完整索引**: [INDEX.md](INDEX.md) - 所有文档的完整列表
- **项目文档**: [project/INDEX.md](project/INDEX.md)
- **设计文档**: [design/INDEX.md](design/INDEX.md)
- **归档文档**: [archive/INDEX.md](archive/INDEX.md)

### 按角色查找

#### 👤 用户/运维人员
- [配置指南](guides/CONFIGURATION_GUIDE.md)
- [API配置](guides/API_SETTINGS_GUIDE.md)
- [性能优化](guides/PERFORMANCE_OPTIMIZATION.md)
- [功能文档](features/)

#### 💻 开发者
- [项目分析](project/PROJECT_ANALYSIS.md)
- [架构设计](design/)
- [开发指南](guides/development/)
- [代码变更政策](project/CODE_CHANGE_POLICY.md)

#### 🔧 维护者
- [项目工作流](project/project-workflow-and-standards.md)
- [维护建议](project/MAINTENANCE_RECOMMENDATIONS.md)
- [Claude文件夹维护](project/CLAUDE_FOLDER_CLEANUP_GUIDE.md)
- [生产就绪检查](project/production_readiness_checklist.md)

---

## 📝 文档贡献

### 添加新文档
1. 确定文档类型（用户、开发、管理）
2. 选择合适的目录
3. 使用 [文档模板](templates/)
4. 更新相应的索引文件

### 更新现有文档
1. 更新文档内容
2. 修改文档顶部的更新日期
3. 如有重大变更，更新CHANGELOG

### 归档旧文档
1. 移动到 `archive/` 相应子目录
2. 添加日期前缀 `YYYY-MM-DD-`
3. 更新索引，移除主索引中的链接
4. 在原位置添加重定向（如需要）

详见 [文档政策](project/policies/DOCUMENTATION_POLICY.md)

---

## 🎯 重要文档

### 核心政策
- [文档政策](project/policies/DOCUMENTATION_POLICY.md)
- [代码变更政策](project/CODE_CHANGE_POLICY.md)
- [安全政策](project/SECURITY.md)
- [发布矩阵](project/PUBLICATION_MATRIX.md)

### 关键指南
- [配置指南](guides/CONFIGURATION_GUIDE.md)
- [性能优化](guides/PERFORMANCE_OPTIMIZATION.md)
- [项目工作流](project/project-workflow-and-standards.md)

### 技术文档
- [高级RAG技术](features/rag/advanced_rag_techniques.md)
- [中文NLP优化](features/rag/chinese_nlp_optimization.md)
- [Agent执行追踪](features/agents/agent_execution_tracking.md)
- [Docling集成](features/pdf/docling_integration.md)

---

## 📊 项目可视化

我们提供多种项目可视化工具，帮助理解项目结构：

- [项目仪表板](visualizations/dashboard.html) - 交互式项目概览
- [结构可视化](visualizations/structure_visualization.html) - 目录结构图
- [可视化指南](visualizations/GUIDE.md) - 如何使用可视化工具

---

## 🔗 外部资源

### 运行时文档
- **API文档**: http://127.0.0.1:8000/docs（后端运行时）
- **前端界面**: http://127.0.0.1:5173/app（前端运行时）

### 相关链接
- [GitHub仓库](https://github.com/your-org/multi-agent-rag) _(如适用)_
- [问题追踪](project/issues/) - 当前问题和解决方案

---

## 📞 获取帮助

### 文档问题
- 检查 [INDEX.md](INDEX.md) 寻找相关文档
- 查看 [归档文档](archive/) 了解历史背景
- 参考 [模板](templates/) 创建新文档

### 技术问题
- 查阅相应的功能文档 [features/](features/)
- 检查 [问题追踪](project/issues/)
- 参考 [历史发布说明](releases/)

### 贡献指南
- 遵循 [文档政策](project/policies/DOCUMENTATION_POLICY.md)
- 使用 [文档模板](templates/)
- 查看 [项目工作流](project/project-workflow-and-standards.md)

---

## 📈 文档统计

- **总文档数**: 184+ 篇
- **活跃维护**: guides/, features/, project/
- **归档文档**: archive/（仅供参考）
- **最后整理**: 2026-06-08

---

**维护者**: 项目团队  
**文档版本**: 2.0  
**下次审查**: 每月或主要版本发布时
