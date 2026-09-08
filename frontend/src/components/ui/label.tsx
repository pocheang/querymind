import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";

import { cn } from "@/lib/utils";

export const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(
      "text-[10px] font-semibold uppercase tracking-wider text-ink-muted",
      "peer-disabled:cursor-not-allowed peer-disabled:opacity-60",
      className
    )}
    {...props}
  />
));
Label.displayName = LabelPrimitive.Root.displayName;
