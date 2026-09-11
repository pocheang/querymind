import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { BaseDialog } from "./BaseDialog";

type Props = {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDanger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  isDanger = false,
  onConfirm,
  onCancel,
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <BaseDialog
      isOpen={isOpen}
      title={title}
      onCancel={onCancel}
      className="max-w-sm"
    >
      <p className="text-xs leading-relaxed text-ink-muted">{message}</p>
      <div className="flex items-center justify-end gap-2 pt-1">
        <Button variant="secondary" size="sm" onClick={onCancel}>
          {cancelText || t("common.cancel")}
        </Button>
        <Button
          variant={isDanger ? "destructive" : "default"}
          size="sm"
          className={cn(isDanger && "danger")}
          onClick={onConfirm}
          autoFocus
        >
          {confirmText || t("common.confirm")}
        </Button>
      </div>
    </BaseDialog>
  );
}
