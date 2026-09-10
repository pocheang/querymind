import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * The frosted content surface. `glass-card` owns its border width, style and
 * colour (see core/app-utilities.css) -- in the design prototype the class set
 * only `border-color`, so every call site had to add `border border-amber-200/80`
 * of its own and the two then fought over which colour won.
 */
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("glass-card rounded-card", className)} {...props} />
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center justify-between gap-2 p-3", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

// typescript:S6850 sees no heading content here because it does not trace the
// `{...props}` spread back to the `children` every call site actually passes
// (`<CardTitle>{t("...")}</CardTitle>`, never a bare `<CardTitle />`).
export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-xs font-bold tracking-tight text-ink", className)} {...props} />
  )
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => <p ref={ref} className={cn("text-[11px] text-ink-muted", className)} {...props} />
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("p-3 pt-0", className)} {...props} />
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-2 p-3 pt-0", className)} {...props} />
  )
);
CardFooter.displayName = "CardFooter";
