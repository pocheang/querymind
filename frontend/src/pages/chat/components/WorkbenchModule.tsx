import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";

type Props = {
  title: string;
  description: string;
  status: ReactNode;
  statusVariant?: BadgeProps["variant"];
  /** The dot colour that identifies the module, as in the design's workbench cards. */
  accent: "brand" | "info" | "success" | "warning";
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
};

const ACCENT_DOT = {
  brand: "bg-brand-accent",
  info: "bg-info",
  success: "bg-success",
  warning: "bg-warning",
} as const;

/**
 * One collapsible card in the sidebar workbench.
 *
 * Four of these were written out longhand with identical markup; the only
 * things that varied were the copy, the status chip and which piece of state
 * they toggled.
 */
export function WorkbenchModule({
  title,
  description,
  status,
  statusVariant = "neutral",
  accent,
  open,
  onToggle,
  children,
}: Readonly<Props>) {
  return (
    <section className="glass-card rounded-card">
      <button
        type="button"
        className="flex w-full items-center gap-2 p-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] rounded-card"
        aria-expanded={open}
        onClick={onToggle}
      >
        <span className={cn("size-2 shrink-0 rounded-pill", ACCENT_DOT[accent])} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[11px] font-semibold text-ink">{title}</span>
          <span className="block truncate text-[10px] text-ink-muted">{description}</span>
        </span>
        <Badge variant={statusVariant} size="xs" mono className="shrink-0">
          {status}
        </Badge>
        <ChevronDown
          className={cn("size-3.5 shrink-0 text-ink-faint transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      {open && <div className="space-y-2 border-t border-line-subtle p-2.5">{children}</div>}
    </section>
  );
}
