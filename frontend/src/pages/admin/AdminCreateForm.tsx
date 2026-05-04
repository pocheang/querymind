type Props = {
  adminUsername: string;
  adminPassword: string;
  adminPassword2: string;
  adminApprovalToken: string;
  newAdminApprovalToken: string;
  adminTicketId: string;
  adminReason: string;
  creatingAdmin: boolean;
  onAdminUsernameChange: (value: string) => void;
  onAdminPasswordChange: (value: string) => void;
  onAdminPassword2Change: (value: string) => void;
  onAdminApprovalTokenChange: (value: string) => void;
  onNewAdminApprovalTokenChange: (value: string) => void;
  onAdminTicketIdChange: (value: string) => void;
  onAdminReasonChange: (value: string) => void;
  onCreateAdmin: () => void;
};

export function AdminCreateForm({
  adminUsername,
  adminPassword,
  adminPassword2,
  adminApprovalToken,
  newAdminApprovalToken,
  adminTicketId,
  adminReason,
  creatingAdmin,
  onAdminUsernameChange,
  onAdminPasswordChange,
  onAdminPassword2Change,
  onAdminApprovalTokenChange,
  onNewAdminApprovalTokenChange,
  onAdminTicketIdChange,
  onAdminReasonChange,
  onCreateAdmin,
}: Props) {
  return (
    <main className="panel admin-create-panel">
      <div className="section-head"><strong>创建管理员</strong></div>
      <p className="muted admin-create-hint">请填写账号信息与审批信息。创建成功后会返回新管理员用户ID。</p>
      <div className="ops-two-col admin-create-grid">
        <label className="admin-field">
          <span>管理员用户名</span>
          <input placeholder="例如：sec_admin_01" value={adminUsername} onChange={(e) => onAdminUsernameChange(e.target.value)} />
        </label>
        <label className="admin-field">
          <span>管理员密码</span>
          <input placeholder="至少 12 位，含大小写、数字和特殊字符" type="password" value={adminPassword} onChange={(e) => onAdminPasswordChange(e.target.value)} />
        </label>
      </div>
      <div className="ops-two-col admin-create-grid">
        <label className="admin-field">
          <span>确认密码</span>
          <input placeholder="再次输入密码" type="password" value={adminPassword2} onChange={(e) => onAdminPassword2Change(e.target.value)} />
        </label>
        <label className="admin-field">
          <span>我的审批令牌</span>
          <input placeholder="当前管理员审批令牌" type="password" value={adminApprovalToken} onChange={(e) => onAdminApprovalTokenChange(e.target.value)} />
        </label>
      </div>
      <div className="ops-two-col admin-create-grid">
        <label className="admin-field">
          <span>新管理员令牌</span>
          <input placeholder="至少 12 位" type="password" value={newAdminApprovalToken} onChange={(e) => onNewAdminApprovalTokenChange(e.target.value)} />
        </label>
        <label className="admin-field">
          <span>工单号</span>
          <input placeholder="例如：SEC-2026-001" value={adminTicketId} onChange={(e) => onAdminTicketIdChange(e.target.value)} />
        </label>
      </div>
      <div className="ops-two-col admin-create-grid">
        <label className="admin-field">
          <span>创建原因</span>
          <input placeholder="请输入创建原因（至少 5 个字符）" value={adminReason} onChange={(e) => onAdminReasonChange(e.target.value)} />
        </label>
        <div className="admin-create-actions">
          <button type="button" disabled={creatingAdmin} onClick={onCreateAdmin}>
            {creatingAdmin ? "创建中..." : "创建管理员"}
          </button>
        </div>
      </div>
    </main>
  );
}
