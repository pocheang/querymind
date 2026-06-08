# 继续完成历史版本文档的提示词

## 📋 任务背景

我们正在为multi_agent_rag_local_v4项目的所有历史版本补充完整的文档，遵循新建立的代码变更管理制度。

**制度要求**:
- 每个版本必须有：计划文档(BEFORE) + 总结文档(AFTER)
- 文档命名格式：`YYYY-MM-DD-HHmm-description.md`
- 包含完整的时间记录、问题分析、解决方案、测试结果、经验教训

---

## ✅ 已完成的版本

| 版本 | 计划文档 | 总结文档 | 状态 |
|------|---------|---------|------|
| **v0.4.3** | ✅ v0.4.3-stability-fixes.md | ✅ (更新在计划中) | 已推送 |
| **v0.4.2** | ✅ 2026-05-22-v0.4.2-hardening.md | ✅ 2026-05-22-v0.4.2-summary.md | 已推送 |
| **v0.4.1** | ✅ 2026-05-20-v0.4.1-refactoring.md | ✅ 2026-05-20-v0.4.1-summary.md | 已推送 |
| **v0.4.0** | ✅ 2026-05-16-v0.4.0-major-features.md | ✅ 2026-05-16-v0.4.0-summary.md | 已推送 |

**文档位置**:
- 计划文档: `.claude/plans/`
- 总结文档: `.claude/completed/`

---

## ⏳ 待完成的版本

### v0.3.x 系列

查看现有的release notes：
```bash
ls -la docs/releases/
```

**已知的v0.3版本**:
- v0.3.1 - 有Release Notes (RELEASE_v0.3.1.md)

### 其他可能的版本

检查Git历史查找所有版本标签：
```bash
git tag -l | sort -V
```

检查CHANGELOG和VERSION文件：
```bash
cat CHANGELOG.md | grep "##"
cat VERSION
```

---

## 📝 任务要求

### 对每个版本创建两个文档

#### 1. 计划文档模板路径
`.claude/templates/change-plan-template.md`

**文件命名**:
```
.claude/plans/YYYY-MM-DD-{version}.md

示例:
.claude/plans/2026-04-15-v0.3.1-security-fixes.md
```

**必填内容**:
- 变更ID, 时间, 创建人, 类型, 优先级
- 问题描述和影响范围
- 解决方案和技术决策
- 风险评估和测试计划
- 预期效果

**注意**: 标注"事后补充"

#### 2. 总结文档模板路径
`.claude/templates/change-summary-template.md`

**文件命名**:
```
.claude/completed/YYYY-MM-DD-{version}-summary.md

示例:
.claude/completed/2026-04-15-v0.3.1-summary.md
```

**必填内容**:
- 时间记录（计划vs实际）
- 实际修改的文件和Git提交
- 测试结果
- 遇到的问题
- 经验教训

---

## 🔍 信息来源

### 1. Release Notes
```bash
# 查看现有的release notes
cat docs/releases/RELEASE_v0.3.1.md
cat docs/releases/RELEASE_NOTES_v0.4.0.md
```

### 2. Git提交历史
```bash
# 查看特定版本的提交
git log --oneline --grep="v0.3"

# 查看某个时间段的提交
git log --oneline --since="2026-03-01" --until="2026-04-30"

# 查看某个标签的详细信息
git show v0.3.1
```

### 3. CHANGELOG
```bash
cat CHANGELOG.md
```

### 4. 代码diff
```bash
# 对比两个版本的差异
git diff v0.3.0..v0.3.1 --stat
```

---

## 📋 详细工作流程

### Step 1: 识别所有需要补充文档的版本

```bash
# 1. 查看所有Git标签
git tag -l | sort -V

# 2. 查看现有的release notes
ls -la docs/releases/

# 3. 查看CHANGELOG中记录的版本
cat CHANGELOG.md | grep "^##"

# 4. 列出需要补充的版本清单
```

### Step 2: 收集每个版本的信息

对于每个版本（以v0.3.1为例）:

```bash
# 1. 查看release notes
cat docs/releases/RELEASE_v0.3.1.md

# 2. 查看Git提交
git log --oneline v0.3.0..v0.3.1

# 3. 查看代码变更统计
git diff v0.3.0..v0.3.1 --stat

# 4. 查看标签信息
git show v0.3.1
```

