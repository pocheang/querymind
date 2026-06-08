# .claude 文件夹整理和清理指南

**日期**: 2026-06-08  
**状态**: ✅ 完成主要整理，提供维护建议

---

## 📁 当前 .claude 文件夹状态

### 目录结构
```
.claude/
├── skills/                     # 自定义Claude Code技能
├── worktrees/                  # Git工作树（3个活跃）
│   ├── advanced-rag-techniques/
│   ├── agent-execution-visualization/
│   └── chinese-nlp-optimization/
├── settings.json               # Claude Code配置
└── settings.local.json         # 本地配置
```

### 统计信息
- **Worktrees数量**: 3个（18MB）
- **配置文件**: 2个
- **Skills**: 1个自定义skill

---

## 🎯 已完成的整理

### 1. 文档迁移（完成）
✅ 所有completed文件 → docs/archive/completion-reports/  
✅ 所有plans文件 → docs/archive/plans/  
✅ 技能指南 → docs/guides/claude-skills-guide.md  
✅ 模板文件 → docs/templates/  
✅ 项目政策 → docs/project/policies/  
✅ 工作流文档 → docs/project/

### 2. 目录清理（完成）
✅ 删除空的 completed/ 目录  
✅ 删除空的 plans/ 目录  
✅ 删除空的 memory/ 目录  
✅ 删除空的 templates/ 目录  

### 3. 重复文件清理（完成）
✅ 移除worktrees中的SKILLS_GUIDE.md副本  

---

## 🔧 Worktrees 管理

### 当前活跃的Worktrees

#### 1. advanced-rag-techniques
- **分支**: worktree-advanced-rag-techniques
- **提交**: b6ab21e
- **用途**: 高级RAG技术开发

#### 2. agent-execution-visualization  
- **分支**: worktree-agent-execution-visualization
- **提交**: 713b677
- **用途**: Agent执行可视化

#### 3. chinese-nlp-optimization
- **分支**: worktree-chinese-nlp-optimization
- **提交**: 7024aba
- **用途**: 中文NLP优化

### Worktree 维护建议

#### 如果功能已合并到主分支
```bash
# 1. 确认功能已合并
git log main --oneline | grep "feature-name"

# 2. 删除worktree
git worktree remove .claude/worktrees/worktree-name

# 3. 删除远程分支（如果存在）
git branch -d worktree-branch-name
git push origin --delete worktree-branch-name

# 4. 清理引用
git worktree prune
```

#### 如果需要保留worktree
保留worktree如果：
- 功能正在开发中
- 需要独立测试环境
- 计划继续在该分支工作

---

## 📋 清理检查清单

### 立即可以清理的内容

#### ✅ 已完成
- [x] completed/ 目录（已迁移到docs/）
- [x] plans/ 目录（已迁移到docs/）
- [x] memory/ 目录（已迁移到docs/）
- [x] templates/ 目录（已迁移到docs/）
- [x] 根目录的 SKILLS_GUIDE.md（已迁移）
- [x] 其他根目录文档（已迁移）
- [x] worktrees中的重复SKILLS_GUIDE.md

#### ⏳ 需要确认后清理
- [ ] worktrees/advanced-rag-techniques/（如果已合并）
- [ ] worktrees/agent-execution-visualization/（如果已合并）
- [ ] worktrees/chinese-nlp-optimization/（如果已合并）

### 检查Worktree是否可以删除

```bash
# 检查各个worktree的状态
cd .claude/worktrees/advanced-rag-techniques
git log --oneline -5
git diff main

# 如果没有未合并的重要更改，可以删除
```

---

## 🎯 .claude 文件夹最佳实践

