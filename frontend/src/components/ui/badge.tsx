import * as React from "react";

import { cn } from "@/lib/utils";
import { badgeVariants, type BadgeVariants } from "./badgeVariants";

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & BadgeVariants;

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, size, mono, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant, size, mono }), className)} {...props} />
  )
);
Badge.displayName = "Badge";
