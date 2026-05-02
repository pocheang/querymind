import type React from "react";
import "./Input.css";

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  inputSize?: "sm" | "md" | "lg";
  variant?: "outlined" | "filled";
}

export function Input({
  label,
  error,
  helperText,
  fullWidth = false,
  inputSize = "md",
  variant = "outlined",
  className = "",
  id,
  ...props
}: InputProps) {
  const inputId = id || `input-${Math.random().toString(36).slice(2, 9)}`;
  const hasError = !!error;

  const wrapperClasses = ["input-wrapper", fullWidth ? "input-full-width" : ""].filter(Boolean).join(" ");

  const inputClasses = [
    "input",
    `input-${variant}`,
    `input-${inputSize}`,
    hasError ? "input-error" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapperClasses}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <input id={inputId} className={inputClasses} {...props} />
      {error && <span className="input-error-text">{error}</span>}
      {!error && helperText && <span className="input-helper-text">{helperText}</span>}
    </div>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  textareaSize?: "sm" | "md" | "lg";
  variant?: "outlined" | "filled";
}

export function Textarea({
  label,
  error,
  helperText,
  fullWidth = false,
  textareaSize = "md",
  variant = "outlined",
  className = "",
  id,
  ...props
}: TextareaProps) {
  const textareaId = id || `textarea-${Math.random().toString(36).slice(2, 9)}`;
  const hasError = !!error;

  const wrapperClasses = ["input-wrapper", fullWidth ? "input-full-width" : ""].filter(Boolean).join(" ");

  const textareaClasses = [
    "textarea",
    `input-${variant}`,
    `input-${textareaSize}`,
    hasError ? "input-error" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapperClasses}>
      {label && (
        <label htmlFor={textareaId} className="input-label">
          {label}
        </label>
      )}
      <textarea id={textareaId} className={textareaClasses} {...props} />
      {error && <span className="input-error-text">{error}</span>}
      {!error && helperText && <span className="input-helper-text">{helperText}</span>}
    </div>
  );
}