### 应该放在 .claude/ 的内容
✅ **skills/** - 自定义Claude Code技能  
✅ **settings.json** - Claude Code配置  
✅ **settings.local.json** - 本地配置  
✅ **worktrees/** - 活跃的Git工作树  

### 不应该放在 .claude/ 的内容
❌ 项目文档（应在 docs/）  
❌ 完成报告（应在 docs/archive/completion-reports/）  
❌ 计划文档（应在 docs/archive/plans/）  
❌ 模板文件（应在 docs/templates/）  
❌ 项目政策（应在 docs/project/policies/）  

---

## 📊 清理效果

### 整理前
```
.claude/
├── SKILLS_GUIDE.md
├── CONTINUE_TASK.md
├── HISTORY_DOCS_PROGRESS.md
├── QUICK_REFERENCE.md
├── completed/ (30个文件)
├── plans/ (22个文件)
├── memory/ (3个文件)
├── templates/ (2个文件)
├── skills/
├── worktrees/ (包含重复文档)
└── settings.json
```

### 整理后
```
.claude/
├── skills/ (1个自定义skill)
├── worktrees/ (3个活跃工作树)
├── settings.json
└── settings.local.json
```

### 改进指标
- **文件减少**: 60+ 个 → 2 个配置文件
- **目录减少**: 删除4个文档目录
- **大小减少**: ~18MB（仅worktrees）
- **职责清晰**: 100%（仅配置和运行时）

---

## 🔄 定期维护建议

### 每月检查
```bash
# 1. 检查worktrees状态
git worktree list

# 2. 清理已删除的worktrees
git worktree prune

# 3. 检查未合并的分支
git branch --no-merged

# 4. 检查worktrees大小
du -sh .claude/worktrees/
```

### 每季度清理
```bash
# 1. 审查所有worktrees
# 2. 删除已合并的worktrees
# 3. 合并或删除旧分支
# 4. 清理Git引用
git gc --prune=now
```

---

## 🚨 注意事项

### 删除Worktree前的检查
1. ✅ 确认所有重要更改已提交
2. ✅ 确认功能已合并到主分支
3. ✅ 确认没有未推送的提交
4. ✅ 备份任何临时文件或笔记

### 安全删除流程
```bash
# 1. 检查未提交的更改
cd .claude/worktrees/worktree-name
git status

# 2. 检查未推送的提交
git log main..HEAD

# 3. 如果有重要内容，先保存
git stash
# 或
git commit -m "save work"
git push

# 4. 返回主目录
cd ../../..

# 5. 删除worktree
git worktree remove .claude/worktrees/worktree-name

# 6. 清理分支（可选）
git branch -d worktree-branch-name
```

---

## 📝 Skills 管理

### 当前Skills
```
.claude/skills/
└── rag-system-debug.skill.md
```

### 添加新Skill
1. 创建 `.skill.md` 文件在 `.claude/skills/`
2. 按照skill格式编写
3. 重启Claude Code加载新skill

### Skill文档位置
- **自定义skills**: `.claude/skills/`（运行时加载）
- **Skills文档**: `docs/project/PROJECT_SKILLS.md`（项目文档）
- **Skills指南**: `docs/guides/claude-skills-guide.md`（通用指南）

---

## 🔗 相关文档

- [docs/project/CLAUDE_FOLDER_CLEANUP.md](../../docs/project/CLAUDE_FOLDER_CLEANUP.md) - 第三阶段清理报告
- [docs/DOCUMENTATION_REORGANIZATION_COMPLETE.md](../../docs/DOCUMENTATION_REORGANIZATION_COMPLETE.md) - 完整整理报告
- [docs/project/PROJECT_SKILLS.md](../../docs/project/PROJECT_SKILLS.md) - 项目技能指南

---

## ✅ 总结

### 已完成
✅ 所有文档已迁移到 docs/  
✅ 空目录已删除  
✅ 重复文件已清理  
✅ .claude/ 职责清晰  

### 维护建议
- 定期检查worktrees状态
- 及时删除已合并的worktrees
- 保持 .claude/ 仅用于配置和运行时
- 所有项目文档放在 docs/

### 最终状态
.claude/ 文件夹现在干净、专注，仅包含：
- ✅ 配置文件（2个）
- ✅ 自定义技能（1个）
- ✅ 活跃工作树（3个，待审查）

---

**整理完成时间**: 2026-06-08  
**维护者**: 项目团队  
**下次审查**: 建议每月检查worktrees状态
