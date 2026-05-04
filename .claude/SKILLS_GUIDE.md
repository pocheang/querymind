# Skills 使用指南

本文档定义了所有可用 skills 的使用场景、优先级和冲突解决规则。

## 📊 Skills 分类总览

### 🔧 开发流程类（Superpowers Core）
| Skill | 触发时机 | 优先级 |
|-------|---------|--------|
| `superpowers:brainstorming` | 任何创意工作前（功能、组件、修改行为） | **必须** |
| `superpowers:writing-plans` | 有规格/需求的多步骤任务，写代码前 | 高 |
| `superpowers:executing-plans` | 执行已写好的计划（独立会话） | 高 |
| `superpowers:subagent-driven-development` | 执行计划（当前会话，可并行任务） | 高 |
| `superpowers:test-driven-development` | 实现任何功能或 bugfix，写实现代码前 | 高 |
| `superpowers:verification-before-completion` | 声称完成/修复/通过前 | **必须** |
| `superpowers:finishing-a-development-branch` | 实现完成，测试通过，需要集成决策 | 高 |

### 🐛 调试类
| Skill | 触发时机 | 优先级 | 关系 |
|-------|---------|--------|------|
| `superpowers:systematic-debugging` | 任何 bug/测试失败/异常行为 | **主流程** | 必须使用 |
| `gitnexus-debugging` | 追踪错误来源、调用链分析 | **工具** | 在 systematic-debugging Phase 1 中可选使用 |

**使用规则**：
```
遇到 bug → systematic-debugging（四阶段流程）
  └─ Phase 1（根因调查）时，可使用 gitnexus-debugging 追踪调用链
```

### 🔍 代码探索类
| Skill | 触发时机 | 优先级 | 使用场景 |
|-------|---------|--------|----------|
| `nexus-mapper` | 首次接触项目、建立知识库 | 首次 | 生成 .nexus-map/ 持久化知识库 |
| `nexus-query` | 日常开发中的精确查询 | 日常 | "谁依赖这个接口"、"影响半径" |
| `gitnexus-exploring` | 深度理解架构、执行流程 | 深度 | "认证流程如何工作"、"这个函数被谁调用" |
| `gitnexus-guide` | 了解 GitNexus 本身 | 参考 | 查询 GitNexus 工具和用法 |

**使用规则**：
```
新项目 → nexus-mapper（一次性，生成知识库）
  ↓
日常查询 → nexus-query（快速、精确）
  ↓
深度探索 → gitnexus-exploring（理解复杂流程）
```

### 🔨 重构与影响分析类
| Skill | 触发时机 | 优先级 |
|-------|---------|--------|
| `gitnexus-impact-analysis` | 修改前的安全分析、"会破坏什么" | 高 |
| `gitnexus-refactoring` | 重命名、提取、拆分、移动代码 | 高 |

### 👁️ 代码审查类
| Skill | 触发时机 | 优先级 | 关系 |
|-------|---------|--------|------|
| `superpowers:requesting-code-review` | 完成任务、实现主要功能、合并前 | **发起流程** | 主动请求审查 |
| `superpowers:receiving-code-review` | 收到审查反馈、实现建议前 | **接收流程** | 处理反馈 |
| `code-review:code-review` | 执行 PR 审查 | **执行审查** | 通用审查 |
| `security-review` | 安全审查 | **执行审查** | 安全专项 |

**使用规则**：
```
完成工作 → requesting-code-review（发起）
  ↓
审查者执行 → code-review / security-review
  ↓
收到反馈 → receiving-code-review（处理）
```

### 🎨 前端与 API 类
| Skill | 触发时机 | 优先级 |
|-------|---------|--------|
| `frontend-design` | 构建 web 组件、页面、应用 | 高 |
| `claude-api` | 构建 Claude API 应用 | 高 |

### 🔧 工具与配置类
| Skill | 触发时机 | 优先级 |
|-------|---------|--------|
| `superpowers:using-git-worktrees` | 需要隔离工作空间、执行计划前 | 高 |
| `gitnexus-cli` | 运行 GitNexus CLI 命令 | 工具 |
| `update-config` | 配置 Claude Code settings.json | 工具 |
| `keybindings-help` | 自定义键盘快捷键 | 工具 |
| `fewer-permission-prompts` | 减少权限提示 | 工具 |
| `loop` | 定期执行任务 | 工具 |
| `schedule` | 创建定时任务 | 工具 |

### 📝 元技能类
| Skill | 触发时机 | 优先级 |
|-------|---------|--------|
| `superpowers:writing-skills` | 创建/编辑 skills | 元 |
| `simplify` | 审查和优化已修改代码 | 质量 |
| `init` | 初始化 CLAUDE.md | 初始化 |

---

## 🚨 冲突解决规则

### 1. 调试场景冲突
**问题**：`systematic-debugging` vs `gitnexus-debugging`

**解决方案**：
```
systematic-debugging = 主流程（必须）
  └─ Phase 1: 根因调查
      └─ gitnexus-debugging = 可选工具（追踪调用链）
```

**示例**：
```
用户："这个 API 返回 500 错误"
→ 使用 systematic-debugging
  → Phase 1 中使用 gitnexus-debugging 追踪错误来源
  → Phase 2-4 继续 systematic-debugging 流程
```

