import { AdminFormField } from "@/components/AdminFormField";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  return (
    <main className="panel admin-create-panel">
      <div className="section-head"><strong>{t("admin.ui.createAdmin")}</strong></div>
      <p className="muted admin-create-hint">{t("admin.ui.createAdminHint")}</p>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label={t("admin.ui.adminUsername")}
          value={adminUsername}
          onChange={onAdminUsernameChange}
          placeholder={t("admin.ui.usernameExample")}
        />
        <AdminFormField
          label={t("admin.ui.adminPassword")}
          type="password"
          value={adminPassword}
          onChange={onAdminPasswordChange}
          placeholder={t("admin.ui.passwordRules")}
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label={t("admin.ui.confirmPassword")}
          type="password"
          value={adminPassword2}
          onChange={onAdminPassword2Change}
          placeholder={t("admin.ui.confirmPasswordPlaceholder")}
        />
        <AdminFormField
          label={t("admin.ui.myApprovalToken")}
          type="password"
          value={adminApprovalToken}
          onChange={onAdminApprovalTokenChange}
          placeholder={t("admin.ui.myApprovalTokenPlaceholder")}
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label={t("admin.ui.newAdminToken")}
          type="password"
          value={newAdminApprovalToken}
          onChange={onNewAdminApprovalTokenChange}
          placeholder={t("admin.ui.tokenPlaceholder")}
        />
        <AdminFormField
          label={t("admin.ui.ticketId")}
          value={adminTicketId}
          onChange={onAdminTicketIdChange}
          placeholder={t("admin.ui.ticketExample")}
        />
      </div>
      <div className="ops-two-col admin-create-grid">
        <AdminFormField
          label={t("admin.ui.reason")}
          value={adminReason}
          onChange={onAdminReasonChange}
          placeholder={t("admin.ui.reasonPlaceholder")}
        />
        <div className="admin-create-actions">
          <button type="button" className="primary-action-btn" disabled={creatingAdmin} onClick={onCreateAdmin}>
            {creatingAdmin ? t("admin.ui.creating") : t("admin.ui.createAdmin")}
          </button>
        </div>
      </div>
    </main>
  );
}
