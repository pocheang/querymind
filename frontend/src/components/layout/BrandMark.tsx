import { Zap } from "lucide-react";

import { cn } from "@/lib/utils";

const SIZES = {
  sm: { box: "size-7 rounded-control", icon: "size-3.5" },
  md: { box: "size-8 rounded-control", icon: "size-4" },
  lg: { box: "size-16 rounded-panel ring-4", icon: "size-8" },
} as const;

/**
 * The bolt-in-a-gradient-square that identifies the product: the top nav
 * logo, the assistant's avatar and the welcome screen's hero all use it.
 *
 * This is the one place `--brand-mark-gradient` is allowed -- the bright
 * amber-600 -> yellow-500 ramp from the design prototype, which is too light
 * to carry text at AA. WCAG 1.4.3 exempts logotypes, and the glyph on it is
 * decorative (every use is paired with a real text label or an aria-label),
 * so the exemption applies. Do not reuse this gradient behind content.
 */
export function BrandMark({ size = "md", className }: Readonly<{ size?: keyof typeof SIZES; className?: string }>) {
  const s = SIZES[size];
  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center text-white shadow-elev-2 ring-1 ring-brand-border-strong",
        "bg-[image:var(--brand-mark-gradient)]",
        s.box,
        className
      )}
      aria-hidden="true"
    >
      <Zap className={s.icon} strokeWidth={2} />
    </span>
  );
}
