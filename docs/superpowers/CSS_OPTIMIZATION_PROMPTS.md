# CSS 优化项目 - 实施计划提示词

本文档包含 CSS 优化项目 4 个 Phase 的完整提示词，用于在新聊天框中创建详细的实施计划。

**设计文档**: `docs/superpowers/specs/2026-05-01-css-optimization-design.md`

---

## 📋 Phase 1: 文件拆分

**目标**: 将超过 300 行的文件拆分为功能模块  
**预期**: 文件数 25 → 45 个，最大文件 1257行 → 250行，可维护性 +40%

### 提示词

```
我需要为 CSS 优化项目创建 Phase 1 的详细实施计划。

设计文档：docs/superpowers/specs/2026-05-01-css-optimization-design.md

请使用 superpowers:writing-plans skill 创建 Phase 1（文件拆分）的实施计划。

Phase 1 目标：拆分大文件（超过 300 行）
- 拆分 dark.css (1257行) → themes/dark/ 6个文件
- 拆分 admin.css (769行) → pages/admin/ 4个文件  
- 拆分 auth.css (698行) → pages/auth/ 4个文件
- 拆分 forms.css (410行) → components/forms/ 4个文件
- 拆分 sidebar.css (430行) → components/navigation/ 3个文件
- 拆分 composer.css (407行) → features/composer/ 3个文件
- 拆分 buttons.css (364行) → components/buttons/ 3个文件
- 拆分 messages.css (283行) → features/messaging/ 3个文件
- 拆分 cards.css (276行) → components/cards/ 3个文件

要求：
- 每个任务包含完整的 CSS 代码（从原文件提取）
- 包含测试验证步骤（构建测试、视觉检查）
- 包含 Git commit 命令
- 更新 main.css 导入路径

验收标准：
- 所有文件 < 300 行
- 构建成功无错误
- 视觉回归测试通过
- 主题切换正常

计划保存到：docs/superpowers/plans/2026-05-01-css-phase1-split-files.md
```

---

## 📋 Phase 2: Critical CSS 提取

**目标**: 提取 14KB 关键样式内联到 HTML  
**预期**: 首屏加载 99KB → 40KB (-60%)，FCP ~2.5s → ~1.2s (-52%)

### 提示词

```
我需要为 CSS 优化项目创建 Phase 2 的详细实施计划。

设计文档：docs/superpowers/specs/2026-05-01-css-optimization-design.md
前置条件：Phase 1 已完成（文件已拆分）

请使用 superpowers:writing-plans skill 创建 Phase 2（Critical CSS 提取）的实施计划。

Phase 2 目标：提取 14KB 关键样式内联到 HTML
- 分析首屏渲染路径（Login/Chat 首屏）
- 提取必需样式到 core/critical.css（~150行）
  - 基础布局（flex/grid）
  - 按钮基础样式
  - 输入框基础样式
  - 首屏可见组件
- 配置 Vite 插件自动内联 Critical CSS
- 实现 preload 策略加载非关键 CSS
- 测试首屏渲染性能

要求：
- 创建 vite-plugin-critical-css.ts 插件
- 包含完整的插件代码
- 包含性能测试步骤（Lighthouse）
- 包含 Git commit 命令

验收标准：
- Critical CSS < 14KB
- FCP < 1s
- LCP < 2.5s
- 无样式闪烁（FOUC）

预期效果：
- 首屏加载：99KB → 40KB (-60%)
- FCP：~2.5s → ~1.2s (-52%)

计划保存到：docs/superpowers/plans/2026-05-01-css-phase2-critical.md
```

---

## 📋 Phase 3: 路由级代码分割

**目标**: 按路由懒加载 CSS  
**预期**: 首屏加载 40KB → 25KB (-38%)，路由切换按需加载 15-25KB

### 提示词

```
我需要为 CSS 优化项目创建 Phase 3 的详细实施计划。

设计文档：docs/superpowers/specs/2026-05-01-css-optimization-design.md
前置条件：Phase 1-2 已完成（文件已拆分，Critical CSS 已提取）

请使用 superpowers:writing-plans skill 创建 Phase 3（路由级代码分割）的实施计划。

Phase 3 目标：按路由懒加载 CSS
- 配置 Vite manualChunks 分割策略
  - auth-styles bundle（登录/注册页面）
  - chat-styles bundle（聊天页面）
  - admin-styles bundle（管理页面）
  - profile-styles bundle（个人资料页面）
- 在路由组件中动态导入 CSS
  - LoginPage.tsx → import auth CSS
  - ChatPage.tsx → import chat CSS
  - AdminPage.tsx → import admin CSS
- 实现路由预加载（hover 时预加载）
- 添加加载状态处理
- 测试路由切换性能

要求：
- 修改 vite.config.ts 添加 manualChunks
- 修改路由组件添加 CSS 导入
- 包含完整的代码
- 包含性能测试步骤
- 包含 Git commit 命令

验收标准：
- 每个路由独立 CSS bundle
- 路由切换加载 < 500ms
- 无样式闪烁（FOUC）
- 缓存命中率 > 70%

预期效果：
- 首屏加载：40KB → 25KB (-38%)
- 路由切换：按需加载 15-25KB

计划保存到：docs/superpowers/plans/2026-05-01-css-phase3-route-split.md
```

