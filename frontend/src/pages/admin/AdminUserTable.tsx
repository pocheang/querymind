import type { AdminUserSummary } from "@/types/api";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CellStack, RowActions } from "./components/AdminPrimitives";
import { ADMIN_FIELD, ADMIN_TABLE, ADMIN_TABLE_WIDE } from "./components/adminClasses";

type Props = {
  users: AdminUserSummary[];
  roleOptions: string[];
  statusOptions: string[];
  onUpdateRole: (user: AdminUserSummary, role: string) => Promise<void>;
  onUpdateStatus: (user: AdminUserSummary, status: string) => Promise<void>;
  onAddCredits: (user: AdminUserSummary) => Promise<void>;
  onOpenClassEditor: (user: AdminUserSummary) => void;
  onResetPassword: (user: AdminUserSummary) => Promise<void>;
  onResetApprovalToken: (user: AdminUserSummary) => Promise<void>;
};

/**
 * The first four columns stay put while the rest scrolls, so each needs its
 * own `left` offset -- the running total of the widths before it. They are
 * written out rather than computed because the widths are also written out:
 * two derived numbers that must agree are worse than one pair side by side.
 */
const STICKY = [
  "sticky left-0 z-[2] w-[220px] bg-surface shadow-[1px_0_0_var(--border-neutral)]",
  "sticky left-[220px] z-[2] w-[120px] bg-surface shadow-[1px_0_0_var(--border-neutral)]",
  "sticky left-[340px] z-[2] w-[150px] bg-surface shadow-[1px_0_0_var(--border-neutral)]",
  "sticky left-[490px] z-[2] w-[236px] bg-surface shadow-[2px_0_0_var(--border-neutral-strong)]",
];
/** The header half sits one layer higher and keeps the header's own fill. */
const STICKY_HEAD = "z-[3] bg-brand-surface-hover shadow-[1px_0_0_var(--brand-border)]";
/** A hovered row must repaint the sticky cells too, or the scroll shows through. */
const STICKY_CELL = "group-hover/row:bg-brand-surface";

/** A small uppercase state pill: online, token set, unlimited credits. */
const FLAG = "inline-flex min-h-[24px] items-center justify-center whitespace-nowrap rounded-pill border px-2.5 text-xs font-bold uppercase tracking-wide";
const FLAG_TONE = {
  on: "border-success-border bg-success-surface text-success",
  active: "border-info-border bg-info-surface text-info",
  off: "border-line-strong bg-brand-surface-hover text-ink-muted",
};

export function AdminUserTable({
  users,
  roleOptions,
  statusOptions,
  onUpdateRole,
  onUpdateStatus,
  onAddCredits,
  onOpenClassEditor,
  onResetPassword,
  onResetApprovalToken,
}: Readonly<Props>) {
  const { t } = useTranslation();

  const renderValue = (value?: string | null) => value?.trim() || "-";

  return (
    <table className={cn(ADMIN_TABLE, ADMIN_TABLE_WIDE, "min-w-[1320px] overflow-visible")}>
      <thead>
        <tr>
          <th className={cn(STICKY[0], STICKY_HEAD)}>{t("admin.ui.username")}</th>
          <th className={cn(STICKY[1], STICKY_HEAD)}>{t("admin.ui.role")}</th>
          <th className={cn(STICKY[2], STICKY_HEAD)}>{t("admin.ui.status")}</th>
          <th className={cn(STICKY[3], STICKY_HEAD)}>{t("admin.ui.credits")}</th>
          <th className="w-[180px]">{t("admin.ui.operation")}</th>
          <th className="w-[180px]">{t("admin.ui.businessUnit")}</th>
          <th className="w-[190px]">{t("admin.ui.type")}</th>
          <th className="w-[110px]">{t("admin.ui.createdBy")}</th>
          <th>{t("admin.ui.token")}</th>
        </tr>
      </thead>
      <tbody>
        {users.map((row) => (
          <tr key={row.user_id} className="group/row">
            <td className={cn(STICKY[0], STICKY_CELL)}>
              <CellStack>
                <span className="block truncate font-bold text-ink">{row.username}</span>
                <span className="truncate font-mono text-xs text-ink/75" title={row.user_id}>
                  {row.user_id}
                </span>
              </CellStack>
            </td>
            <td className={cn(STICKY[1], STICKY_CELL)}>
              <select className={ADMIN_FIELD} value={row.role} onChange={(e) => void onUpdateRole(row, e.target.value)}>
                {([...(row.role === "admin" ? ["admin"] : []), ...roleOptions] as string[]).map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </td>
            <td className={cn(STICKY[2], STICKY_CELL)}>
              <CellStack>
                <select
                  className={ADMIN_FIELD}
                  value={row.status}
                  onChange={(e) => void onUpdateStatus(row, e.target.value)}
                >
                  {statusOptions.map((x) => (
                    <option key={x} value={x}>
                      {x}
                    </option>
                  ))}
                </select>
                <div className="flex flex-wrap gap-1.5">
                  <span className={cn(FLAG, row.is_online ? FLAG_TONE.on : FLAG_TONE.off)}>
                    {row.is_online ? t("admin.ui.online") : t("admin.ui.offline")}
                  </span>
                  <span className={cn(FLAG, row.is_online_10m ? FLAG_TONE.active : FLAG_TONE.off)}>
                    {row.is_online_10m ? t("admin.ui.active10m") : "-"}
                  </span>
                </div>
              </CellStack>
            </td>
            <td className={cn(STICKY[3], STICKY_CELL)}>
              <span className={cn(FLAG, FLAG_TONE.on)}>
                {(row.role || "").toLowerCase() === "admin" ? t("admin.ui.unlimited") : row.credit_balance}
              </span>
            </td>
            <td>
              <RowActions className="gap-1.5">
                <Button variant="secondary" size="xs" onClick={() => onOpenClassEditor(row)}>
                  {t("admin.ui.classify")}
                </Button>
                <Button variant="secondary" size="xs" onClick={() => void onResetPassword(row)}>
                  {t("admin.ui.resetPassword")}
                </Button>
                {(row.role || "").toLowerCase() !== "admin" ? (
                  <Button variant="secondary" size="xs" onClick={() => void onAddCredits(row)}>
                    {t("admin.ui.addCredits")}
                  </Button>
                ) : null}
                {(row.role || "").toLowerCase() === "admin" ? (
                  <Button variant="secondary" size="xs" onClick={() => void onResetApprovalToken(row)}>
                    {t("admin.ui.resetToken")}
                  </Button>
                ) : null}
              </RowActions>
            </td>
            <td>
              <CellStack>
                <span className="truncate">{renderValue(row.business_unit)}</span>
                <span className="truncate font-mono text-xs text-ink/75">{renderValue(row.department)}</span>
              </CellStack>
            </td>
            <td>
              <CellStack>
                <span className="truncate">{renderValue(row.user_type)}</span>
                <span className="truncate font-mono text-xs text-ink/75">{renderValue(row.data_scope)}</span>
              </CellStack>
            </td>
            <td>
              <CellStack>
                <span className="truncate">{renderValue(row.created_by_username || row.created_by_user_id)}</span>
                <span className="truncate font-mono text-xs text-ink/75">
                  {renderValue(row.admin_ticket_id)}
                </span>
              </CellStack>
            </td>
            <td>
              <span className={cn(FLAG, row.has_admin_approval_token ? FLAG_TONE.on : FLAG_TONE.off)}>
                {row.has_admin_approval_token ? t("admin.ui.tokenSet") : t("admin.ui.tokenUnset")}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
