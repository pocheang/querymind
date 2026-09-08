import { cva, type VariantProps } from "class-variance-authority";

/**
 * The button shapes the design prototype repeats, as a variant table.
 *
 * This lives in its own module rather than beside the component because
 * `react-refresh/only-export-components` fires on a component file that also
 * exports a `cva()` call -- `allowConstantExport` covers literals, not call
 * expressions -- and the lint budget (`--max-warnings 25`) is a ratchet
 * sitting at exactly 25. The repo already does this twice, in
 * `admin/effectiveComponentVariants.ts`.
 *
 * On the colours: `default` and `flat` carry white text, so they use
 * `--brand` (#b45309, 5.02:1) rather than the prototype's amber-500/600
 * gradient, which measures 2.15-3.19:1 and fails AA. `soft` and `ghost` put
 * amber ON a light ground, so they use `--brand-text` (#92400e, 7.09:1).
 * `--brand-accent` (#d97706) is the prototype's original hue and survives on
 * icon strokes and borders, where 3:1 is the applicable minimum.
 */
export const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-1.5 whitespace-nowrap",
    "font-semibold transition-all",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] focus-visible:ring-offset-1",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        /* The hero CTA: send, sign in, save. */
        default: [
          "text-white shadow-elev-1",
          "bg-[image:var(--brand-gradient)]",
          "hover:brightness-110 active:scale-[0.98]",
        ],
        /* The workhorse inside dense panels -- same weight, no gradient. */
        flat: "bg-brand text-white shadow-elev-1 hover:bg-brand-hover active:scale-[0.98]",
        /* White ground, amber edge. The prototype's "Cancel" and filter buttons. */
        secondary:
          "bg-surface text-ink border border-brand-border hover:bg-brand-surface hover:border-brand-border-strong",
        /* Tinted. New-session, tag chips, inline affordances. */
        soft: "bg-brand-surface text-brand-text border border-brand-border hover:bg-brand-surface-hover active:scale-95",
        /* Cool-neutral edge, for actions that should not read as branded. */
        outline: "bg-surface text-ink border border-line hover:bg-surface-muted hover:border-line-strong",
        ghost: "text-ink-muted hover:text-brand-text hover:bg-brand-surface",
        destructive: "bg-danger text-white shadow-elev-1 hover:brightness-110 active:scale-[0.98]",
        "destructive-ghost": "text-ink-muted hover:text-danger hover:bg-danger-surface",
        link: "text-brand-text underline-offset-4 hover:underline",
      },
      size: {
        xs: "h-6 rounded-control px-2 text-[11px]",
        sm: "h-7 rounded-control px-2.5 text-[11px]",
        default: "h-8 rounded-control px-3 text-xs",
        lg: "h-10 rounded-panel px-6 text-sm",
        icon: "size-8 rounded-control [&_svg]:size-4",
        "icon-sm": "size-6 rounded-control [&_svg]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export type ButtonVariants = VariantProps<typeof buttonVariants>;
