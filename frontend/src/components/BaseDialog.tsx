import { useEffect, useId, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type Props = {
  isOpen: boolean;
  title: string;
  className?: string;
  onCancel: () => void;
  children: ReactNode;
};

export function BaseDialog({
  isOpen,
  title,
  className,
  onCancel,
  children,
}: Readonly<Props>) {
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
    <div
      className="confirm-dialog-overlay fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4 backdrop-blur-sm"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <dialog
        open
        className={cn(
          "glass-panel w-full space-y-3 rounded-panel border-brand-border-strong p-5 shadow-elev-3 animate-in fade-in-0 zoom-in-95 m-0 max-h-none max-w-none bg-transparent",
          className
        )}
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h3 className="text-sm font-bold text-ink" id={titleId}>
          {title}
        </h3>
        {children}
      </dialog>
    </div>
  );
}
