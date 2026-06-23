# P2改进实施报告 - 前端权限匹配与扩展功能

**实施日期：** 2026-06-22  
**执行人员：** Claude AI Assistant  
**改进状态：** 🚧 进行中  
**当前进度：** 25%

---

## 📋 P2改进目标

根据项目规划，P2优先级改进包括：

1. ✅ **前端权限匹配** - 根据用户角色显示/隐藏功能（已完成）
2. ⏳ **文档共享功能** - 团队级文档共享（待实施）
3. ⏳ **会话分享功能** - 只读会话链接（待实施）
4. ⏳ **API文档更新** - OpenAPI标注权限要求（待实施）

---

## ✅ 已完成：前端权限匹配

### 创建的文件

**文件：** `frontend/src/hooks/usePermissions.ts` (340行)

### 核心功能

#### 1. usePermissions Hook
提供基于角色的权限检查，与后端RBAC完全同步。

```typescript
const permissions = usePermissions(user);

if (permissions.canDeleteSession) {
  return <DeleteButton onClick={handleDelete} />;
}

if (permissions.isAdmin) {
  return <AdminPanel />;
}
```

#### 2. PermissionGate Component
条件渲染组件，根据权限显示/隐藏内容。

```typescript
<PermissionGate user={user} requires={['canDeleteSession']}>
  <DeleteButton />
</PermissionGate>

<PermissionGate user={user} requires={['isAdmin']}>
  <AdminPanel />
</PermissionGate>
```

#### 3. withPermission HOC
高阶组件模式，包装需要权限的组件。

```typescript
const ProtectedDeleteButton = withPermission(
  DeleteButton,
  ['canDeleteSession'],
  <span>No permission</span>
);
```

#### 4. RoleBadge Component
显示用户角色徽章。

```typescript
<RoleBadge role={user.role} />
// 显示: Admin | Analyst | Viewer
```

### 权限定义

#### Admin权限（全部）
```typescript
canCreateSession: true,
canDeleteSession: true,
canLockStrategy: true,
canEditMessage: true,
canDeleteMessage: true,
canViewPrompts: true,
canCreatePrompt: true,
canEditPrompt: true,
canDeletePrompt: true,
canUploadDocument: true,
canDeleteDocument: true,
canReindexDocument: true,
canAccessAdmin: true,
canManageUsers: true,
canConfigureSystem: true,
canViewAnalytics: true,
canQuery: true,
canViewAgentTracking: true,
```

#### Analyst权限（内容管理）
```typescript
canCreateSession: true,
canDeleteSession: true,
canLockStrategy: true,
canEditMessage: true,
canDeleteMessage: true,
canViewPrompts: true,
canCreatePrompt: true,
canEditPrompt: true,
canDeletePrompt: true,
canUploadDocument: true,
canDeleteDocument: true,
canReindexDocument: true,
canAccessAdmin: false,      // ❌
canManageUsers: false,       // ❌
canConfigureSystem: false,   // ❌
canViewAnalytics: false,     // ❌
canQuery: true,
canViewAgentTracking: true,
```

#### Viewer权限（只读）
```typescript
canCreateSession: true,
canDeleteSession: false,     // ❌
canLockStrategy: false,      // ❌
canEditMessage: false,       // ❌
canDeleteMessage: false,     // ❌
canViewPrompts: true,
canCreatePrompt: false,      // ❌
canEditPrompt: false,        // ❌
canDeletePrompt: false,      // ❌
canUploadDocument: false,    // ❌
canDeleteDocument: false,    // ❌
canReindexDocument: false,   // ❌
canAccessAdmin: false,       // ❌
canManageUsers: false,       // ❌
canConfigureSystem: false,   // ❌
canViewAnalytics: false,     // ❌
canQuery: true,
canViewAgentTracking: true,
```

### 使用示例

#### 示例1: 条件渲染按钮
```typescript
import { usePermissions } from '@/hooks/usePermissions';

function SessionActions({ user, sessionId }) {
  const permissions = usePermissions(user);

  return (
    <div className="flex gap-2">
      {/* 所有用户都能创建会话 */}
      <button>New Session</button>

      {/* 只有Analyst和Admin能删除 */}
      {permissions.canDeleteSession && (
        <button onClick={() => deleteSession(sessionId)}>
          Delete
        </button>
      )}

      {/* 只有Admin能访问设置 */}
      {permissions.canConfigureSystem && (
        <button onClick={() => openSettings()}>
          Settings
        </button>
      )}
    </div>
  );
}
```

