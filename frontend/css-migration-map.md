# CSS迁移映射表

**生成时间:** 2026-05-01  
**项目:** Multi-Agent RAG Local v4  
**目标架构:** 分层CSS架构

---

## 📋 迁移概览

| 源文件 | 大小 | 目标层级 | 优先级 |
|--------|------|----------|--------|
| base.css | 7.94 KB | core/, themes/ | P1 - 高 |
| components.css | 28.73 KB | components/ | P1 - 高 |
| pages.css | 35.60 KB | pages/, features/ | P2 - 中 |
| chat-workbench.css | 38.47 KB | features/ | P2 - 中 |
| chat-console.css | 14.54 KB | features/ | P2 - 中 |
| sidebar.css | 6.83 KB | components/ | P2 - 中 |
| admin.css | 5.37 KB | pages/ | P3 - 低 |
| profile.css | 6.04 KB | pages/ | P3 - 低 |
| tables.css | 1.37 KB | components/ | P3 - 低 |
| modern-ui-enhancements.css | 16.91 KB | 合并到各层 | P1 - 高 |
| final-polish.css | 12.28 KB | 合并到各层 | P1 - 高 |
| ui-polish.css | 11.63 KB | 合并到各层 | P1 - 高 |
| precision-adjustments.css | 9.89 KB | 合并到各层 | P1 - 高 |

---

## 🎯 阶段2：核心层迁移 (core/)

### core/tokens.css
**来源:** base.css  
**内容:** CSS变量定义

```css
/* 从 base.css 提取 */
:root {
  /* 颜色变量 */
  --primary: #667eea;
  --primary-dark: #5568d3;
  --success: #10b981;
  --success-light: #d1fae5;
  --danger: #ef4444;
  --danger-light: #fee2e2;
  --warning: #f59e0b;
  --warning-light: #fef3c7;
  
  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* 字体 */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", ...;
  --font-mono: "SF Mono", Monaco, "Cascadia Code", ...;
  
  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  
  /* Z-index */
  --z-dropdown: 1000;
  --z-modal: 2000;
  --z-tooltip: 3000;
  
  /* 过渡 */
  --transition-fast: 150ms;
  --transition-base: 200ms;
  --transition-slow: 300ms;
}
```

### core/reset.css
**来源:** base.css  
**内容:** 全局重置样式

```css
/* 从 base.css 提取 */
*,
*::before,
*::after {
  box-sizing: border-box;
}

html, body, #root {
  margin: 0;
  padding: 0;
  height: 100%;
}

body {
  font-family: var(--font-sans);
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
}

h1, h2, h3, h4, h5, h6 {
  margin: 0 0 1rem;
  font-weight: 600;
  line-height: 1.2;
}

p {
  margin: 0 0 1rem;
}

a {
  color: var(--primary);
  text-decoration: none;
}

button {
  font-family: inherit;
  cursor: pointer;
}

input, textarea, select {
  font-family: inherit;
}
```

### core/utilities.css
**来源:** base.css  
**内容:** 工具类

```css
/* 从 base.css 提取 */
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-muted { color: var(--text-muted); }
.text-sm { font-size: 0.875rem; }
.text-lg { font-size: 1.125rem; }

.bg-primary { background: var(--primary); }
.bg-success { background: var(--success); }
.bg-danger { background: var(--danger); }

.rounded-sm { border-radius: var(--radius-sm); }
.rounded-md { border-radius: var(--radius-md); }
.rounded-lg { border-radius: var(--radius-lg); }

.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: var(--shadow-lg); }
```

---

## 🎨 阶段3：主题层迁移 (themes/)

### themes/dark.css
**来源:** 多个文件的暗色模式样式  
**内容:** 所有 `[data-theme="dark"]` 选择器

#### 从 base.css 提取
```css
:root[data-theme="dark"] {
  --bg: #0f172a;
  --bg-secondary: #1e293b;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --border: #334155;
  /* ... 其他暗色变量 */
}
```

#### 从 pages.css 提取
- `.bubble` 暗色样式
- `.topbar` 暗色样式
- `.sidebar` 暗色样式
- 表单元素暗色样式

#### 从 components.css 提取
- 按钮暗色样式
- 卡片暗色样式
- 输入框暗色样式

#### 从其他文件提取
- admin.css 暗色样式
- profile.css 暗色样式
- chat-workbench.css 暗色样式
- chat-console.css 暗色样式

**预计行数:** ~400-500行

---

## 🧩 阶段4：组件层迁移 (components/)

### components/buttons.css
**来源:**
- components.css (按钮基础样式)
- components/ui/Button.css (117行) - 如果存在
- modern-ui-enhancements.css (按钮增强)
- final-polish.css (按钮优化)

