import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { RowActions } from "./AdminPrimitives";
import { ADMIN_FIELD } from "./adminClasses";

type LogLimitActionsProps = {
  limit: number;
  onLimitChange: (limit: number) => void;
  onRefresh: () => void;
  options?: number[];
};

export function LogLimitActions({
  limit,
  onLimitChange,
  onRefresh,
  options = [100, 200, 500],
}: Readonly<LogLimitActionsProps>) {
  const { t } = useTranslation();

  return (
    <RowActions className="flex-nowrap justify-end gap-1.5 rounded-card border border-line bg-brand-surface-hover p-1">
      <select
        className={`${ADMIN_FIELD} w-auto min-w-32 shrink-0 font-mono font-semibold`}
        value={limit}
        onChange={(e) => onLimitChange(Number(e.target.value) || 200)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {t(`admin.ui.last${opt}`, `Last ${opt}`)}
          </option>
        ))}
      </select>
      <Button variant="secondary" size="xs" onClick={onRefresh}>
        {t("common.refresh")}
      </Button>
    </RowActions>
  );
}
