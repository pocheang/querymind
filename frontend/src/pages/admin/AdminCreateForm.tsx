import { AdminFormField } from "@/components/AdminFormField";

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
        <AdminFormField
          label="管理员用户名"
          value={adminUsername}
          onChange={onAdminUsernameChange}
          placeholder="例如：sec_admin_01"
        />
        <AdminFormField
          label="管理员密码"
          type="password"
          value={adminPassword}
          onChange={onAdminPasswordChange}
          placeholder="至少 12 位，含大小写、数字和特殊字符"
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label="确认密码"
          type="password"
          value={adminPassword2}
          onChange={onAdminPassword2Change}
          placeholder="再次输入密码"
        />
        <AdminFormField
          label="我的审批令牌"
          type="password"
          value={adminApprovalToken}
          onChange={onAdminApprovalTokenChange}
          placeholder="当前管理员审批令牌"
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label="新管理员令牌"
          type="password"
          value={newAdminApprovalToken}
          onChange={onNewAdminApprovalTokenChange}
          placeholder="至少 12 位"
        />
        <AdminFormField
          label="工单号"
          value={adminTicketId}
          onChange={onAdminTicketIdChange}
          placeholder="例如：SEC-2026-001"
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label="创建原因"
          value={adminReason}
          onChange={onAdminReasonChange}
          placeholder="请输入创建原因（至少 5 个字符）"
        />
        <div className="admin-create-actions">
          <button type="button" disabled={creatingAdmin} onClick={onCreateAdmin}>
            {creatingAdmin ? "创建中..." : "创建管理员"}
          </button>
        </div>
      </div>
    </main>
  );
}
