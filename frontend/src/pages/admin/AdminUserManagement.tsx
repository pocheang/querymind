import { useMemo, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AdminUserTable } from "@/pages/admin/AdminUserTable";
import { AdminPagination } from "@/components/AdminPagination";
import type { AdminUserSummary } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  AdminField,
  AdminPanel,
  AdminSkeleton,
  FilterGrid,
  Hint,
  RowActions,
  SectionHead,
  TwoCol,
} from "./components/AdminPrimitives";
import { ADMIN_FIELD, ADMIN_TABLE_WRAP } from "./components/adminClasses";

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
  onAddCredits: (target: AdminUserSummary) => Promise<void>;
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
  onAddCredits,
  onOpenClassEditor,
  onResetPassword,
  onResetApprovalToken,
}: Readonly<Props>) {
  const { t } = useTranslation();
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

  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [kw, fRole, fStatus, fOnline]);

  const paginatedUsers = useMemo(() => {
    const startIdx = (currentPage - 1) * pageSize;
    return filteredUsers.slice(startIdx, startIdx + pageSize);
  }, [filteredUsers, currentPage, pageSize]);

  return (
    <main className="space-y-6">
      <SectionHead title={t("admin.userManagement")}>
<Button variant="secondary" size="xs" onClick={onLoadUsers}>{t("common.refresh")}</Button></SectionHead>
      <Hint>{t("admin.ui.usersHint")}</Hint>

      <FilterGrid>
        <AdminField label={t("admin.ui.search")}>
          <input className={ADMIN_FIELD} placeholder={t("admin.ui.userSearchPlaceholder")} value={kw} onChange={(e) => onKwChange(e.target.value)} />
        </AdminField>
        <AdminField label={t("admin.ui.role")}>
          <select className={ADMIN_FIELD} value={fRole} onChange={(e) => onFRoleChange(e.target.value)}>
            <option value="">{t("admin.ui.allRoles")}</option>
            <option value="admin">admin</option>
            <option value="analyst">analyst</option>
            <option value="viewer">viewer</option>
          </select>
        </AdminField>
      </FilterGrid>

      <FilterGrid>
        <AdminField label={t("admin.ui.status")}>
          <select className={ADMIN_FIELD} value={fStatus} onChange={(e) => onFStatusChange(e.target.value)}>
            <option value="">{t("admin.ui.allStatuses")}</option>
            <option value="active">active</option>
            <option value="disabled">disabled</option>
          </select>
        </AdminField>
        <AdminField label={t("admin.ui.onlineStatus")}>
          <select className={ADMIN_FIELD} value={fOnline} onChange={(e) => onFOnlineChange(e.target.value)}>
            <option value="">{t("admin.ui.allOnlineStatuses")}</option>
            <option value="online_10m">{t("admin.ui.online10m")}</option>
            <option value="online">{t("admin.ui.online")}</option>
            <option value="offline">{t("admin.ui.offline")}</option>
          </select>
        </AdminField>
      </FilterGrid>

      {editingUser && (
        <AdminPanel as="div" className="mb-3">
          <SectionHead title={t("admin.ui.userClassification", { username: editingUser.username })}>
<Button variant="secondary" size="xs" onClick={() => onEditingUserChange(null)}>{t("common.cancel")}</Button></SectionHead>
          <TwoCol>
            <input className={ADMIN_FIELD} placeholder={t("admin.ui.businessUnit")} value={editBu} onChange={(e) => onEditBuChange(e.target.value)} />
            <input className={ADMIN_FIELD} placeholder={t("admin.ui.department")} value={editDept} onChange={(e) => onEditDeptChange(e.target.value)} />
          </TwoCol>
          <TwoCol>
            <input className={ADMIN_FIELD} placeholder={t("admin.ui.userType")} value={editType} onChange={(e) => onEditTypeChange(e.target.value)} />
            <input className={ADMIN_FIELD} placeholder={t("admin.ui.dataScope")} value={editScope} onChange={(e) => onEditScopeChange(e.target.value)} />
          </TwoCol>
          <RowActions>
            <Button size="sm" disabled={savingClass} onClick={onSaveClass}>
              {savingClass ? t("admin.ui.saving") : t("admin.ui.saveClassification")}
            </Button>
          </RowActions>
        </AdminPanel>
      )}

      {loadingUsers && <AdminSkeleton />}
      {!loadingUsers && (
        <>
          {filteredUsers.length > 0 && (
            <AdminPagination
              totalItems={filteredUsers.length}
              currentPage={currentPage}
              pageSize={pageSize}
              pageSizeOptions={[10, 20, 50]}
              onPageChange={setCurrentPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setCurrentPage(1);
              }}
            />
          )}
          <div className={ADMIN_TABLE_WRAP}>
            <AdminUserTable
              users={paginatedUsers}
              roleOptions={roleOptions}
              statusOptions={statusOptions}
              onUpdateRole={onUpdateRole}
              onUpdateStatus={onUpdateStatus}
              onAddCredits={onAddCredits}
              onOpenClassEditor={onOpenClassEditor}
              onResetPassword={onResetPassword}
              onResetApprovalToken={onResetApprovalToken}
            />
          </div>
        </>
      )}
    </main>
  );
}
