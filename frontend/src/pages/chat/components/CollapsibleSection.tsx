import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

type Props = {
  title: ReactNode;
  ariaLabel: string;
  open?: boolean;
  className?: string;
  children: ReactNode;
};

/**
 * A `<details>`/`<summary>` disclosure styled as one of the assistant card's
 * stacked blocks. Native rather than state-driven so it works before hydration
 * and keeps keyboard and find-in-page behaviour for free.
 */
export function CollapsibleSection({ title, ariaLabel, open, className, children }: Readonly<Props>) {
  return (
    <details
      open={open}
      className={cn("group rounded-card border border-line bg-surface-inset p-3 text-xs sm:text-sm", className)}
    >
      <summary
        aria-label={ariaLabel}
        className="flex cursor-pointer list-none items-center gap-1.5 text-xs sm:text-sm font-semibold text-ink marker:content-none hover:text-brand-text [&::-webkit-details-marker]:hidden"
      >
        <ChevronRight
          className="size-3.5 shrink-0 text-brand-accent transition-transform group-open:rotate-90"
          aria-hidden="true"
        />
        {title}
      </summary>
      <div className="mt-2 border-t border-line-subtle pt-2">{children}</div>
    </details>
  );
}