---

## 📋 Phase 4: 组件级懒加载

**目标**: Modal/Dropdown 等交互组件按需加载  
**预期**: 首屏加载 25KB → 14KB (-86% vs 原始)，Lighthouse Score 95+

### 提示词

```
我需要为 CSS 优化项目创建 Phase 4 的详细实施计划。

设计文档：docs/superpowers/specs/2026-05-01-css-optimization-design.md
前置条件：Phase 1-3 已完成（文件已拆分，Critical CSS 已提取，路由已分割）

请使用 superpowers:writing-plans skill 创建 Phase 4（组件级懒加载）的实施计划。

Phase 4 目标：Modal/Dropdown 等交互组件按需加载
- 识别低频使用组件
  - Modal（对话框）
  - Dropdown（下拉菜单）
  - Tooltip（工具提示）
- 实现组件级 CSS 懒加载
  - 使用 React.lazy() 动态导入 CSS
  - 添加 Suspense 边界
- 优化加载体验（skeleton/placeholder）
- 测试交互性能

要求：
- 修改 Modal.tsx、Dropdown.tsx、Tooltip.tsx 组件
- 包含完整的组件代码
- 包含懒加载实现
- 包含性能测试步骤
- 包含 Git commit 命令

验收标准：
- 交互组件首次使用时加载
- 加载时间 < 200ms
- 用户体验流畅
- 无明显延迟感知

预期效果（最终目标）：
- 首屏加载：25KB → 14KB Critical CSS (-86% vs 原始)
- 总 CSS：99KB → 按需加载
- 交互组件：首次使用时加载 5-10KB
- FCP：~1.0s ✅
- LCP：~1.8s ✅
- Lighthouse Score：95+ ✅

计划保存到：docs/superpowers/plans/2026-05-01-css-phase4-lazy-load.md
```

---

## 📊 实施进度总览

| Phase | 目标 | 预期效果 | 状态 |
|-------|------|----------|------|
| **Phase 1** | 文件拆分 | 可维护性 +40% | ⏳ 待开始 |
| **Phase 2** | Critical CSS | 首屏 -60% | ⏳ 待开始 |
| **Phase 3** | 路由分割 | 首屏 -38% | ⏳ 待开始 |
| **Phase 4** | 组件懒加载 | 首屏 -86% | ⏳ 待开始 |

---

## 📝 使用说明

### 1. 按顺序执行

必须按照 Phase 1 → Phase 2 → Phase 3 → Phase 4 的顺序执行，因为后续 Phase 依赖前面的完成。

### 2. 每个 Phase 的工作流程

1. **复制提示词** - 从本文档复制对应 Phase 的提示词
2. **新建聊天** - 在新的聊天框中粘贴提示词
3. **生成计划** - AI 会调用 writing-plans skill 生成详细计划
4. **执行计划** - 按照生成的计划逐步实施
5. **验收测试** - 完成后进行验收测试
6. **Git 提交** - 提交代码并打 tag

### 3. Git 分支策略

每个 Phase 使用独立的 feature 分支：

```bash
# Phase 1
git checkout -b feature/css-phase1-split-files

# Phase 2
git checkout -b feature/css-phase2-critical

# Phase 3
git checkout -b feature/css-phase3-route-split

# Phase 4
git checkout -b feature/css-phase4-lazy-load
```

### 4. 版本标记

每个 Phase 完成后打 tag：

```bash
# Phase 1 完成
git tag v0.3.2.0-phase1

# Phase 2 完成
git tag v0.3.2.1-phase2

# Phase 3 完成
git tag v0.3.2.2-phase3

# Phase 4 完成
git tag v0.3.2.3-phase4
```

### 5. 回滚策略

如果某个 Phase 出现问题，可以快速回退：

```bash
# 回退到 Phase 1
git checkout v0.3.2.0-phase1

# 回退到 Phase 2
git checkout v0.3.2.1-phase2
```

---

## 🎯 最终目标

完成所有 4 个 Phase 后，预期达到：

### 性能指标
- ✅ 首屏加载：99KB → 14KB (-86%)
- ✅ FCP：2.5s → 1.0s (-60%)
- ✅ LCP：3.5s → 1.8s (-49%)
- ✅ Lighthouse Score：95+

### 代码质量
- ✅ 文件数：25 → 45 个
- ✅ 最大文件：1257行 → 250行
- ✅ 按功能组织，易于查找
- ✅ 无重复代码

### 用户体验
- ✅ 页面加载速度提升 60%
- ✅ 无样式闪烁
- ✅ 主题切换流畅
- ✅ 路由切换快速

---

## 📚 相关文档

- **设计文档**: `docs/superpowers/specs/2026-05-01-css-optimization-design.md`
- **Phase 1 计划**: `docs/superpowers/plans/2026-05-01-css-phase1-split-files.md`
- **Phase 2 计划**: `docs/superpowers/plans/2026-05-01-css-phase2-critical.md`
- **Phase 3 计划**: `docs/superpowers/plans/2026-05-01-css-phase3-route-split.md`
- **Phase 4 计划**: `docs/superpowers/plans/2026-05-01-css-phase4-lazy-load.md`

---

**创建日期**: 2026-05-02  
**项目**: Multi-Agent RAG Local - CSS 优化  
**预计周期**: 4 周
