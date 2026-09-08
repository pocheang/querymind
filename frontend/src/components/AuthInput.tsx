import type { ChangeEvent, KeyboardEvent } from "react";
import { Lock, Mail, User } from "lucide-react";

interface AuthInputProps {
  id: string;
  type?: "text" | "password" | "email";
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  autoComplete?: string;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
  icon: "user" | "lock" | "email";
}

const ICONS = { user: User, lock: Lock, email: Mail } as const;

/**
 * A text field with a leading icon, for the auth pages.
 *
 * `placeholder` stays required and stays the literal it was: scripts/
 * screenshots.mjs finds these fields with `getByPlaceholder("Username")` and
 * `getByPlaceholder("Password")`.
 */
export function AuthInput({
  id,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
  onKeyDown,
  icon,
}: Readonly<AuthInputProps>) {
  const Icon = ICONS[icon];

  return (
    <div className="field-shell flex items-center gap-2 rounded-control border border-brand-border bg-surface px-2.5 py-2 transition-all focus-within:border-brand-accent focus-within:ring-2 focus-within:ring-[var(--brand-ring)]">
      <Icon className="size-4 shrink-0 text-brand-accent" aria-hidden="true" />
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        onKeyDown={onKeyDown}
        className="w-full bg-transparent text-xs text-ink placeholder:text-ink-faint focus-visible:outline-none"
      />
    </div>
  );
}
