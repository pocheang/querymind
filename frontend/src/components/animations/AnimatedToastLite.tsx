/**
 * AnimatedToastLite - 轻量级Toast通知组件（CSS-only）
 *
 * 不依赖Framer Motion，使用纯CSS实现动画效果
 * 适用于对bundle大小敏感的场景
 *
 * @version 1.0.0
 * @created 2026-08-16
 */

import { useEffect, useState, createContext, useContext, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

/** Icon and tone per severity. Both are needed: colour alone does not carry
    meaning, and these sit on a warm ground where a tint is easy to miss. */
const ICONS = { info: Info, success: CheckCircle2, warning: AlertTriangle, error: XCircle } as const;
const TONE = {
  info: "border-info-border bg-info-surface/95 text-info",
  success: "border-success-border bg-success-surface/95 text-success",
  warning: "border-warning-border bg-warning-surface/95 text-warning",
  error: "border-danger-border bg-danger-surface/95 text-danger",
} as const;

export interface Toast {
  id: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  duration?: number;
}

interface AnimatedToastLiteProps {
  toast: Toast;
  index: number;
  onClose: (id: string) => void;
}

export function AnimatedToastLite({ toast, index: _index, onClose }: Readonly<AnimatedToastLiteProps>) {
  const { t } = useTranslation();
  const [isPaused, setIsPaused] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const duration = toast.duration || 4000;

  useEffect(() => {
    if (isPaused || isExiting) return;

    const timer = setTimeout(() => {
      setIsExiting(true);
      // 等待退出动画完成后再移除
      setTimeout(() => onClose(toast.id), 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [toast.id, duration, isPaused, isExiting, onClose]);

  const handleClick = () => {
    if (!isExiting) {
      setIsExiting(true);
      setTimeout(() => onClose(toast.id), 300);
    }
  };

  const Icon = ICONS[toast.type];

  return (
    <div
      className={cn(
        "pointer-events-auto relative flex w-72 items-start gap-2 overflow-hidden rounded-card border p-2.5 shadow-elev-2 backdrop-blur-md",
        "animate-in fade-in-0 slide-in-from-top-2 duration-300",
        TONE[toast.type],
        isExiting && "animate-out fade-out-0 slide-out-to-top-2 duration-300"
      )}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      role="alert"
      aria-live="polite"
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1 text-xs sm:text-sm font-medium leading-relaxed">{toast.message}</span>
      <button
        type="button"
        className="shrink-0 rounded-control p-0.5 opacity-60 transition-opacity hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
        onClick={handleClick}
        aria-label={t("toast.close")}
      >
        <X className="size-3.5" aria-hidden="true" />
      </button>

      {/* The auto-dismiss countdown. `--toast-duration` is read by the one
          keyframe this component still needs -- a width animation cannot be
          expressed as a utility because its duration is a prop. */}
      {!isPaused && !isExiting && (
        <span
          className="toast-progress absolute inset-x-0 bottom-0 h-0.5 origin-left bg-current opacity-40"
          style={{ "--toast-duration": `${duration}ms` } as React.CSSProperties}
        />
      )}
    </div>
  );
}

// Toast容器组件
interface ToastContainerProps {
  toasts: Toast[];
  onClose: (id: string) => void;
}

export function ToastContainer({ toasts, onClose }: Readonly<ToastContainerProps>) {
  return (
    <div className="pointer-events-none fixed right-5 top-5 z-50 flex flex-col gap-2">
      {toasts.map((toast, index) => (
        <AnimatedToastLite key={toast.id} toast={toast} index={index} onClose={onClose} />
      ))}
    </div>
  );
}

// Toast Context 和 Hook
interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, type: Toast["type"], duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: Toast["type"], duration?: number) => {
    const id = `toast-${crypto.randomUUID()}`;
    const newToast: Toast = { id, message, type, duration };

    setToasts((prev) => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const contextValue = useMemo(
    () => ({ toasts, addToast, removeToast }),
    [toasts, addToast, removeToast]
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  );
}

// 便捷的 Hook
export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }

  return {
    info: (message: string, duration?: number) => context.addToast(message, "info", duration),
    success: (message: string, duration?: number) => context.addToast(message, "success", duration),
    warning: (message: string, duration?: number) => context.addToast(message, "warning", duration),
    error: (message: string, duration?: number) => context.addToast(message, "error", duration),
  };
}
