import { AdminFormField } from "@/components/AdminFormField";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { AdminPanel, Hint, SectionHead, TwoCol } from "./components/AdminPrimitives";

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
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <AdminPanel as="main" className="mx-auto grid max-w-3xl gap-3 p-6">
      <SectionHead title={t("admin.ui.createAdmin")} />
      <Hint>{t("admin.ui.createAdminHint")}</Hint>
      <TwoCol className="gap-3.5">
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
      </TwoCol>
      <TwoCol className="gap-3.5">
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
      </TwoCol>
      <TwoCol className="gap-3.5">
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
      </TwoCol>
      <TwoCol className="gap-3.5">
        <AdminFormField
          label={t("admin.ui.reason")}
          value={adminReason}
          onChange={onAdminReasonChange}
          placeholder={t("admin.ui.reasonPlaceholder")}
        />
        <div className="grid items-end">
          <Button className="h-10 w-full" size="sm" disabled={creatingAdmin} onClick={onCreateAdmin}>
            {creatingAdmin ? t("admin.ui.creating") : t("admin.ui.createAdmin")}
          </Button>
        </div>
      </TwoCol>
    </AdminPanel>
  );
}
