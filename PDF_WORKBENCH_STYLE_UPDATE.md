# PDF Workbench 样式统一更新

## 概述
将 PDF Workbench 组件的样式与聊天界面的设计语言统一，确保整个应用的视觉一致性。

## 修改内容

### 1. CSS 样式 - `frontend/src/styles/components/sidebar/modules.css`

添加了与 Knowledge Base 卡片样式完全匹配的 PDF Workbench 卡片样式：

```css
/* PDF Workbench Grid - 匹配 Knowledge Base 样式 */
.pdf-kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.pdf-kpi-card {
  padding: 8px;
  border-radius: 8px;
  border: 1px solid rgba(100, 122, 180, 0.16);
  background: rgba(7, 12, 24, 0.38);
  transition: all 0.18s ease;
}

.pdf-kpi-card:hover {
  border-color: rgba(91, 140, 255, 0.28);
  background: rgba(15, 25, 45, 0.52);
}

.pdf-kpi-card span {
  display: block;
  color: var(--text-tertiary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.pdf-kpi-card strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 780;
}
```

**关键特性：**
- 完全匹配 `.sidebar-kb-card` 样式模式
- 一致的间距、颜色和排版
- 平滑的悬停过渡效果，带蓝色强调色
- 针对深色主题优化，使用半透明背景

### 2. 组件更新 - `frontend/src/pages/chat/components/PdfWorkbench.tsx`

**结构优化：**
- 移除了多余的 `<section className="panel">` 包裹层
- 移除了未使用的 `onDraftPdfQuestion` prop
- 简化组件结构，直接渲染内容

**中文本地化：**
```tsx
// 之前：
<span>PDF/Image Docs</span>
<span>Need Reindex</span>
<option>No PDF docs</option>
<button>Force pdf_text</button>
<button>Back to auto</button>

// 之后：
<span>PDF/IMAGE DOCS</span>
<span>NEED REINDEX</span>
<option>暂无PDF文档</option>
<button>强制 pdf_text</button>
<button>返回自动</button>
```

### 3. 相关组件清理

移除了未使用的 `onDraftPdfQuestion` prop 从以下文件：
- `frontend/src/pages/chat/components/WorkbenchPanel.tsx`
- `frontend/src/pages/chat/components/ChatSidebar.tsx`
- `frontend/src/pages/ChatPage.tsx`

## 设计原则

### 视觉一致性
- **调色板**：使用与消息气泡和其他 UI 元素相同的蓝色强调色 (`rgba(91, 140, 255, ...)`)
- **圆角**：一致的 8px 圆角，匹配其他卡片
- **间距**：卡片之间 8px 间距，匹配 Knowledge Base 指标网格

### 排版
- **标签**：10px，800 字重，0.08em 字间距（大写样式）
- **数值**：16px，780 字重
- **颜色层次**：标签使用三级文本色，数值使用主文本色

### 交互状态
- **悬停效果**：边框颜色变为蓝色强调色，背景变亮
- **过渡**：所有状态变化使用平滑的 0.18s ease 过渡
- **视觉反馈**：交互元素有清晰的指示

### 深色主题优化
- 半透明背景增加深度感
- 不会过于突出的细微边框
- 适当的对比度确保可访问性

## 与聊天界面的对比

| 元素 | 聊天界面 | PDF Workbench | 状态 |
|---------|---------------|---------------|--------|
| 卡片背景 | `rgba(7, 12, 24, 0.38)` | `rgba(7, 12, 24, 0.38)` | ✅ 匹配 |
| 边框颜色 | `rgba(100, 122, 180, 0.16)` | `rgba(100, 122, 180, 0.16)` | ✅ 匹配 |
| 悬停边框 | `rgba(91, 140, 255, 0.28)` | `rgba(91, 140, 255, 0.28)` | ✅ 匹配 |
| 标签字号 | 10px | 10px | ✅ 匹配 |
| 数值字号 | 16px | 16px | ✅ 匹配 |
| 圆角 | 8px | 8px | ✅ 匹配 |
| 网格间距 | 8px | 8px | ✅ 匹配 |

## 构建验证

✅ 前端构建成功完成，无错误
✅ 所有 TypeScript 类型验证通过
✅ CSS 正确打包和压缩

## 视觉效果

PDF Workbench 现在与聊天界面无缝集成：
- 与 Knowledge Base 指标一致的卡片样式
- 统一的配色方案和排版
- 平滑的悬停交互
- 专业、统一的外观
- 完全本地化的中文界面

## 修改的文件

1. `frontend/src/styles/components/sidebar/modules.css` - 添加 PDF 卡片样式
2. `frontend/src/pages/chat/components/PdfWorkbench.tsx` - 优化结构和本地化文本
3. `frontend/src/pages/chat/components/WorkbenchPanel.tsx` - 移除未使用的 prop
4. `frontend/src/pages/chat/components/ChatSidebar.tsx` - 移除未使用的 prop
5. `frontend/src/pages/ChatPage.tsx` - 移除未使用的 prop

