import { useMemo } from "react";
import { AdminUserTable } from "@/pages/admin/AdminUserTable";
import type { AdminUserSummary } from "@/types/api";

type Props = {
  users: AdminUserSummary[];
  loadingUsers: boolean;
  kw: string;
  fRole: string;
  fStatus: string;
  fOnline: string;
  editingUser: AdminUserSummary | null;
  editBu: string;
  editDept: string;
  editType: string;
  editScope: string;
  savingClass: boolean;
  roleOptions: string[];
  statusOptions: string[];
  onKwChange: (value: string) => void;
  onFRoleChange: (value: string) => void;
  onFStatusChange: (value: string) => void;
  onFOnlineChange: (value: string) => void;
  onEditingUserChange: (user: AdminUserSummary | null) => void;
  onEditBuChange: (value: string) => void;
  onEditDeptChange: (value: string) => void;
  onEditTypeChange: (value: string) => void;
  onEditScopeChange: (value: string) => void;
  onLoadUsers: () => void;
  onSaveClass: () => void;
  onUpdateRole: (target: AdminUserSummary, role: string) => Promise<void>;
  onUpdateStatus: (target: AdminUserSummary, status: string) => Promise<void>;
  onOpenClassEditor: (user: AdminUserSummary) => void;
  onResetPassword: (target: AdminUserSummary) => Promise<void>;
  onResetApprovalToken: (target: AdminUserSummary) => Promise<void>;
};

export function AdminUserManagement({
  users,
  loadingUsers,
  kw,
  fRole,
  fStatus,
  fOnline,
  editingUser,
  editBu,
  editDept,
  editType,
  editScope,
  savingClass,
  roleOptions,
  statusOptions,
  onKwChange,
  onFRoleChange,
  onFStatusChange,
  onFOnlineChange,
  onEditingUserChange,
  onEditBuChange,
  onEditDeptChange,
  onEditTypeChange,
  onEditScopeChange,
  onLoadUsers,
  onSaveClass,
  onUpdateRole,
  onUpdateStatus,
  onOpenClassEditor,
  onResetPassword,
  onResetApprovalToken,
}: Props) {
  const filteredUsers = useMemo(() => {
    const q = kw.trim().toLowerCase();
    return users.filter((u) => {
      if (q && ![u.username, u.user_id, u.business_unit, u.department, u.user_type, u.data_scope].join(" ").toLowerCase().includes(q)) return false;
      if (fRole && (u.role || "") !== fRole) return false;
      if (fStatus && (u.status || "") !== fStatus) return false;
      if (fOnline === "online" && !u.is_online) return false;
      if (fOnline === "offline" && u.is_online) return false;
      if (fOnline === "online_10m" && !u.is_online_10m) return false;
      return true;
    });
  }, [users, kw, fRole, fStatus, fOnline]);

  return (
    <main className="panel admin-users-panel">
      <div className="section-head">
        <strong>用户管理</strong>
        <button type="button" className="secondary tiny-btn" onClick={onLoadUsers}>刷新</button>
      </div>
      <p className="muted admin-users-hint">可按用户ID/用户名筛选，并直接执行角色、状态和安全操作。</p>

      <div className="ops-two-col admin-filter-grid">
        <label className="admin-field">
          <span>搜索</span>
          <input placeholder="搜索用户名 / 用户ID / 分类字段" value={kw} onChange={(e) => onKwChange(e.target.value)} />
        </label>
        <label className="admin-field">
          <span>角色</span>
          <select value={fRole} onChange={(e) => onFRoleChange(e.target.value)}>
            <option value="">全部角色</option>
            <option value="admin">admin</option>
            <option value="analyst">analyst</option>
            <option value="viewer">viewer</option>
          </select>
        </label>
      </div>

      <div className="ops-two-col admin-filter-grid">
        <label className="admin-field">
          <span>状态</span>
          <select value={fStatus} onChange={(e) => onFStatusChange(e.target.value)}>
            <option value="">全部状态</option>
            <option value="active">active</option>
            <option value="disabled">disabled</option>
          </select>
        </label>
        <label className="admin-field">
          <span>在线状态</span>
          <select value={fOnline} onChange={(e) => onFOnlineChange(e.target.value)}>
            <option value="">全部在线状态</option>
            <option value="online_10m">10分钟内在线</option>
            <option value="online">在线</option>
            <option value="offline">离线</option>
          </select>
        </label>
      </div>

      {editingUser && (
        <div className="panel" style={{ marginBottom: 12 }}>
          <div className="section-head">
            <strong>用户分类：{editingUser.username}</strong>
            <button type="button" className="secondary tiny-btn" onClick={() => onEditingUserChange(null)}>取消</button>
          </div>
          <div className="ops-two-col">
            <input placeholder="业务单元" value={editBu} onChange={(e) => onEditBuChange(e.target.value)} />
            <input placeholder="部门" value={editDept} onChange={(e) => onEditDeptChange(e.target.value)} />
          </div>
          <div className="ops-two-col">
            <input placeholder="用户类型" value={editType} onChange={(e) => onEditTypeChange(e.target.value)} />
            <input placeholder="数据范围" value={editScope} onChange={(e) => onEditScopeChange(e.target.value)} />
          </div>
          <div className="row-actions">
            <button type="button" disabled={savingClass} onClick={onSaveClass}>
              {savingClass ? "保存中..." : "保存分类"}
            </button>
          </div>
        </div>
      )}

      {loadingUsers && <div className="skeleton-list" />}
      {!loadingUsers && (
        <AdminUserTable
          users={filteredUsers}
          roleOptions={roleOptions}
          statusOptions={statusOptions}
          onUpdateRole={onUpdateRole}
          onUpdateStatus={onUpdateStatus}
          onOpenClassEditor={onOpenClassEditor}
          onResetPassword={onResetPassword}
          onResetApprovalToken={onResetApprovalToken}
        />
      )}
    </main>
  );
}
