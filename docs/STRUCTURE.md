# 文档结构说明

**更新日期**: 2026-06-08  
**状态**: 已整理

---

## 📁 目录结构

```
docs/
├── README.md                    # 文档导航和概述
├── INDEX.md                     # 完整文档索引
├── STRUCTURE.md                 # 本文件：文档结构说明
│
├── archive/                     # 📦 历史归档
│   ├── INDEX.md                # 归档索引
│   ├── completion-reports/     # 任务完成报告
│   ├── plans/                  # 历史计划文档
│   ├── internal-migration/     # 内部整理记录
│   ├── fixes/                  # 历史修复记录
│   ├── frontend/               # 前端历史文档
│   ├── investigations/         # 技术调研报告
│   ├── refactoring/            # 重构记录
│   ├── summaries/              # 历史总结
│   └── ui/                     # UI相关归档
│
├── design/                      # 🎨 设计文档
│   ├── INDEX.md                # 设计文档索引
│   └── [设计规范和架构设计]
│
├── features/                    # ✨ 功能文档
│   ├── agents/                 # Agent相关功能
│   ├── ocr/                    # OCR功能
│   ├── pdf/                    # PDF处理功能
│   └── rag/                    # RAG功能
│
├── guides/                      # 📖 操作指南
│   ├── development/            # 开发指南
│   ├── API_SETTINGS_GUIDE.md   # API配置指南
│   ├── CONFIGURATION_GUIDE.md  # 配置指南
│   ├── PERFORMANCE_OPTIMIZATION.md  # 性能优化指南
│   ├── PDF_PERFORMANCE_TUNING.md    # PDF性能调优
│   ├── PDF_TESTING_GUIDE.md         # PDF测试指南
│   └── claude-skills-guide.md       # Claude技能指南
│
├── history/                     # 📜 版本历史
│   ├── VERSION_HISTORY.md      # 版本历史
│   ├── OPTIMIZATION_HISTORY.md # 优化历史
│   └── demo_dataset_setup.md   # Demo数据集配置
│
├── images/                      # 🖼️ 图片资源
│   └── [架构图和截图]
│
├── project/                     # 🔧 项目管理
│   ├── INDEX.md                # 项目文档索引
│   ├── policies/               # 项目政策
│   │   ├── DOCUMENTATION_POLICY.md      # 文档政策
│   │   └── [其他政策文档]
│   ├── issues/                 # 问题跟踪
│   ├── CLAUDE_FOLDER_CLEANUP_GUIDE.md   # Claude文件夹维护指南
│   ├── CODE_CHANGE_POLICY.md            # 代码变更政策
│   ├── CODE_CHANGE_SUMMARY.md           # 代码变更总结
│   ├── FRONTEND_CHANGES_ANALYSIS.md     # 前端变更分析
│   ├── MAINTENANCE_RECOMMENDATIONS.md   # 维护建议
│   ├── PROJECT_ANALYSIS.md              # 项目分析报告
│   ├── PROJECT_SKILLS.md                # 项目技能
│   ├── PUBLICATION_MATRIX.md            # 发布矩阵
│   ├── SECURITY.md                      # 安全政策
│   ├── SKILLS_INSTALLATION.md           # 技能安装
│   ├── TASK_COMPLETION_REPORT.md        # 任务完成报告
│   ├── continue-task.md                 # 任务继续说明
│   ├── next-actions.md                  # 下一步行动
│   ├── production_readiness_checklist.md # 生产就绪检查清单
│   └── project-workflow-and-standards.md # 项目工作流和标准
│
├── releases/                    # 🚀 版本发布
│   ├── README.md               # 发布说明概览
│   ├── RELEASE_NOTES_v0.4.*.md # 各版本发布说明
│   ├── v0.4.4-implementation-guide.md   # v0.4.4实现指南
│   └── v0.4.4-quick-reference.md        # v0.4.4快速参考
│
├── templates/                   # 📝 文档模板
│   ├── README.md               # 模板使用说明
│   ├── change-plan-template.md # 变更计划模板
│   └── change-summary-template.md # 变更总结模板
│
└── visualizations/              # 📊 可视化
    ├── README.md               # 可视化说明
    ├── GUIDE.md                # 可视化指南
    ├── SUMMARY.md              # 可视化总结
    ├── dashboard.html          # 项目仪表板
    ├── structure_visualization.html  # 结构可视化
    ├── structure_report.txt    # 结构报告
    └── *.dot                   # GraphViz图表源文件
```

---

## 📋 文档分类

### 1. 用户文档
**目标读者**: 使用系统的开发者和用户

- **guides/** - 操作和配置指南
- **features/** - 功能说明文档
- **releases/** - 版本发布说明
- **README.md** - 项目概述

### 2. 开发文档
**目标读者**: 项目开发者和贡献者

- **design/** - 架构和设计文档
- **project/** - 项目管理和政策
- **templates/** - 文档模板
- **history/** - 版本和优化历史

### 3. 归档文档
**目标读者**: 需要查看历史的维护者

- **archive/** - 所有历史记录和过时文档

### 4. 辅助资源
**目标读者**: 所有人

- **images/** - 图片和图表
- **visualizations/** - 项目可视化工具

---

## 🎯 文档使用指南

### 查找文档
1. **从 README.md 开始** - 获取项目概览和快速链接
2. **查阅 INDEX.md** - 查找特定主题的完整索引
3. **浏览子目录 INDEX.md** - 深入特定领域

### 添加新文档
1. **确定文档类型**：用户文档、开发文档、还是归档？
2. **选择合适目录**：参考上面的分类说明
3. **更新索引**：在相应的 INDEX.md 中添加链接
4. **使用模板**：从 templates/ 复制合适的模板

### 归档旧文档
1. **保持价值**：只归档有历史价值的文档
2. **添加日期前缀**：格式为 `YYYY-MM-DD-description.md`
3. **更新索引**：从主索引移除，添加到 archive/INDEX.md
4. **保留链接**：如果其他文档引用了该文档，添加重定向说明

---

## 🔍 特殊目录说明

### archive/
**用途**: 保存历史记录，不应该删除，但也不活跃维护

- **completion-reports/** - 每个重要任务完成后的报告
- **plans/** - 历史的实现计划
- **internal-migration/** - 项目内部整理和重构记录
- **fixes/** - 历史的bug修复文档
- **investigations/** - 技术调研和问题调查

### project/
**用途**: 活跃的项目管理文档

- **policies/** - 项目政策（不轻易变更）
- **issues/** - 当前的问题跟踪
- 其他：项目分析、技能、工作流等活跃维护的管理文档

### visualizations/
**用途**: 项目可视化工具和输出

- HTML文件可以直接在浏览器中打开
- .dot文件可以用GraphViz工具渲染
- 这些文件通常由脚本自动生成

---

## ✅ 维护原则

### DO ✅
- 保持目录结构清晰
- 及时更新索引文件
- 为文档添加适当的元数据（日期、状态）
- 使用描述性的文件名
- 在归档前检查文档价值

### DON'T ❌
- 不要在多个地方重复文档
- 不要在docs根目录堆积文档
- 不要删除有价值的历史文档
- 不要跳过更新索引
- 不要混淆临时笔记和正式文档

---

## 📞 相关资源

- [文档政策](project/policies/DOCUMENTATION_POLICY.md)
- [文档模板](templates/README.md)
- [归档索引](archive/INDEX.md)
- [Claude文件夹维护指南](project/CLAUDE_FOLDER_CLEANUP_GUIDE.md)

---

**整理完成**: 2026-06-08  
**维护者**: 项目团队
