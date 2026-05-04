import type { AdminUserSummary } from "@/types/api";

type Props = {
  users: AdminUserSummary[];
  roleOptions: string[];
  statusOptions: string[];
  onUpdateRole: (user: AdminUserSummary, role: string) => Promise<void>;
  onUpdateStatus: (user: AdminUserSummary, status: string) => Promise<void>;
  onOpenClassEditor: (user: AdminUserSummary) => void;
  onResetPassword: (user: AdminUserSummary) => Promise<void>;
  onResetApprovalToken: (user: AdminUserSummary) => Promise<void>;
};

export function AdminUserTable({
  users,
  roleOptions,
  statusOptions,
  onUpdateRole,
  onUpdateStatus,
  onOpenClassEditor,
  onResetPassword,
  onResetApprovalToken,
}: Props) {
  return (
    <table className="table admin-user-table">
      <thead>
        <tr>
          <th>用户ID</th>
          <th>用户名</th>
          <th>角色</th>
          <th>状态</th>
          <th>在线</th>
          <th>10分钟</th>
          <th>业务单元</th>
          <th>部门</th>
          <th>类型</th>
          <th>范围</th>
          <th>创建人</th>
          <th>工单</th>
          <th>令牌</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {users.map((row) => (
          <tr key={row.user_id}>
            <td className="admin-user-id">{row.user_id}</td>
            <td className="admin-username">{row.username}</td>
            <td>
              <select value={row.role} onChange={(e) => void onUpdateRole(row, e.target.value)}>
                {([...(row.role === "admin" ? ["admin"] : []), ...roleOptions] as string[]).map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <select value={row.status} onChange={(e) => void onUpdateStatus(row, e.target.value)}>
                {statusOptions.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </td>
            <td>{row.is_online ? "在线" : "离线"}</td>
            <td>{row.is_online_10m ? "活跃" : "-"}</td>
            <td>{row.business_unit || "-"}</td>
            <td>{row.department || "-"}</td>
            <td>{row.user_type || "-"}</td>
            <td>{row.data_scope || "-"}</td>
            <td>{row.created_by_username || row.created_by_user_id || "-"}</td>
            <td>{row.admin_ticket_id || "-"}</td>
            <td>{row.has_admin_approval_token ? "已设置" : "未设置"}</td>
            <td>
              <div className="row-actions user-row-actions">
                <button type="button" className="secondary tiny-btn" onClick={() => onOpenClassEditor(row)}>
                  分类
                </button>
                <button type="button" className="secondary tiny-btn" onClick={() => void onResetPassword(row)}>
                  重置密码
                </button>
                {(row.role || "").toLowerCase() === "admin" ? (
                  <button type="button" className="secondary tiny-btn" onClick={() => void onResetApprovalToken(row)}>
                    重置令牌
                  </button>
                ) : null}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