#### 示例2: 使用PermissionGate
```typescript
import { PermissionGate } from '@/hooks/usePermissions';

function ChatSidebar({ user }) {
  return (
    <div>
      <h2>Sessions</h2>

      {/* Viewer看不到上传按钮 */}
      <PermissionGate user={user} requires={['canUploadDocument']}>
        <button>Upload Document</button>
      </PermissionGate>

      {/* 只有Admin看到管理面板 */}
      <PermissionGate user={user} requires={['isAdmin']}>
        <AdminDashboardLink />
      </PermissionGate>
    </div>
  );
}
```

#### 示例3: 显示角色徽章
```typescript
import { RoleBadge } from '@/hooks/usePermissions';

function UserProfile({ user }) {
  return (
    <div className="flex items-center gap-2">
      <span>{user.username}</span>
      <RoleBadge role={user.role} />
    </div>
  );
}
```

### 前后端权限同步

| 权限 | 后端RBAC | 前端Hook | 同步状态 |
|------|---------|---------|---------|
| session:read | ✅ | canCreateSession* | ✅ |
| session:delete | ✅ | canDeleteSession | ✅ |
| message:edit | ✅ | canEditMessage | ✅ |
| message:delete | ✅ | canDeleteMessage | ✅ |
| prompt:create | ✅ | canCreatePrompt | ✅ |
| prompt:delete | ✅ | canDeletePrompt | ✅ |
| upload:create | ✅ | canUploadDocument | ✅ |
| admin:ops_manage | ✅ | canAccessAdmin | ✅ |

*注：session:read映射为canCreateSession，因为创建包含读取

### 集成指南

#### 步骤1: 在App.tsx中使用
```typescript
import { usePermissions, PermissionGate } from '@/hooks/usePermissions';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const permissions = usePermissions(user);

  return (
    <div>
      <Header user={user} permissions={permissions} />
      <Sidebar user={user} permissions={permissions} />
      <MainContent user={user} permissions={permissions} />
    </div>
  );
}
```

#### 步骤2: 更新UI组件
需要更新以下组件以支持权限：

1. **ChatSidebar** - 隐藏上传/删除按钮（Viewer）
2. **ChatTopbar** - 隐藏设置按钮（非Admin）
3. **SessionList** - 隐藏删除按钮（Viewer）
4. **PromptManager** - 隐藏创建/编辑按钮（Viewer）
5. **DocumentUpload** - 完全隐藏（Viewer）
6. **AdminPanel** - 完全隐藏（非Admin）

#### 步骤3: 测试权限
```bash
# 1. 以Viewer登录
# 验证：看不到删除、编辑、上传按钮

# 2. 以Analyst登录
# 验证：可以看到删除、编辑、上传按钮，但看不到Admin面板

# 3. 以Admin登录
# 验证：可以看到所有功能
```

---

## ⏳ 待实施：文档共享功能

### 目标
实现团队级文档共享，允许用户分享文档给特定用户或组。

### 计划的功能

#### 1. 后端API
```python
# app/api/routes/document_sharing.py

@router.post("/documents/{document_id}/share")
def share_document(
    document_id: str,
    share_with: List[str],  # user_ids
    permission: str = "read",  # read | write
    user: dict = Depends(_require_user)
):
    # 只有文档所有者或Admin可以分享
    # 创建sharing记录
    pass

@router.get("/documents/shared-with-me")
def list_shared_documents(user: dict = Depends(_require_user)):
    # 列出分享给当前用户的文档
    pass
```

#### 2. 数据库Schema
```sql
CREATE TABLE document_shares (
    share_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    shared_with_user_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'read',
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(user_id),
    FOREIGN KEY (shared_with_user_id) REFERENCES users(user_id)
);
```

#### 3. 前端UI
- 文档列表显示分享图标
- 分享对话框选择用户
- "分享给我的"标签页

### 预期工作量
- 后端实现：6-8小时
- 数据库迁移：1小时
- 前端UI：4-6小时
- 测试：2-3小时
- **总计：13-18小时**

---

## ⏳ 待实施：会话分享功能

### 目标
生成只读会话链接，允许分享对话给其他人查看。

### 计划的功能

