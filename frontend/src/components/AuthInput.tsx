import type { ChangeEvent, KeyboardEvent } from "react";

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

const ICONS = {
  user: (
    <path d="M12 12a4 4 0 1 0-4-4a4 4 0 0 0 4 4Zm0 2c-3.33 0-6 2.02-6 4.5V20h12v-1.5c0-2.48-2.67-4.5-6-4.5Z" />
  ),
  lock: (
    <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
  ),
  email: (
    <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5l-8-5V6l8 5l8-5v2z" />
  )
};

export function AuthInput({
  id,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
  onKeyDown,
  icon
}: AuthInputProps) {
  return (
    <div className="auth-input-shell">
      <span className="auth-input-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          {ICONS[icon]}
        </svg>
      </span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        onKeyDown={onKeyDown}
      />
    </div>
  );
}
