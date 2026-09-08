import * as React from "react";

import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, type, ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      "flex h-8 w-full rounded-control border border-brand-border bg-surface px-2.5 py-1.5 text-xs text-ink",
      "placeholder:text-ink-faint",
      "transition-colors",
      "focus-visible:outline-none focus-visible:border-brand-accent focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
      "disabled:cursor-not-allowed disabled:opacity-60 disabled:bg-surface-muted",
      "file:mr-2 file:rounded-control file:border-0 file:bg-brand-surface file:px-2 file:py-1 file:text-xs file:text-brand-text",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";
