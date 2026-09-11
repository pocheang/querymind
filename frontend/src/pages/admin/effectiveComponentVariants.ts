import { cva, type VariantProps } from "class-variance-authority";

/**
 * The status table for the "effective configuration" rows.
 *
 * Written as a variant table rather than `admin-effective-${status}` for the
 * reason this project keeps variant tables at all: a template literal produces class
 * names nothing can check against the stylesheet, and this project has already
 * shipped a rule that never matched anything.
 *
 * It very nearly happened again here. The first draft interpolated the status,
 * and the backend can emit four of them -- active, degraded, disabled,
 * unavailable -- while the CSS defined row styling for two. `disabled` and
 * `unavailable` would have rendered with the neutral default border, which is
 * exactly what "no rule matched" looks like, so nothing would have appeared
 * wrong. With the table, `VariantProps` makes the four a type and every one of
 * them has a class here.
 *
 * The classes are Tailwind utilities now rather than names in
 * `styles/pages/admin/ops.css`, which is deleted -- but the argument for the
 * table is unchanged, and stronger: a `cva()` entry per status is the only
 * thing that guarantees all four are spelled somewhere.
 */
export const effectiveRow = cva(
  "grid grid-cols-[minmax(7rem,auto)_auto_1fr] items-center gap-x-3 gap-y-2 rounded-control border-l-[3px] bg-surface-muted px-3 py-2",
  {
    variants: {
      status: {
        active: "border-l-info",
        degraded: "border-l-warning",
        disabled: "border-l-ink-muted",
        unavailable: "border-l-ink-muted",
      },
    },
    defaultVariants: { status: "active" },
  }
);

export const effectiveStatusPill = cva(
  "justify-self-start rounded-pill px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-wider",
  {
    variants: {
      status: {
        active: "bg-info-surface text-info",
        degraded: "bg-warning-surface text-warning",
        disabled: "bg-surface-muted text-ink-muted",
        unavailable: "bg-surface-muted text-ink-muted",
      },
    },
    defaultVariants: { status: "active" },
  }
);

export type EffectiveStatus = NonNullable<VariantProps<typeof effectiveRow>["status"]>;
