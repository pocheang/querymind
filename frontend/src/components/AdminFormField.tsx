import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AdminFormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "password" | "number";
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  children?: ReactNode;
}

/**
 * A labelled admin input.
 *
 * The label wraps the control rather than pointing at it with `htmlFor`, which
 * is what gives the input its accessible name -- `AdminConfigEditor.test.tsx`
 * finds every config field with `getByRole("textbox", { name: "TOP_K" })`, so
 * that association has to survive any restyling.
 */
export function AdminFormField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  disabled = false,
  required = false,
  className = "",
}: Readonly<AdminFormFieldProps>) {
  return (
    <label className={cn("block space-y-1", className)}>
      <Label asChild>
        <span>
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </span>
      </Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </label>
  );
}

interface AdminFormSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }> | string[];
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

/**
 * The select sibling.
 *
 * A native select rather than the Radix one: these forms hold long option
 * lists (model names, log levels) that the platform control handles better on
 * a phone, and nothing here needs a custom option renderer.
 */
export function AdminFormSelect({
  label,
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  required = false,
  className = "",
}: Readonly<AdminFormSelectProps>) {
  const normalizedOptions = options.map((opt) => (typeof opt === "string" ? { value: opt, label: opt } : opt));

  return (
    <label className={cn("block space-y-1", className)}>
      <Label asChild>
        <span>
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </span>
      </Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="h-8 w-full rounded-control border border-brand-border bg-surface px-2 text-xs text-ink transition-colors focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {normalizedOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}
