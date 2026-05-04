# CSS重构执行指南 - 分阶段执行手册

**项目:** Multi-Agent RAG Local v4  
**生成时间:** 2026-05-01  
**总阶段数:** 9个阶段  
**预计总时长:** 2-3周

---

## 📋 快速导航

- [阶段0：CSS审计](#阶段0css审计) ⬅️ **从这里开始**
- [阶段1：准备工作](#阶段1准备工作)
- [阶段2：核心层迁移](#阶段2核心层迁移)
- [阶段3：主题层迁移](#阶段3主题层迁移)
- [阶段4：组件层迁移](#阶段4组件层迁移)
- [阶段5：页面层迁移](#阶段5页面层迁移)
- [阶段6：功能模块层迁移](#阶段6功能模块层迁移)
- [阶段7：创建特殊文件](#阶段7创建特殊文件)
- [阶段8：清理和优化](#阶段8清理和优化)

---

## 阶段0：CSS审计

**目标:** 获取准确数据，识别优化机会  
**预计时长:** 2-3小时  
**风险等级:** 🟢 低（只读操作）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段0：CSS审计。

请帮我完成以下任务：

1. 安装并运行 PurgeCSS 检测未使用的CSS样式
   - 分析 frontend/src/styles/ 目录
   - 生成未使用样式报告

2. 安装并运行 csscss 识别重复的CSS规则
   - 检查所有CSS文件
   - 生成重复代码报告

3. 分析CSS特异性
   - 识别高特异性选择器
   - 找出 !important 使用情况

4. 生成详细的迁移映射表
   - 每个选择器的来源文件
   - 每个选择器的目标文件
   - 暗色模式样式清单

5. 测量当前性能基线
   - CSS文件总大小
   - 首屏加载时间
   - 生成性能报告

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md
```

### ✅ 完成标准

- [ ] PurgeCSS 报告生成
- [ ] csscss 重复代码报告生成
- [ ] CSS特异性分析完成
- [ ] 迁移映射表创建
- [ ] 性能基线报告生成

### 📊 预期输出

- `frontend/css-audit-report.md` - 审计总报告
- `frontend/css-unused-styles.json` - 未使用样式列表
- `frontend/css-duplicates.txt` - 重复代码列表
- `frontend/css-migration-map.md` - 迁移映射表
- `frontend/css-performance-baseline.json` - 性能基线数据

---

## 阶段1：准备工作

**目标:** 创建目录结构，备份文件  
**预计时长:** 30分钟  
**风险等级:** 🟢 低（可回滚）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段1：准备工作。

请帮我完成以下任务：

1. 创建新的目录结构
   mkdir -p frontend/src/styles/{core,themes,components,pages,features}

2. 备份现有CSS文件
   - 复制 frontend/src/styles 到 frontend/src/styles.backup
   - 创建 Git 标签 css-refactor-start

3. 创建迁移检查清单
   - 基于阶段0的审计结果
   - 标记高风险区域

4. 验证开发环境
   - 确认 npm run dev 正常运行
   - 确认热重载工作正常

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md
前置条件：阶段0已完成
```

### ✅ 完成标准

- [ ] 目录结构创建完成
- [ ] 备份文件创建
- [ ] Git 标签创建
- [ ] 迁移检查清单创建
- [ ] 开发环境验证通过

---

## 阶段2：核心层迁移

**目标:** 创建 tokens, reset, utilities  
**预计时长:** 2-3小时  
**风险等级:** 🟡 中（影响全局）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段2：核心层迁移。

请帮我完成以下任务：

1. 创建 core/tokens.css
   - 从 base.css 提取所有 CSS 变量定义
   - 包含：颜色、间距、字体、圆角、阴影、z-index、过渡时长
   - 保持变量名不变

2. 创建 core/reset.css
   - 从 base.css 提取全局重置样式
   - 包含：box-sizing, html/body, h1-h6, p, a, button, input

3. 创建 core/utilities.css
   - 从 base.css 提取工具类
   - 包含：.text-*, .bg-*, .rounded-*, .shadow-*

4. 测试核心层加载
   - 临时在 App.tsx 中导入核心层文件
   - 验证变量可访问性
   - 检查重置样式生效

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md
前置条件：阶段1已完成
```

### ✅ 完成标准

- [ ] core/tokens.css 创建并包含所有变量
- [ ] core/reset.css 创建并包含重置样式
- [ ] core/utilities.css 创建并包含工具类
- [ ] 核心层测试通过
- [ ] 无控制台错误

---

## 阶段3：主题层迁移

**目标:** 集中所有暗色模式样式  
**预计时长:** 3-4小时  
**风险等级:** 🟡 中（影响主题切换）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段3：主题层迁移。

请帮我完成以下任务：

1. 创建 themes/dark.css
   - 从 base.css 提取 :root[data-theme="dark"] 变量
   - 从 pages.css 提取所有暗色模式样式
   - 从 components.css 提取暗色模式样式
   - 从 admin.css 提取暗色模式样式
   - 从 sidebar.css 提取暗色模式样式
   - 从 profile.css 提取暗色模式样式
   - 从 chat-workbench.css 提取暗色模式样式
   - 从 chat-console.css 提取暗色模式样式

2. 按组件分组组织
   - 变量覆盖放在最前面
   - 按组件分组（topbar, sidebar, bubble, admin-shell等）
   - 添加清晰的注释分隔

3. 测试主题切换
   - 浅色主题完整性
   - 暗色主题完整性
   - 切换无闪烁

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md
前置条件：阶段2已完成
```

### ✅ 完成标准

- [ ] themes/dark.css 创建
- [ ] 所有暗色模式样式已迁移
- [ ] 按组件分组组织
- [ ] 主题切换测试通过
- [ ] 无视觉回归

---

## 阶段4：组件层迁移

**目标:** 迁移所有可复用组件  
**预计时长:** 6-8小时  
**风险等级:** 🟡 中（影响多个页面）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段4：组件层迁移。

请按以下优先级顺序完成：

**优先级1：基础组件（先做这些）**
1. components/buttons.css
   - 合并 components.css 中的按钮样式
   - 合并 components/ui/Button.css (117行)
   - 合并增强层中的按钮优化

2. components/forms.css
   - 合并 components.css 中的表单样式
   - 合并 components/ui/Input.css (118行)
   - 合并 precision-adjustments.css 中的 Toggle 开关 (402行)

3. components/cards.css
   - 合并 components.css 中的卡片样式
   - 合并 components/ui/Card.css (76行)
   - 合并 final-polish.css 中的 Agent 卡片优化

测试基础组件后，再继续优先级2和3。

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md 第3.3节
前置条件：阶段3已完成
```

### ✅ 完成标准

- [ ] 12个组件文件全部创建
- [ ] 增强层代码已合并
- [ ] 每个组件测试通过
- [ ] 无样式冲突
- [ ] 无视觉回归

---

## 阶段5：页面层迁移

**目标:** 拆分 pages.css 到各个页面  
**预计时长:** 3-4小时  
**风险等级:** 🟢 低（页面独立）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段5：页面层迁移。

请帮我完成以下任务：

1. 拆分 pages.css 到各个页面文件
   - pages/auth.css - 认证页面（登录、注册、忘记密码）
   - pages/chat.css - 聊天页面布局
   - pages/admin.css - 从 admin.css 迁移
   - pages/profile.css - 从 profile.css 迁移

2. 保持页面特定样式独立
   - 不要包含可复用组件样式
   - 只包含页面特定的布局和样式

3. 测试各个页面
   - 登录页面
   - 注册页面
   - 聊天页面
   - 管理后台
   - 用户资料页

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md 第3.5节
前置条件：阶段4已完成
```

### ✅ 完成标准

- [ ] 4个页面文件全部创建
- [ ] pages.css 已完全拆分
- [ ] 每个页面测试通过
- [ ] 无布局破碎

---

## 阶段6：功能模块层迁移

**目标:** 迁移复杂功能模块  
**预计时长:** 4-5小时  
**风险等级:** 🟡 中（复杂交互）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段6：功能模块层迁移。

请帮我完成以下任务：

1. features/chat-messages.css
   - 从 pages.css 提取消息气泡基础
   - 合并 modern-ui-enhancements.css 中的消息优化 (704行)

2. features/chat-composer.css
   - 从 pages.css 提取输入框基础
   - 合并 final-polish.css 中的输入框优化 (511行)

3. features/chat-options.css
   - 从 pages.css 提取选项栏

4. features/api-settings.css
   - 从 components/ApiSettings.css 迁移 (397行)

5. features/user-menu.css
   - 从 pages.css 提取用户菜单

6. features/process-timeline.css
   - 从 pages.css 提取流程时间线

7. features/chat-workbench.css
   - 保留原文件，只提取暗色模式到 themes/dark.css

8. features/chat-console.css
   - 保留原文件，只提取暗色模式到 themes/dark.css

测试所有功能模块的交互。

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md 第3.6节
前置条件：阶段5已完成
```

### ✅ 完成标准

- [ ] 8个功能模块文件全部创建
- [ ] 增强层代码已合并
- [ ] 所有交互功能正常
- [ ] 无功能回归

---

## 阶段7：创建特殊文件

**目标:** 创建 overrides.css, critical.css, main.css  
**预计时长:** 2-3小时  
**风险等级:** 🟢 低

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段7：创建特殊文件。

请帮我完成以下任务：

1. 创建 overrides.css
   - 收集增强层中未合并的临时调整（~10%）
   - 添加管理规则注释
   - 每个覆盖必须有 TODO 注释

2. 生成 critical.css
   - 安装 critical 工具
   - 提取首屏关键CSS
   - 目标大小 < 14KB

3. 创建 main.css
   - 按正确顺序导入所有模块
   - 添加清晰的注释分组
   - overrides.css 最后导入

4. 更新 App.tsx 或主入口文件
   - 只导入 main.css
   - 移除旧的CSS导入

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md 第3.7-3.8节
前置条件：阶段6已完成
```

### ✅ 完成标准

- [ ] overrides.css 创建
- [ ] critical.css 生成
- [ ] main.css 创建
- [ ] 主入口文件更新
- [ ] 所有样式正常加载

---

## 阶段8：清理和优化

**目标:** 删除旧文件，全面测试，性能优化  
**预计时长:** 4-5小时  
**风险等级:** 🟡 中（最终验证）

### 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段8：清理和优化。

请帮我完成以下任务：

1. 删除旧文件
   - 移动旧CSS文件到 styles.backup/ 而不是直接删除
   - 保留备份以便回滚

2. 全面测试（使用测试检查清单）
   - 功能测试（所有页面、主题切换、响应式、交互）
   - 视觉测试（浅色/暗色主题、各断点、无闪烁）
   - 回归测试（截图对比、特异性检查、变量继承）
   - 性能测试（文件大小、加载速度、重复率）
   - 兼容性测试（Chrome/Firefox/Safari）
   - 可访问性测试（对比度、焦点状态）

3. 性能优化
   - 运行 cssnano 压缩CSS
   - 运行 PurgeCSS 移除未使用样式
   - 优化选择器特异性

4. 生成对比报告
   - 对比优化前后的指标
   - 验证预期收益

5. 文档更新
   - 更新 README
   - 添加样式指南
   - 记录文件结构

参考文档：frontend/CSS_OPTIMIZATION_PLAN.md 第七节（测试检查清单）
前置条件：阶段7已完成
```

### ✅ 完成标准

- [ ] 旧文件已备份
- [ ] 所有测试通过
- [ ] 性能优化完成
- [ ] 对比报告生成
- [ ] 文档更新完成
- [ ] 准备合并到主分支

---

## 📊 进度跟踪

| 阶段 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| 阶段0：CSS审计 | ✅ 已完成 | 2026-05-01 | 生成了审计报告、迁移映射表和性能基线 |
| 阶段1：准备工作 | ✅ 已完成 | 2026-05-01 | 创建目录结构、备份文件、Git标签 |
| 阶段2：核心层迁移 | ✅ 已完成 | 2026-05-01 | 创建tokens.css, reset.css, utilities.css |
| 阶段3：主题层迁移 | ✅ 已完成 | 2026-05-01 | 提取197个暗色模式规则到dark.css (35.69 KB) |
| 阶段4：组件层迁移 | ⬜ 未开始 | - | - |
| 阶段5：页面层迁移 | ⬜ 未开始 | - | - |
| 阶段6：功能模块层迁移 | ⬜ 未开始 | - | - |
| 阶段7：创建特殊文件 | ⬜ 未开始 | - | - |
| 阶段8：清理和优化 | ⬜ 未开始 | - | - |

---

## 🚨 回滚计划

如果任何阶段出现问题：

```bash
# 回滚到重构开始前
git reset --hard css-refactor-start

# 或恢复备份
rm -rf frontend/src/styles
cp -r frontend/src/styles.backup frontend/src/styles
```

---

## 📞 需要帮助？

每个阶段遇到问题时，在新聊天框中提供：
1. 当前阶段编号
2. 具体问题描述
3. 错误信息（如有）
4. 已完成的步骤

---

**祝重构顺利！** 🚀