### 2. 执行计划场景冲突
**问题**：`executing-plans` vs `subagent-driven-development`

**解决方案**：
```
大型/需要隔离 → executing-plans（独立会话 + worktree）
中小型/可并行 → subagent-driven-development（当前会话）
```

**决策树**：
```
有实现计划？
  ├─ 需要隔离环境？（大型重构、实验性功能）
  │   └─ YES → executing-plans
  └─ 任务可并行？（独立模块、无共享状态）
      └─ YES → subagent-driven-development
```

### 3. 代码探索场景重叠
**问题**：`nexus-mapper` vs `nexus-query` vs `gitnexus-exploring`

**解决方案**：
```
首次接触项目 → nexus-mapper（生成知识库）
  ↓
日常快速查询 → nexus-query（"谁依赖这个"）
  ↓
深度理解流程 → gitnexus-exploring（"认证如何工作"）
```

---

## 📋 典型工作流

### 🆕 新功能开发
```
1. superpowers:brainstorming（探索需求）
2. superpowers:writing-plans（编写计划）
3. superpowers:using-git-worktrees（隔离环境）
4. superpowers:test-driven-development（TDD 实现）
5. superpowers:verification-before-completion（验证）
6. superpowers:requesting-code-review（请求审查）
7. superpowers:finishing-a-development-branch（集成决策）
```

### 🐛 Bug 修复
```
1. superpowers:systematic-debugging（系统化调试）
   └─ Phase 1: gitnexus-debugging（可选，追踪调用链）
2. superpowers:test-driven-development（写测试）
3. 实现修复
4. superpowers:verification-before-completion（验证）
5. superpowers:requesting-code-review（请求审查）
```

### 🔨 重构任务
```
1. nexus-query / gitnexus-exploring（理解现有代码）
2. gitnexus-impact-analysis（影响分析）
3. superpowers:writing-plans（编写重构计划）
4. superpowers:using-git-worktrees（隔离环境）
5. gitnexus-refactoring（执行重构）
6. superpowers:verification-before-completion（验证）
7. superpowers:requesting-code-review（请求审查）
```

### 🆕 新项目探索
```
1. nexus-mapper（生成知识库）
2. gitnexus-exploring（理解架构）
3. nexus-query（日常查询）
```

---

## 🎯 强制规则（不可违反）

### 必须使用的 Skills
1. **superpowers:brainstorming** - 任何创意工作前
2. **superpowers:systematic-debugging** - 任何 bug/测试失败
3. **superpowers:verification-before-completion** - 声称完成前

### 禁止的行为
1. ❌ 遇到 bug 直接修复（跳过 systematic-debugging）
2. ❌ 声称"已完成"但未运行验证命令
3. ❌ 创意工作前跳过 brainstorming
4. ❌ 同时使用 executing-plans 和 subagent-driven-development

---

## 🔄 Skills 优先级矩阵

| 场景 | 主 Skill | 辅助 Skills | 禁止 Skills |
|------|---------|------------|------------|
| 新功能 | brainstorming | writing-plans, TDD | - |
| Bug 修复 | systematic-debugging | gitnexus-debugging | 直接修复 |
| 重构 | gitnexus-refactoring | impact-analysis, nexus-query | - |
| 代码审查 | requesting-code-review | code-review, security-review | - |
| 项目探索 | nexus-mapper | gitnexus-exploring, nexus-query | - |
| 执行计划（大型） | executing-plans | using-git-worktrees | subagent-driven-development |
| 执行计划（中小型） | subagent-driven-development | - | executing-plans |

---

## 📚 快速参考

### 我应该用哪个 Skill？

| 你想做什么 | 使用这个 Skill |
|-----------|---------------|
| 添加新功能 | brainstorming → writing-plans → TDD |
| 修复 bug | systematic-debugging |
| 追踪错误来源 | gitnexus-debugging（在 systematic-debugging 中） |
| 理解代码如何工作 | gitnexus-exploring |
| 查询"谁依赖这个" | nexus-query |
| 首次接触项目 | nexus-mapper |
| 重构代码 | gitnexus-refactoring |
| 检查修改影响 | gitnexus-impact-analysis |
| 请求代码审查 | requesting-code-review |
| 处理审查反馈 | receiving-code-review |
| 执行大型计划 | executing-plans |
| 执行中小型计划 | subagent-driven-development |
| 隔离工作环境 | using-git-worktrees |
| 构建前端界面 | frontend-design |
| 构建 Claude API 应用 | claude-api |
| 声称工作完成 | verification-before-completion |
| 决定如何集成 | finishing-a-development-branch |

---

## 🔧 维护说明

### 已废弃的 Skills
- ~~`superpowers:brainstorm`~~ → 使用 `superpowers:brainstorming`
- ~~`superpowers:execute-plan`~~ → 使用 `superpowers:executing-plans`
- ~~`superpowers:write-plan`~~ → 使用 `superpowers:writing-plans`

### 自定义 Skills 位置
- 官方插件：`~/.claude/plugins/cache/claude-plugins-official/`
- 自定义 skills：`~/.claude/skills/`

### 更新此文档
当添加/修改/删除 skills 时，更新此文档的相应部分。

---

**最后更新**：2026-05-01
**版本**：1.0.0
