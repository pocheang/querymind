import { ReactNode } from "react";

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

export function AdminFormField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  disabled = false,
  required = false,
  className = "",
}: AdminFormFieldProps) {
  return (
    <label className={`admin-field ${className}`.trim()}>
      <span>
        {label}
        {required && <span className="required">*</span>}
      </span>
      <input
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

export function AdminFormSelect({
  label,
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  required = false,
  className = "",
}: AdminFormSelectProps) {
  const normalizedOptions = options.map((opt) =>
    typeof opt === "string" ? { value: opt, label: opt } : opt
  );

  return (
    <label className={`admin-field ${className}`.trim()}>
      <span>
        {label}
        {required && <span className="required">*</span>}
      </span>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
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