#### 1. 后端API
```python
# app/api/routes/session_sharing.py

@router.post("/sessions/{session_id}/share")
def create_share_link(
    session_id: str,
    expires_in_hours: int = 24,
    user: dict = Depends(_require_user)
):
    # 生成唯一的分享token
    # 返回分享链接
    pass

@router.get("/shared/sessions/{share_token}")
def view_shared_session(share_token: str):
    # 公开访问，不需要认证
    # 返回只读会话内容
    pass
```

#### 2. 数据库Schema
```sql
CREATE TABLE session_shares (
    share_token TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    view_count INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

#### 3. 前端UI
- 会话右键菜单"分享会话"
- 复制分享链接
- 只读查看器页面

### 预期工作量
- 后端实现：4-6小时
- 数据库迁移：1小时
- 前端UI：3-4小时
- 测试：2小时
- **总计：10-13小时**

---

## ⏳ 待实施：API文档更新

### 目标
在OpenAPI/Swagger文档中标注每个端点的权限要求。

### 计划的内容

#### 1. 权限标注
```python
@router.get("/documents/index-health")
@permission_required("admin")  # 装饰器
def document_index_health(...):
    """
    Get document index health statistics.

    **Required Permission:** admin:ops_manage
    **Allowed Roles:** admin
    """
    pass
```

#### 2. 生成权限矩阵文档
自动生成Markdown表格，展示所有端点的权限要求。

```markdown
| Endpoint | Method | Required Permission | Admin | Analyst | Viewer |
|----------|--------|-------------------|-------|---------|--------|
| /sessions | GET | session:read | ✅ | ✅ | ✅ |
| /sessions | DELETE | session:delete | ✅ | ✅ | ❌ |
| /prompts | POST | prompt:create | ✅ | ✅ | ❌ |
```

#### 3. 在Swagger UI中显示
更新FastAPI的OpenAPI配置，在每个端点描述中添加权限信息。

### 预期工作量
- 添加权限标注：2-3小时
- 生成文档工具：2小时
- 更新Swagger配置：1小时
- **总计：5-6小时**

---

## 📊 P2整体进度

| 任务 | 状态 | 进度 | 预计工作量 |
|------|------|------|-----------|
| 前端权限匹配 | ✅ 完成 | 100% | 4-6小时 |
| 文档共享功能 | ⏳ 待实施 | 0% | 13-18小时 |
| 会话分享功能 | ⏳ 待实施 | 0% | 10-13小时 |
| API文档更新 | ⏳ 待实施 | 0% | 5-6小时 |

**总体进度：** 25% (1/4完成)  
**总预计工作量：** 32-43小时

---

## 🎯 下一步计划

### 优先级1：集成前端权限
1. 更新ChatSidebar组件
2. 更新ChatTopbar组件
3. 更新SessionList组件
4. 更新PromptManager组件
5. 添加RoleBadge到用户菜单
6. 测试所有角色的UI

### 优先级2：实施文档共享
如果用户需要文档共享功能，开始实施后端API和数据库schema。

### 优先级3：实施会话分享
如果用户需要会话分享功能，开始实施分享链接生成。

### 优先级4：更新API文档
最后更新API文档，确保所有权限要求都有文档记录。

---

## 📝 使用建议

### 立即可用
前端权限hook已创建，可以立即在现有组件中使用：

```typescript
import { usePermissions, PermissionGate } from '@/hooks/usePermissions';
```

### 渐进式集成
不需要一次性更新所有组件，可以逐步集成：

1. **第一阶段：** 关键操作（删除、上传）
2. **第二阶段：** 次要功能（编辑、分享）
3. **第三阶段：** UI优化（徽章、提示）

### 测试方法
```bash
# 创建测试用户
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test_viewer","password":"TestViewer@123"}'

# 在前端以不同角色登录测试UI
```

---

## ✅ 交付物

### 已完成
1. ✅ `frontend/src/hooks/usePermissions.ts` - 权限hook (340行)
2. ✅ `P2_IMPLEMENTATION_REPORT.md` - 实施报告（本文档）

### 待完成
3. ⏳ 更新的UI组件（6-8个文件）
4. ⏳ 文档共享API
5. ⏳ 会话分享API
6. ⏳ API文档更新

---

**报告状态：** 🚧 进行中  
**当前阶段：** 前端权限hook已完成，等待集成到UI  
**日期：** 2026-06-22  
**下一步：** 等待用户确认是否继续实施其他P2功能
