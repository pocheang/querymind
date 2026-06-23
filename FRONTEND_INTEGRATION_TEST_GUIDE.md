# 前端权限集成测试指南

**测试日期：** 2026-06-22  
**状态：** ✅ 代码集成完成，待UI测试  

---

## ✅ 已完成的集成

### 1. 更新的文件

| 文件 | 变更 | 状态 |
|------|------|------|
| `frontend/src/pages/ChatPage.tsx` | 传递user到ChatTopbar | ✅ |
| `frontend/src/pages/chat/components/ChatSidebar.tsx` | 传递user到SessionList | ✅ |
| `frontend/src/pages/chat/components/ChatTopbar.tsx` | 接收user，显示徽章 | ✅ |
| `frontend/src/pages/chat/components/SessionList.tsx` | 接收user，隐藏删除按钮 | ✅ |
| `frontend/src/hooks/usePermissions.ts` | 权限系统hook | ✅ |

### 2. 数据流

```
App.tsx
  └─> ChatPage.tsx (user)
      ├─> ChatTopbar (user) ✅
      │   └─> usePermissions(user)
      │       └─> 显示RoleBadge
      │       └─> 隐藏设置按钮（非Admin）
      │
      └─> ChatSidebar (user) ✅
          └─> SessionList (user) ✅
              └─> usePermissions(user)
                  └─> 隐藏删除按钮（Viewer）
```

---

## 🧪 测试步骤

### 准备工作

#### 1. 确保后端服务运行
```bash
# 检查后端
curl http://localhost:8000/health
# 应该返回: {"status":"ok"}
```

#### 2. 确保有测试用户
```bash
# 如果还没有，创建测试用户
# Viewer
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer_test","password":"ViewerTest@123"}'

# Analyst
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst_test","password":"AnalystTest@123"}'

# 提升analyst_test为analyst角色
python << 'EOF'
import sqlite3
conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()
cursor.execute("UPDATE users SET role='analyst' WHERE username='analyst_test'")
conn.commit()
conn.close()
print("Analyst role updated")
EOF

# Admin (使用已有的admin_test)
# 已经在数据库中，密码是 AdminTest@123
```

#### 3. 启动前端
```bash
cd frontend
npm install  # 如果还没安装依赖
npm run dev
```

### 测试场景

---

## 测试1：Viewer角色 ✅

### 操作步骤
1. 打开浏览器访问 `http://localhost:5173`（或前端运行的端口）
2. 使用Viewer账户登录
   - 用户名：`viewer_test`
   - 密码：`ViewerTest@123`

### 预期结果

#### ✅ 顶部栏（ChatTopbar）
```
应该显示：
┌──────────────────────────────────────────┐
│ [viewer_test] [Viewer徽章] [语言] [主题] [架构] │
└──────────────────────────────────────────┘

不应该显示：
❌ 设置按钮 (⚙)
```

#### ✅ 会话列表（SessionList）
```
创建一个会话，然后点击会话右侧的菜单按钮(⋯)

应该显示：
┌──────────────┐
│ ✎ 重命名     │
└──────────────┘

不应该显示：
❌ × 删除
```

#### ✅ 功能验证
- ✅ 可以创建新会话
- ✅ 可以查看会话
- ✅ 可以重命名会话
- ✅ 可以执行查询
- ❌ 不能删除会话
- ❌ 不能访问设置

### 测试检查清单
- [ ] 顶部栏显示"Viewer"徽章
- [ ] 顶部栏没有设置按钮
- [ ] 会话菜单只有"重命名"
- [ ] 会话菜单没有"删除"
- [ ] 可以正常查询

---

## 测试2：Analyst角色 ✅

### 操作步骤
1. 登出当前用户
2. 使用Analyst账户登录
   - 用户名：`analyst_test`
   - 密码：`AnalystTest@123`

### 预期结果

#### ✅ 顶部栏（ChatTopbar）
```
应该显示：
┌──────────────────────────────────────────┐
│ [analyst_test] [Analyst徽章] [语言] [主题] [架构] │
└──────────────────────────────────────────┘

不应该显示：
❌ 设置按钮 (⚙)
```

#### ✅ 会话列表（SessionList）
```
创建一个会话，然后点击会话右侧的菜单按钮(⋯)

应该显示：
┌──────────────┐
│ ✎ 重命名     │
│ × 删除       │
└──────────────┘
```

#### ✅ 功能验证
- ✅ 可以创建新会话
- ✅ 可以查看会话
- ✅ 可以重命名会话
- ✅ 可以删除会话 ⭐（与Viewer的区别）
- ✅ 可以执行查询
- ❌ 不能访问设置

### 测试检查清单
- [ ] 顶部栏显示"Analyst"徽章
- [ ] 顶部栏没有设置按钮
- [ ] 会话菜单有"重命名"
- [ ] 会话菜单有"删除" ⭐
- [ ] 可以成功删除会话 ⭐

---

## 测试3：Admin角色 ✅

### 操作步骤
1. 登出当前用户
2. 使用Admin账户登录
   - 用户名：`admin_test`
   - 密码：`AdminTest@123`

### 预期结果

#### ✅ 顶部栏（ChatTopbar）
```
应该显示：
┌────────────────────────────────────────────────┐
│ [admin_test] [Admin徽章] [语言] [⚙设置] [主题] [架构] │
└────────────────────────────────────────────────┘

✅ 有设置按钮 (⚙) ⭐
```

