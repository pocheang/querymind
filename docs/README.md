# 多智能体RAG系统文档中心

**项目版本**: v0.4.4  
**文档更新**: 2026-06-08  
**状态**: 活跃维护

---

## 📚 快速导航

### 🚀 快速开始
- [项目README](../README.md) - 项目概述、安装和使用
- [CHANGELOG](../CHANGELOG.md) - 版本更新日志
- [配置指南](guides/CONFIGURATION_GUIDE.md) - 系统配置完整指南

### 📖 核心指南
- [API配置指南](guides/API_SETTINGS_GUIDE.md) - API和模型配置
- [性能优化指南](guides/PERFORMANCE_OPTIMIZATION.md) - 性能调优
- [PDF性能调优](guides/PDF_PERFORMANCE_TUNING.md) - PDF处理优化
- [PDF测试指南](guides/PDF_TESTING_GUIDE.md) - PDF测试流程

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
- [所有发布说明](releases/) - 历史版本发布说明

---

## 📁 文档组织结构

```
docs/
├── README.md           # 本文件 - 文档中心导航
├── INDEX.md            # 完整文档索引
├── STRUCTURE.md        # 详细的目录结构说明
│
├── guides/             # 📖 操作和配置指南
├── features/           # ✨ 功能文档和说明
├── project/            # 🔧 项目管理和政策
├── releases/           # 🚀 版本发布说明
├── design/             # 🎨 架构和设计文档
├── history/            # 📜 版本和优化历史
├── templates/          # 📝 文档模板
├── visualizations/     # 📊 项目可视化工具
├── images/             # 🖼️ 图片和图表
└── archive/            # 📦 历史归档文档
```

详细的结构说明请参考 [STRUCTURE.md](STRUCTURE.md)

---

## 🔍 按角色查找文档

### 👤 用户/运维人员
- [配置指南](guides/CONFIGURATION_GUIDE.md) - 系统配置
- [API配置](guides/API_SETTINGS_GUIDE.md) - API设置
- [性能优化](guides/PERFORMANCE_OPTIMIZATION.md) - 性能调优
- [功能文档](features/) - 各功能说明

### 💻 开发者
- [项目分析](project/PROJECT_ANALYSIS.md) - 项目概况
- [架构设计](design/) - 系统架构
- [开发指南](guides/development/) - 开发规范
- [代码变更政策](project/CODE_CHANGE_POLICY.md) - 变更流程

### 🔧 维护者
- [项目工作流](project/project-workflow-and-standards.md) - 工作流程
- [维护建议](project/MAINTENANCE_RECOMMENDATIONS.md) - 维护指南
- [Claude文件夹维护](project/CLAUDE_FOLDER_CLEANUP_GUIDE.md) - Claude配置维护
- [生产就绪检查](project/production_readiness_checklist.md) - 上线检查清单

---

## 📝 文档索引

### 完整索引
- **[INDEX.md](INDEX.md)** - 所有文档的完整列表和分类
- **[STRUCTURE.md](STRUCTURE.md)** - 文档组织结构详细说明

### 分类索引
- [项目文档索引](project/INDEX.md) - 项目管理相关文档
- [设计文档索引](design/INDEX.md) - 架构和设计文档
- [归档文档索引](archive/INDEX.md) - 历史文档归档

---

## 🎯 重要文档快速链接

### 核心政策
- [文档政策](project/policies/DOCUMENTATION_POLICY.md) - 文档管理规范
- [代码变更政策](project/CODE_CHANGE_POLICY.md) - 代码变更流程
- [安全政策](project/SECURITY.md) - 安全相关政策
- [发布矩阵](project/PUBLICATION_MATRIX.md) - 文档发布管理

### 关键指南
- [配置指南](guides/CONFIGURATION_GUIDE.md) - 完整配置说明
- [性能优化](guides/PERFORMANCE_OPTIMIZATION.md) - 性能调优方法
- [项目工作流](project/project-workflow-and-standards.md) - 开发工作流程

### 技术亮点
- [高级RAG技术](features/rag/advanced_rag_techniques.md) - 查询分解和Self-RAG
- [中文NLP优化](features/rag/chinese_nlp_optimization.md) - 中文处理优化
- [Agent执行追踪](features/agents/agent_execution_tracking.md) - 实时追踪
- [Docling集成](features/pdf/docling_integration.md) - PDF处理集成

---

## 📊 项目可视化

我们提供多种可视化工具帮助理解项目结构：

- [项目仪表板](visualizations/dashboard.html) - 交互式项目概览
- [结构可视化](visualizations/structure_visualization.html) - 目录结构图
- [可视化指南](visualizations/GUIDE.md) - 使用说明

---

## 📝 贡献文档

### 添加新文档
1. 确定文档类型（用户文档/开发文档/管理文档）
2. 选择合适的目录（参考 [STRUCTURE.md](STRUCTURE.md)）
3. 使用 [文档模板](templates/)
4. 更新相应的索引文件

### 更新现有文档
1. 修改文档内容
2. 更新文档头部的日期
3. 如有重大变更，同步更新 CHANGELOG

### 归档旧文档
1. 移动到 `archive/` 相应子目录
2. 添加日期前缀（格式：`YYYY-MM-DD-description.md`）
3. 从主索引移除，添加到归档索引
4. 必要时添加重定向说明

详见：[文档政策](project/policies/DOCUMENTATION_POLICY.md)

---

## 🔗 外部资源

### 运行时文档
- **API文档**: http://127.0.0.1:8000/docs（后端运行时可访问）
- **前端界面**: http://127.0.0.1:5173/app（前端运行时可访问）

### 相关资源
- [问题追踪](project/issues/) - 当前已知问题
- [版本历史](history/VERSION_HISTORY.md) - 版本演进记录

---

## 📞 获取帮助

### 查找信息
1. 从本文件开始，找到相关主题
2. 查阅 [INDEX.md](INDEX.md) 获取完整文档列表
3. 检查 [archive/](archive/) 了解历史背景

### 技术问题
- 查阅功能文档 [features/](features/)
- 检查 [问题追踪](project/issues/)
- 参考 [归档文档](archive/) 了解已解决的类似问题

### 贡献指南
- 遵循 [文档政策](project/policies/DOCUMENTATION_POLICY.md)
- 使用 [文档模板](templates/)
- 参考 [项目工作流](project/project-workflow-and-standards.md)

---

## 📈 文档统计

- **总文档数**: 184+ 篇
- **活跃维护**: guides/, features/, project/
- **归档文档**: archive/（仅供参考）
- **最后整理**: 2026-06-08

---

## 🔐 文档分类说明

本文档中心包含**公开文档**，适合发布到GitHub。敏感内容（安全审计、内部计划等）保存在 `internal_docs/` 目录下（.gitignore排除）。

详见：[发布矩阵](project/PUBLICATION_MATRIX.md)

---

**维护者**: 项目团队  
**文档版本**: 2.0  
**下次审查**: 每月或主要版本发布时
