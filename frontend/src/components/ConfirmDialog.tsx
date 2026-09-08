import { useEffect, useId } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

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
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    // The backdrop is scenery, not a control: role="presentation" says so, and
    // dismissing on a click that landed on the backdrop itself replaces the
    // inner stopPropagation handler that used to exist only to undo this one.
    // Escape is wired above and is the keyboard route.
    //
    // Deliberately NOT a Radix AlertDialog. This element's contract --
    // `.confirm-dialog-overlay`, role="presentation", no tabindex, and the
    // click/Escape split above -- is asserted by ConfirmDialog.test.tsx and was
    // arrived at on purpose; Radix supplies a different one. Only the paint
    // changed here.
    <div
      className="confirm-dialog-overlay fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4 backdrop-blur-sm"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        className="glass-panel w-full max-w-sm space-y-3 rounded-panel border-brand-border-strong p-5 shadow-elev-3 animate-in fade-in-0 zoom-in-95"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h3 className="text-sm font-bold text-ink" id={titleId}>
          {title}
        </h3>
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
      </div>
    </div>
  );
}
