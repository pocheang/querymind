import * as React from "react";

import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex w-full rounded-control border border-brand-border bg-surface px-2.5 py-1.5 text-xs text-ink",
      "placeholder:text-ink-faint resize-none transition-colors",
      "focus-visible:outline-none focus-visible:border-brand-accent focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
      "disabled:cursor-not-allowed disabled:opacity-60",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