**选择器:**
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`
- `.icon-btn`, `.link-btn`
- `.topbar-btn`, `.row-actions button`

### components/forms.css
**来源:**
- components.css (表单基础)
- components/ui/Input.css (118行) - 如果存在
- precision-adjustments.css (Toggle开关, 402行)

**选择器:**
- `input`, `textarea`, `select`
- `.form-group`, `.form-label`
- `.toggle-switch`

### components/cards.css
**来源:**
- components.css (卡片基础)
- components/ui/Card.css (76行) - 如果存在
- final-polish.css (Agent卡片优化)

**选择器:**
- `.card`, `.kpi-card`
- `.agent-card`, `.pdf-kpi-card`
- `.sidebar-kb-card`

### components/modals.css
**来源:** components.css

**选择器:**
- `.modal-overlay`, `.modal-content`
- `.modal-header`, `.modal-body`, `.modal-footer`

### components/dropdowns.css
**来源:** components.css, pages.css

**选择器:**
- `.dropdown`, `.dropdown-menu`
- `.user-menu`, `.option-menu`

### components/badges.css
**来源:** components.css, pages.css

**选择器:**
- `.badge`, `.status-badge`
- `.user-badge`, `.role-badge`

### components/avatars.css
**来源:** components.css, pages.css

**选择器:**
- `.avatar`, `.avatar-sm`, `.avatar-lg`
- `.message-role` (头像相关)

### components/tooltips.css
**来源:** components.css

**选择器:**
- `.tooltip`, `.tooltip-content`

### components/spinners.css
**来源:** components.css

**选择器:**
- `.spinner`, `.loading`
- 加载动画

### components/alerts.css
**来源:** components.css

**选择器:**
- `.alert`, `.alert-success`, `.alert-danger`

### components/tables.css
**来源:** tables.css, admin.css

**选择器:**
- `.table`, `.table-row`
- `.admin-shell .table`

### components/sidebar.css
**来源:** sidebar.css

**选择器:**
- `.sidebar`, `.sidebar-header`
- `.sidebar-nav`, `.sidebar-item`

---

## 📄 阶段5：页面层迁移 (pages/)

### pages/auth.css
**来源:** pages.css

**选择器:**
- `.auth-page`, `.auth-container`
- `.login-form`, `.register-form`
- `.forgot-password-form`

**预计行数:** ~150行

### pages/chat.css
**来源:** pages.css

**选择器:**
- `.chat-page`, `.page-shell`
- `.chat-layout`, `.chat-main`
- 页面级布局样式（不包括消息气泡等组件）

**预计行数:** ~200行

### pages/admin.css
**来源:** admin.css

**选择器:**
- `.admin-page`, `.admin-shell`
- `.admin-header`, `.admin-content`
- `.admin-field`, `.admin-section`

**预计行数:** ~200行

### pages/profile.css
**来源:** profile.css

**选择器:**
- `.profile-page`, `.profile-container`
- `.profile-header`, `.profile-section`

**预计行数:** ~300行

---

## ⚙️ 阶段6：功能模块层迁移 (features/)

### features/chat-messages.css
**来源:**
- pages.css (消息气泡基础)
- modern-ui-enhancements.css (消息优化, 704行)
- final-polish.css (消息样式优化)

**选择器:**
- `.bubble`, `.bubble.user`, `.bubble.assistant`
- `.message-content`, `.message-role`
- `.row-actions`, `.copy-btn`

**预计行数:** ~400行

### features/chat-composer.css
**来源:**
- pages.css (输入框基础)
- final-polish.css (输入框优化, 511行)
- precision-adjustments.css (输入框调整)

**选择器:**
- `.composer`, `.composer-main`
- `.composer textarea`
- `.send-btn`, `.attach-btn`

**预计行数:** ~300行

### features/chat-options.css
**来源:** pages.css

**选择器:**
- `.options-bar`, `.option-row`
- `.option-label`, `.option-value`
- `.quick-prompt-row`

**预计行数:** ~200行

### features/api-settings.css
**来源:** components/ApiSettings.css (397行)

**选择器:**
- `.api-settings`, `.api-settings-modal`
- `.provider-select`, `.model-select`

**预计行数:** ~400行

### features/user-menu.css
**来源:** pages.css

**选择器:**
- `.user-menu`, `.user-menu-dropdown`
- `.user-menu-item`

**预计行数:** ~100行

### features/process-timeline.css
**来源:** pages.css

**选择器:**
- `.process-timeline`, `.timeline-item`
- `.timeline-step`

**预计行数:** ~150行

### features/chat-workbench.css
**来源:** chat-workbench.css (保留原文件)

**操作:** 只提取暗色模式到 themes/dark.css

**预计行数:** 保持 ~2000行

### features/chat-console.css
**来源:** chat-console.css (保留原文件)

**操作:** 只提取暗色模式到 themes/dark.css

**预计行数:** 保持 ~700行

---

## 🔧 增强层文件处理

### modern-ui-enhancements.css (16.91 KB, 704行)
**处理方式:** 拆分合并

| 内容 | 目标文件 | 行数估计 |
|------|----------|----------|
| 消息气泡增强 | features/chat-messages.css | ~300 |
| 按钮增强 | components/buttons.css | ~100 |
| 卡片增强 | components/cards.css | ~100 |
| 动画增强 | core/utilities.css | ~100 |
| 其他优化 | overrides.css | ~100 |

### final-polish.css (12.28 KB, 511行)
**处理方式:** 拆分合并

| 内容 | 目标文件 | 行数估计 |
|------|----------|----------|
| 输入框优化 | features/chat-composer.css | ~200 |
| 消息样式优化 | features/chat-messages.css | ~150 |
| Agent卡片优化 | components/cards.css | ~100 |
| 其他调整 | overrides.css | ~60 |

### ui-polish.css (11.63 KB, 581行)
**处理方式:** 拆分合并

| 内容 | 目标文件 | 行数估计 |
|------|----------|----------|
| 组件优化 | 对应 components/ | ~400 |
| 暗色模式调整 | themes/dark.css | ~100 |
| 临时覆盖 | overrides.css | ~80 |

### precision-adjustments.css (9.89 KB, 402行)
**处理方式:** 拆分合并

| 内容 | 目标文件 | 行数估计 |
|------|----------|----------|
| Toggle开关 | components/forms.css | ~150 |
| 输入框调整 | features/chat-composer.css | ~100 |
| 其他精确调整 | overrides.css | ~150 |

---

## 📊 迁移统计

### 预期文件结构

```
frontend/src/styles/
├── core/
│   ├── tokens.css          (~150行)
│   ├── reset.css           (~100行)
│   └── utilities.css       (~150行)
├── themes/
│   └── dark.css            (~500行)
├── components/
│   ├── buttons.css         (~250行)
│   ├── forms.css           (~300行)
│   ├── cards.css           (~250行)
│   ├── modals.css          (~150行)
│   ├── dropdowns.css       (~100行)
│   ├── badges.css          (~80行)
│   ├── avatars.css         (~80行)
│   ├── tooltips.css        (~60行)
│   ├── spinners.css        (~60行)
│   ├── alerts.css          (~80行)
│   ├── tables.css          (~150行)
│   └── sidebar.css         (~400行)
├── pages/
│   ├── auth.css            (~150行)
│   ├── chat.css            (~200行)
│   ├── admin.css           (~200行)
│   └── profile.css         (~300行)
├── features/
│   ├── chat-messages.css   (~400行)
│   ├── chat-composer.css   (~300行)
│   ├── chat-options.css    (~200行)
│   ├── api-settings.css    (~400行)
│   ├── user-menu.css       (~100行)
│   ├── process-timeline.css (~150行)
│   ├── chat-workbench.css  (~2000行)
│   └── chat-console.css    (~700行)
├── overrides.css           (~400行)
├── critical.css            (生成)
└── main.css                (~50行, 导入文件)
```

### 代码量对比

| 指标 | 当前 | 重构后 | 变化 |
|------|------|--------|------|
| 总行数 | 9,271 | ~8,500 | -8% |
| 文件数 | 13 | 28 | +115% |
| 重复规则 | 19 | 0 | -100% |
| !important | 5 | 0 | -100% |
| 高特异性选择器 | 88 | <20 | -77% |

---

## ⚠️ 高风险区域

### 1. 暗色模式迁移
**风险:** 暗色样式分散在8个文件中  
**缓解:** 创建详细的暗色样式清单，逐个验证

### 2. 重复规则处理
**风险:** 19个重复规则需要决定保留哪个版本  
**缓解:** 优先保留增强层版本（更新）

### 3. 高特异性选择器
**风险:** 88个高特异性选择器可能导致样式冲突  
**缓解:** 重构时降低特异性，使用BEM命名

### 4. 增强层合并
**风险:** 4个增强层文件需要拆分到多个目标文件  
**缓解:** 按功能模块分组，保持代码连贯性

---

## ✅ 验证检查清单

### 每个阶段完成后验证

- [ ] 所有选择器已迁移
- [ ] 暗色模式样式完整
- [ ] 无样式冲突
- [ ] 无视觉回归
- [ ] 开发服务器正常运行
- [ ] 热重载工作正常

### 最终验证

- [ ] 所有页面渲染正常
- [ ] 主题切换无闪烁
- [ ] 响应式布局正常
- [ ] 所有交互功能正常
- [ ] 性能指标达标
- [ ] 无控制台错误

---

## 📞 问题追踪

| 问题 | 文件 | 解决方案 | 状态 |
|------|------|----------|------|
| - | - | - | - |

---

**下一步:** 开始阶段1 - 准备工作
