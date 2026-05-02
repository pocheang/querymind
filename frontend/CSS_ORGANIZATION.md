# CSS 组织结构文档

## 文件结构

```
frontend/src/
├── styles.css                      # 主入口文件（导入所有模块）
└── styles/
    ├── base.css                    # 设计系统基础（变量、重置、工具类）
    ├── components.css              # 共享组件样式
    ├── pages.css                   # 页面特定样式
    ├── precision-adjustments.css   # 精准调整（Toggle开关、快捷提示等）
    ├── modern-ui-enhancements.css  # 现代UI增强
    ├── final-polish.css            # 最终润色
    └── ui-polish.css               # UI优化
```

## 各文件职责

### 1. base.css (299 行)
**职责：** 设计系统基础层
- CSS 自定义属性（颜色、间距、字体、阴影等）
- 亮色/暗色主题变量
- 全局重置样式
- 基础工具类

**不要修改：** 除非需要添加新的设计令牌

### 2. components.css (1,473 行)
**职责：** 共享组件库
- 认证页面组件（.auth-root, .auth-card, .auth-form）
- 表单组件（.input-group, .auth-input-shell）
- 按钮（.primary-action-btn, .social-btn）
- 状态消息（.alert, .status）
- 密码要求组件
- 社交登录按钮

**包含页面：**
- 登录页面
- 注册页面
- 忘记密码页面
- 修改密码页面

### 3. pages.css (5,326 行)
**职责：** 页面特定样式

#### 管理后台 (1-883 行)
- `.admin-shell` - 管理页面容器
- `.table` - 数据表格
- `.admin-kpi-card` - KPI 卡片
- `.admin-section-tabs` - 标签页
- `.admin-field` - 表单字段
- `.audit-table` - 审计日志表格

#### 聊天界面 (1000-2243 行)
- `.page-shell` - 页面布局
- `.sidebar` - 侧边栏
- `.topbar` - 顶部导航
- `.chat-window` - 聊天窗口
- `.bubble` - 消息气泡
- `.composer-panel` - 输入框面板
- `.session-item` - 会话列表项

#### 运营面板 (2245-2815 行)
- `.ops-kpi-grid` - 运营 KPI 网格
- `.ops-diagnostic-list` - 诊断列表
- `.architecture-grid` - 架构图
- `.progress-bar` - 进度条

#### 聊天控制台刷新 (4308-5326 行)
- 完整的聊天界面重新设计
- 新的配色方案和布局
- 暗色模式优化

### 4. precision-adjustments.css (402 行)
**职责：** 精准的视觉调整

**关键特性：**
1. **Toggle 开关** (.option-chip)
   - iOS/Vercel 风格的滑动开关
   - 替代原有的按钮样式
   - 48px × 26px 尺寸

2. **快捷提示词** (.quick-prompt-row)
   - 横向滚动布局
   - Outline chip 样式
   - 隐藏滚动条

3. **Agent 卡片增强** (.agent-mode-card)
   - 渐变背景动画
   - Active 状态左侧高亮条
   - 强化的 hover 效果

4. **输入框升级** (.composer-main textarea)
   - 渐变背景
   - Focus 光晕效果
   - 柔和的过渡动画

### 5. modern-ui-enhancements.css (704 行)
**职责：** 现代化 UI 增强
- 终端风格的详情面板
- 优化的 chip 样式
- 改进的 hover 状态
- 消息气泡增强

### 6. final-polish.css (511 行)
**职责：** 最终视觉润色
- 增强对比度
- 加粗字体
- 优化阴影
- 改进 focus 状态

### 7. ui-polish.css (581 行)
**职责：** UI 细节优化
- 精细化间距
- 优化信息密度
- 更流畅的过渡动画

## 导入顺序

```css
/* styles.css */
@import './styles/base.css';                    /* 1. 基础层 */
@import './styles/components.css';              /* 2. 组件层 */
@import './styles/pages.css';                   /* 3. 页面层 */
@import './styles/precision-adjustments.css';   /* 4. 精准调整 */
@import './styles/modern-ui-enhancements.css';  /* 5. 现代增强 */
@import './styles/final-polish.css';            /* 6. 最终润色 */
@import './styles/ui-polish.css';               /* 7. UI 优化 */
```

**重要：** 顺序不能改变！后面的文件会覆盖前面的样式。

## 样式优先级

1. **base.css** - 最低优先级（设计令牌）
2. **components.css** - 组件默认样式
3. **pages.css** - 页面特定样式
4. **precision-adjustments.css** - 覆盖特定组件
5. **modern-ui-enhancements.css** - 增强现有样式
6. **final-polish.css** - 视觉润色
7. **ui-polish.css** - 最高优先级（最终调整）

## 关键选择器说明

### Toggle 开关冲突解决
**问题：** `.option-chip` 在多个文件中定义不同样式
- `components.css` - 按钮样式
- `pages.css` - 按钮样式
- `precision-adjustments.css` - Toggle 开关样式（最终生效）

**解决方案：** `precision-adjustments.css` 在导入顺序中靠后，其样式会覆盖前面的定义。

### 暗色模式
所有文件都包含 `:root[data-theme="dark"]` 选择器，按导入顺序层叠应用。

## 修改指南

### 添加新组件
1. 如果是共享组件 → 添加到 `components.css`
2. 如果是页面特定 → 添加到 `pages.css`
3. 如果是视觉调整 → 添加到对应的增强文件

### 修改现有样式
1. 找到样式定义的文件
2. 检查是否有后续文件覆盖
3. 在最后覆盖的文件中修改

### 删除样式
1. 搜索所有文件中的选择器
2. 确认没有依赖关系
3. 从所有文件中删除

## 已知重复

以下选择器在多个文件中定义（按优先级排序）：

1. **`.option-chip`**
   - components.css (按钮)
   - pages.css (按钮)
   - precision-adjustments.css (Toggle 开关) ✓ 最终生效

2. **`.composer-main textarea`**
   - pages.css (基础样式)
   - precision-adjustments.css (增强样式) ✓ 最终生效
   - modern-ui-enhancements.css (进一步增强)
   - final-polish.css (润色)
   - ui-polish.css (最终调整)

3. **`.bubble`**
   - pages.css (基础样式)
   - final-polish.css (增强)
   - modern-ui-enhancements.css (进一步增强)

4. **`.agent-mode-card`**
   - pages.css (基础样式)
   - precision-adjustments.css (增强样式) ✓ 最终生效

## 性能考虑

- **总行数：** ~9,300 行
- **文件数：** 8 个
- **加载顺序：** 串行（通过 @import）
- **构建工具：** Vite 会自动合并和压缩

## 未来优化建议

1. **拆分 pages.css**
   - 创建 `auth.css` (认证页面)
   - 创建 `chat.css` (聊天界面)
   - 创建 `admin.css` (管理后台)
   - 创建 `profile.css` (个人资料)

2. **合并增强文件**
   - 将 4 个增强文件合并为 1 个
   - 减少 HTTP 请求

3. **CSS Modules**
   - 考虑使用 CSS Modules 避免全局污染
   - 更好的作用域隔离

4. **CSS-in-JS**
   - 考虑迁移到 styled-components 或 emotion
   - 更好的类型安全和动态样式

## 维护清单

- [ ] 定期检查重复选择器
- [ ] 删除未使用的样式
- [ ] 合并相似的规则
- [ ] 优化选择器性能
- [ ] 更新暗色模式支持
- [ ] 测试响应式布局
- [ ] 验证浏览器兼容性

## 联系方式

如有问题，请查看：
- Git 提交历史
- CSS 重构文档
- 设计系统文档
