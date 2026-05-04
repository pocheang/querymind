# CSS重构 - 阶段4启动包

**当前状态:** 阶段0-3已完成  
**下一步:** 阶段4 - 组件层迁移  
**预计时长:** 6-8小时

---

## 📋 已完成的工作

### ✅ 阶段0：CSS审计
- 审计报告：`frontend/css-audit-report.md`
- 迁移映射表：`frontend/css-migration-map.md`
- 性能基线：`frontend/css-performance-baseline.json`

### ✅ 阶段1：准备工作
- 目录结构已创建：`src/styles/{core,themes,components,pages,features}`
- 备份已创建：`src/styles.backup/`
- Git标签已创建：`css-refactor-start`

### ✅ 阶段2：核心层迁移
- `src/styles/core/tokens.css` - CSS变量
- `src/styles/core/reset.css` - 全局重置
- `src/styles/core/utilities.css` - 工具类

### ✅ 阶段3：主题层迁移
- `src/styles/themes/dark.css` - 197个暗色模式规则 (35.69 KB)

### 📁 当前文件结构
```
frontend/src/styles/
├── core/
│   ├── tokens.css          ✅ 已创建
│   ├── reset.css           ✅ 已创建
│   └── utilities.css       ✅ 已创建
├── themes/
│   └── dark.css            ✅ 已创建 (35.69 KB)
├── components/             ⬜ 待创建 (阶段4)
├── pages/                  ⬜ 待创建 (阶段5)
├── features/               ⬜ 待创建 (阶段6)
└── [旧文件保持不变]
```

---

## 🎯 阶段4：组件层迁移

### 目标
创建12个组件文件，从现有CSS中提取可复用组件样式。

### 优先级顺序

#### 优先级1：基础组件（先做这些）

1. **components/buttons.css**
   - 来源：components.css (按钮样式)
   - 来源：modern-ui-enhancements.css (按钮增强)
   - 来源：final-polish.css (按钮优化)
   - 选择器：`.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.icon-btn`, `.link-btn`, `.topbar-btn`, `.tiny-btn`
   - 预计：~250行

2. **components/forms.css**
   - 来源：components.css (表单基础)
   - 来源：precision-adjustments.css (Toggle开关)
   - 选择器：`input`, `textarea`, `select`, `.form-group`, `.form-label`, `.toggle-switch`
   - 预计：~300行

3. **components/cards.css**
   - 来源：components.css (卡片基础)
   - 来源：final-polish.css (Agent卡片优化)
   - 选择器：`.card`, `.kpi-card`, `.agent-card`, `.pdf-kpi-card`, `.sidebar-kb-card`
   - 预计：~250行

#### 优先级2：交互组件

4. **components/modals.css**
   - 来源：components.css
   - 选择器：`.modal-overlay`, `.modal-content`, `.modal-header`, `.modal-body`, `.modal-footer`
   - 预计：~150行

5. **components/dropdowns.css**
   - 来源：components.css, pages.css
   - 选择器：`.dropdown`, `.dropdown-menu`, `.user-menu`, `.option-menu`
   - 预计：~100行

6. **components/badges.css**
   - 来源：components.css, pages.css
   - 选择器：`.badge`, `.status-badge`, `.user-badge`, `.role-badge`
   - 预计：~80行

#### 优先级3：辅助组件

7. **components/avatars.css**
   - 来源：components.css, pages.css
   - 选择器：`.avatar`, `.avatar-sm`, `.avatar-lg`, `.message-role`
   - 预计：~80行

8. **components/tooltips.css**
   - 来源：components.css
   - 选择器：`.tooltip`, `.tooltip-content`
   - 预计：~60行

9. **components/spinners.css**
   - 来源：components.css
   - 选择器：`.spinner`, `.loading`
   - 预计：~60行

10. **components/alerts.css**
    - 来源：components.css
    - 选择器：`.alert`, `.alert-success`, `.alert-danger`
    - 预计：~80行

11. **components/tables.css**
    - 来源：tables.css, admin.css
    - 选择器：`.table`, `.table-row`, `.admin-shell .table`
    - 预计：~150行

12. **components/sidebar.css**
    - 来源：sidebar.css
    - 选择器：`.sidebar`, `.sidebar-header`, `.sidebar-nav`, `.sidebar-item`
    - 预计：~400行

---

## 📝 复制到新聊天框的提示词

```
我正在执行CSS重构项目的阶段4：组件层迁移。

**背景：**
- 阶段0-3已完成（审计、准备、核心层、主题层）
- 当前状态文档：frontend/CSS_REFACTOR_PHASE4_START.md
- 执行指南：frontend/CSS_REFACTOR_EXECUTION_GUIDE.md
- 迁移映射表：frontend/css-migration-map.md

**任务：**
按优先级顺序创建12个组件CSS文件，从现有CSS中提取可复用组件样式。

**优先级1（先做这3个）：**
1. components/buttons.css - 从 components.css, modern-ui-enhancements.css, final-polish.css 提取按钮样式
2. components/forms.css - 从 components.css, precision-adjustments.css 提取表单样式
3. components/cards.css - 从 components.css, final-polish.css 提取卡片样式

完成优先级1后，测试构建和样式是否正常，然后继续优先级2和3。

**要求：**
- 每个组件文件创建后，更新 src/styles.css 导入
- 每完成3个组件，运行 npm run build 测试
- 保持选择器名称不变
- 不要删除源文件中的代码（稍后统一清理）
- 使用 TodoWrite 跟踪进度

**参考文档：**
- frontend/CSS_OPTIMIZATION_PLAN.md 第3.3节
- frontend/css-migration-map.md 组件层部分
```

---

## 🔧 有用的命令

```bash
# 搜索特定选择器
cd frontend/src/styles
grep -n "\.btn" components.css

# 测试构建
cd frontend
npm run build

# 查看文件大小
ls -lh src/styles/components/

# 验证CSS语法
npx stylelint "src/styles/components/*.css"
```

---

## ⚠️ 注意事项

1. **不要删除源文件代码** - 在阶段8统一清理
2. **保持选择器名称** - 不要重命名，避免破坏现有功能
3. **测试频繁** - 每完成3个组件就测试构建
4. **暗色模式已提取** - 不要再提取暗色样式到组件文件
5. **增强层代码** - 优先使用增强层的版本（更新）

---

## 📊 预期结果

完成阶段4后：
- 12个组件文件已创建
- src/styles.css 已更新导入
- 构建测试通过
- 无样式回归
- 准备进入阶段5（页面层迁移）

---

**祝重构顺利！** 🚀
