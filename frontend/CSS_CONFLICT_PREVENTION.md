# CSS 冲突预防指南

## 已修复的问题

### 按钮重叠问题
**根本原因**：`.theme-toggle` 类在多个 CSS 文件中定义，且包含 `position: fixed`

**修复的文件**：
1. `src/styles/core/critical.css` - 第419行
2. `src/styles/pages/auth/layout.css` - 第16行

**修复方案**：移除 `position: fixed`，让按钮遵循父容器的 flex 布局

---

## 预防措施

### 1. CSS 类命名规范
- 避免在多个文件中定义同一个类
- 使用 BEM 命名规范（Block__Element--Modifier）
- 组件样式应该只在组件对应的 CSS 文件中定义

### 2. 定位属性使用原则
- 避免在可复用组件上使用 `position: fixed` 或 `position: absolute`
- 固定定位应该在父容器中通过内联样式控制
- 优先使用 flexbox 或 grid 布局

### 3. CSS 文件组织
```
styles/
├── core/
│   └── critical.css       # ⚠️ 关键样式，避免组件特定样式
├── components/
│   ├── language-toggle.css # ✓ 组件独立样式
│   └── theme-toggle.css    # 建议：创建独立文件
└── pages/
    └── auth/
        └── layout.css      # ⚠️ 避免重复定义组件样式
```

### 4. 检查清单
在添加新 CSS 之前：
- [ ] 检查该类名是否已在其他文件中定义
- [ ] 确认定位属性不会与父容器布局冲突
- [ ] 使用浏览器开发者工具查看实际应用的样式
- [ ] 测试不同页面和布局场景

### 5. 建议的改进
1. **创建独立的 theme-toggle.css**
   - 从 critical.css 和 auth/layout.css 中移除
   - 放在 `components/theme-toggle.css`

2. **使用 CSS Modules 或 Scoped CSS**
   - 防止全局样式冲突
   - 自动生成唯一的类名

3. **定期运行 CSS 审计**
   - 检查重复定义
   - 查找未使用的样式
   - 识别冲突的样式规则

---

## 当前状态

✅ **已修复**：
- `.theme-toggle` 在 critical.css 中移除 `position: fixed`
- `.theme-toggle` 在 auth/layout.css 中移除 `position: fixed`
- 按钮现在正确遵循 flex 布局

⚠️ **待优化**：
- 考虑将 `.theme-toggle` 统一到一个文件
- 使用更明确的组件样式隔离策略

---

**最后更新**: 2026-06-03
**状态**: ✅ 按钮重叠问题已解决
