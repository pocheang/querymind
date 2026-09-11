import { useState, type ChangeEvent, type KeyboardEvent } from "react";
import { Check, Eye, EyeOff, Lock, Mail, User, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface AuthInputProps {
  id: string;
  type?: "text" | "password" | "email";
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  autoComplete?: string;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
  icon: "user" | "lock" | "email";
  isValid?: boolean | null;
  onClear?: () => void;
  className?: string;
  disabled?: boolean;
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
  isValid = null,
  onClear,
  className,
  disabled = false,
}: Readonly<AuthInputProps>) {
  const Icon = ICONS[icon];
  const [showPassword, setShowPassword] = useState(false);
  const [isCapsLock, setIsCapsLock] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const isPassword = type === "password";
  const actualType = isPassword ? (showPassword ? "text" : "password") : type;

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (isPassword) {
      setIsCapsLock(e.getModifierState("CapsLock"));
    }
    onKeyDown?.(e);
  };

  const handleKeyUp = (e: KeyboardEvent<HTMLInputElement>) => {
    if (isPassword) {
      setIsCapsLock(e.getModifierState("CapsLock"));
    }
  };

  return (
    <div className={cn("field-shell group relative flex h-11 items-center gap-3 rounded-xl border bg-stone-50/50 px-3.5 transition-all duration-150 border-stone-200 hover:border-stone-300 hover:bg-stone-50 focus-within:bg-white focus-within:border-amber-500 focus-within:ring-2 focus-within:ring-amber-200/60 shadow-xs", isValid === false && value.length > 0 && "border-rose-400 focus-within:border-rose-500 focus-within:ring-rose-200/60", className)}>
      <Icon
        className={cn(
          "size-4.5 shrink-0 transition-colors duration-150",
          isFocused ? "text-amber-600" : "text-stone-400 group-hover:text-stone-600"
        )}
        aria-hidden="true"
      />
      <input
        id={id}
        type={actualType}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        onKeyDown={handleKeyDown}
        onKeyUp={handleKeyUp}
        onFocus={() => setIsFocused(true)}
        onBlur={() => {
          setIsFocused(false);
          setIsCapsLock(false);
        }}
        disabled={disabled}
        className="w-full bg-transparent text-sm sm:text-base font-medium text-stone-900 placeholder:text-stone-400 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      />
      <div className="flex items-center gap-1.5 shrink-0">
        {isCapsLock && isFocused && (
          <span
            className="flex items-center gap-0.5 rounded px-2 py-0.5 text-xs font-mono font-bold text-amber-900 bg-amber-100 border border-amber-300 select-none"
            title="Caps Lock is ON"
          >
            ⇪ CAPS
          </span>
        )}
        {onClear && value.length > 0 && !disabled && (
          <button
            type="button"
            tabIndex={-1}
            onClick={onClear}
            className="rounded p-1 text-stone-400 hover:text-stone-700 focus-visible:outline-none transition-colors"
            aria-label="Clear input"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        )}
        {isValid === true && (
          <div
            className="flex size-4.5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
            aria-hidden="true"
          >
            <Check className="size-3" strokeWidth={3} />
          </div>
        )}
        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((prev) => !prev)}
            className="rounded p-1 text-stone-400 hover:text-stone-700 focus-visible:outline-none transition-colors"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeOff className="size-4.5" aria-hidden="true" />
            ) : (
              <Eye className="size-4.5" aria-hidden="true" />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
