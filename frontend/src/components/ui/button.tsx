import * as React from "react";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/lib/utils";
import { buttonVariants, type ButtonVariants } from "./buttonVariants";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  ButtonVariants & {
    /** Render the child element instead of a `<button>`, keeping the styling. */
    asChild?: boolean;
  };

/**
 * `React.forwardRef` rather than the ref-as-prop form: this project is on
 * React 18, where a function component receives no `ref` in props.
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        // A button inside a form defaults to `submit`, which has surprised
        // this codebase before. Only set it when we actually render one.
        type={asChild ? undefined : (type ?? "button")}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