### Step 3: 创建计划文档

```bash
# 1. 复制模板
cp .claude/templates/change-plan-template.md \
   .claude/plans/2026-XX-XX-v0.3.1-description.md

# 2. 填写内容（基于收集的信息）
# 3. 提交
git add .claude/plans/2026-XX-XX-v0.3.1-description.md
git commit -m "plan: add retrospective plan for v0.3.1"
```

### Step 4: 创建总结文档

```bash
# 1. 复制模板
cp .claude/templates/change-summary-template.md \
   .claude/completed/2026-XX-XX-v0.3.1-summary.md

# 2. 填写内容
# 3. 提交
git add .claude/completed/2026-XX-XX-v0.3.1-summary.md
git commit -m "docs: add retrospective summary for v0.3.1"
```

### Step 5: 推送到GitHub

```bash
git push origin main
```

---

## 📊 参考已完成的v0.4.x文档

### 参考v0.4.2的结构（推荐）

**计划文档**: `.claude/plans/2026-05-22-v0.4.2-hardening.md`
- 清晰的5个commit拆解
- 详细的问题分析
- 完整的解决方案
- 风险评估和缓解措施

**总结文档**: `.claude/completed/2026-05-22-v0.4.2-summary.md`
- 时间记录对比
- 每个commit的详细说明
- 遇到的问题和解决方案
- 经验教训

### 参考v0.4.0的结构（Major Release）

**计划文档**: `.claude/plans/2026-05-16-v0.4.0-major-features.md`
- 6个主要模块的设计
- 技术决策说明
- 预期效果量化

**总结文档**: `.claude/completed/2026-05-16-v0.4.0-summary.md`
- 每个模块的完成情况
- 量化指标对比
- 详细的问题记录

---

## 🎯 质量标准

### 计划文档要求
- [ ] 标注"事后补充"
- [ ] 问题描述清晰
- [ ] 解决方案完整
- [ ] 包含技术决策理由
- [ ] 有风险评估
- [ ] 有测试计划

### 总结文档要求
- [ ] 时间记录完整
- [ ] Git提交列表
- [ ] 测试结果
- [ ] 问题和解决方案
- [ ] 经验教训
- [ ] 与计划的偏差分析

---

## 💡 注意事项

1. **日期推测**: 如果不确定确切日期，基于Git提交时间推测
2. **事后补充标注**: 所有文档都要标注"这是事后补充的计划文档"
3. **内容真实性**: 基于实际的Git提交和Release Notes，不要编造
4. **保持一致性**: 参考已完成的v0.4.x文档的格式和详细程度
5. **提交规范**: 遵循Git commit message规范

---

## 🚀 开始提示词

**复制以下内容到新的聊天框**:

---

你好！我需要继续完成multi_agent_rag_local_v4项目的历史版本文档补充工作。

**当前状态**:
- ✅ 已完成v0.4.0、v0.4.1、v0.4.2、v0.4.3的完整文档
- ⏳ 需要补充v0.3.x及其他历史版本的文档

**任务要求**:
为每个历史版本创建：
1. 计划文档（BEFORE）- 存放在`.claude/plans/`
2. 总结文档（AFTER）- 存放在`.claude/completed/`

**参考资料**:
- 已完成的文档在`.claude/plans/`和`.claude/completed/`
- 文档模板在`.claude/templates/`
- Release notes在`docs/releases/`
- 详细要求见`.claude/CONTINUE_TASK.md`

**请帮我**:
1. 首先识别所有需要补充文档的版本（运行`git tag -l | sort -V`）
2. 然后为每个版本创建完整的计划和总结文档
3. 参考v0.4.2的文档结构（详细但精炼）
4. 所有文档标注"事后补充"
5. 基于实际的Git提交和Release Notes编写
6. 每完成一个版本就提交并推送到GitHub

开始吧！

---

**文件路径**: `.claude/CONTINUE_TASK.md`  
**创建时间**: 2026-06-02 18:05:00  
**目的**: 在新聊天框中继续完成历史版本文档补充任务