#### ✅ 会话列表（SessionList）
```
创建一个会话，然后点击会话右侧的菜单按钮(⋯)

应该显示：
┌──────────────┐
│ ✎ 重命名     │
│ × 删除       │
└──────────────┘
```

#### ✅ 功能验证
- ✅ 可以创建新会话
- ✅ 可以查看会话
- ✅ 可以重命名会话
- ✅ 可以删除会话
- ✅ 可以执行查询
- ✅ 可以访问设置 ⭐（与Analyst的区别）

### 测试检查清单
- [ ] 顶部栏显示"Admin"徽章
- [ ] 顶部栏有设置按钮 ⭐
- [ ] 可以点击设置按钮打开设置页面 ⭐
- [ ] 会话菜单有"重命名"和"删除"
- [ ] 可以成功删除会话

---

## 测试4：权限对比 ✅

创建一个对比测试表格，记录实际结果：

| 功能 | Viewer | Analyst | Admin | 备注 |
|------|--------|---------|-------|------|
| 顶部栏-用户名显示 | [ ] | [ ] | [ ] | 应该都显示 |
| 顶部栏-角色徽章 | [ ] | [ ] | [ ] | 应该显示对应角色 |
| 顶部栏-设置按钮 | [ ] 无 | [ ] 无 | [ ] 有 | 只有Admin有 |
| 会话-创建 | [ ] | [ ] | [ ] | 应该都可以 |
| 会话-查看 | [ ] | [ ] | [ ] | 应该都可以 |
| 会话-重命名 | [ ] | [ ] | [ ] | 应该都可以 |
| 会话-删除按钮 | [ ] 无 | [ ] 有 | [ ] 有 | Viewer看不到 |
| 执行查询 | [ ] | [ ] | [ ] | 应该都可以 |

---

## 🐛 常见问题排查

### 问题1：角色徽章不显示
**可能原因：**
- user对象为null
- user.role未正确传递

**解决方法：**
```typescript
// 在ChatTopbar组件中添加调试
console.log('User:', user);
console.log('User role:', user?.role);
```

### 问题2：删除按钮仍然显示给Viewer
**可能原因：**
- user未传递到SessionList
- permissions.canDeleteSession返回错误值

**解决方法：**
```typescript
// 在SessionList组件中添加调试
console.log('User:', user);
console.log('Permissions:', permissions);
console.log('Can delete:', permissions.canDeleteSession);
```

### 问题3：设置按钮不显示给Admin
**可能原因：**
- user.role不是'admin'
- permissions.canConfigureSystem返回false

**解决方法：**
```typescript
// 在ChatTopbar组件中添加调试
console.log('User role:', user?.role);
console.log('Can configure:', permissions.canConfigureSystem);
```

### 问题4：TypeScript编译错误
**可能原因：**
- User类型未导入
- usePermissions未正确导入

**解决方法：**
```typescript
// 确保导入正确
import { usePermissions, RoleBadge, type User } from '@/hooks/usePermissions';
```

---

## 📸 截图收集

测试时建议截图保存以下场景：

1. **Viewer界面**
   - [ ] 顶部栏（显示Viewer徽章，无设置）
   - [ ] 会话菜单（只有重命名）

2. **Analyst界面**
   - [ ] 顶部栏（显示Analyst徽章，无设置）
   - [ ] 会话菜单（有重命名和删除）

3. **Admin界面**
   - [ ] 顶部栏（显示Admin徽章，有设置）
   - [ ] 会话菜单（有重命名和删除）
   - [ ] 设置页面

---

## ✅ 测试完成标准

### 必须通过
- [ ] 所有3种角色都能正常登录
- [ ] 所有3种角色都显示正确的徽章
- [ ] Viewer看不到删除按钮
- [ ] Analyst和Admin看到删除按钮
- [ ] 只有Admin看到设置按钮
- [ ] 所有角色都能正常查询

### 可选验证
- [ ] 徽章样式正确（颜色、字体）
- [ ] UI响应流畅
- [ ] 无控制台错误
- [ ] 无TypeScript编译错误

---

## 🚀 测试后操作

### 如果测试通过
```bash
# 1. 提交代码
git add frontend/src/pages/ChatPage.tsx
git add frontend/src/pages/chat/components/ChatSidebar.tsx
git commit -m "feat: complete frontend permission integration

- Pass user prop to ChatTopbar
- Pass user prop to SessionList via ChatSidebar
- All permission controls now working in UI
- Tested with Viewer, Analyst, and Admin roles"

# 2. 推送到远程
git push origin main

# 3. 准备部署
```

### 如果测试失败
1. 记录失败的测试场景
2. 检查控制台错误信息
3. 使用上面的"常见问题排查"
4. 修复问题后重新测试

---

## 📝 测试报告模板

测试完成后，填写以下报告：

```markdown
# 前端权限集成测试报告

**测试人员：** [你的名字]
**测试日期：** 2026-06-22
**测试环境：** 本地开发环境

## 测试结果

### Viewer角色
- [ ] 通过 / [ ] 失败
- 问题：[如果失败，描述问题]

### Analyst角色
- [ ] 通过 / [ ] 失败
- 问题：[如果失败，描述问题]

### Admin角色
- [ ] 通过 / [ ] 失败
- 问题：[如果失败，描述问题]

## 总体评价
- 测试通过率：__/3
- 是否可以部署：[ ] 是 / [ ] 否
- 备注：[其他说明]
```

---

**测试指南状态：** ✅ 完成  
**下一步：** 执行UI测试  
**预计时间：** 30-60分钟
