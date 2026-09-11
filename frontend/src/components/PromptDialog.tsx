import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type React from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { BaseDialog } from "./BaseDialog";

type Props = {
  isOpen: boolean;
  title: string;
  message: string;
  defaultValue?: string;
  placeholder?: string;
  confirmText?: string;
  cancelText?: string;
  multiline?: boolean;
  inputType?: "text" | "password";
  onConfirm: (value: string) => void;
  onCancel: () => void;
};

export function PromptDialog({
  isOpen,
  title,
  message,
  defaultValue = "",
  placeholder,
  confirmText,
  cancelText,
  multiline = false,
  inputType = "text",
  onConfirm,
  onCancel,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [value, setValue] = useState(defaultValue);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    setValue(isOpen ? defaultValue : "");
  }, [isOpen, defaultValue]);

  useEffect(() => {
    if (!isOpen) return;
    window.setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, 0);
  }, [isOpen]);

  return (
    <BaseDialog
      isOpen={isOpen}
      title={title}
      onCancel={onCancel}
      className="max-w-md"
    >
      <div className="space-y-2">
        <p className="text-xs leading-relaxed text-ink-muted">{message}</p>
        {multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            className="w-full resize-none rounded-control border border-brand-border bg-surface px-2.5 py-1.5 text-xs text-ink placeholder:text-ink-faint focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
            value={value}
            placeholder={placeholder}
            rows={5}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                onConfirm(value);
              }
            }}
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type={inputType}
            className="w-full rounded-control border border-brand-border bg-surface px-2.5 py-1.5 text-xs text-ink placeholder:text-ink-faint focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
            value={value}
            placeholder={placeholder}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                onConfirm(value);
              }
            }}
          />
        )}
      </div>
      <div className="flex items-center justify-end gap-2 pt-1">
        <Button variant="secondary" size="sm" onClick={onCancel}>
          {cancelText || t("common.cancel")}
        </Button>
        <Button size="sm" onClick={() => onConfirm(value)}>
          {confirmText || t("common.confirm")}
        </Button>
      </div>
    </BaseDialog>
  );
}
