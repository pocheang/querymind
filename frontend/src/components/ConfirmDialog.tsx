import type { ConfirmDialogOptions } from "@/lib/hooks/useConfirmDialog";

interface ConfirmDialogProps {
  isOpen: boolean;
  options: ConfirmDialogOptions | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ isOpen, options, onConfirm, onCancel }: ConfirmDialogProps) {
  if (!isOpen || !options) return null;

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {options.title && <h3>{options.title}</h3>}
        <p>{options.message}</p>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn-secondary">
            {options.cancelText || "取消"}
          </button>
          <button onClick={onConfirm} className="btn-danger">
            {options.confirmText || "确认"}
          </button>
        </div>
      </div>
    </div>
  );
}
