import { cva, type VariantProps } from "class-variance-authority";

/**
 * Status and metadata chips.
 *
 * `mono` is the design's signature: every number, latency, token count, id,
 * filename and tag renders in JetBrains Mono on a warm tint. It is a size
 * axis rather than a colour one, so it composes with any variant.
 *
 * Separate module for the same lint reason as `buttonVariants.ts`.
 */
export const badgeVariants = cva(
  "inline-flex items-center gap-1 border font-semibold whitespace-nowrap transition-colors",
  {
    variants: {
      variant: {
        brand: "bg-brand-surface text-brand-text border-brand-border",
        solid: "bg-brand text-white border-transparent",
        neutral: "bg-surface-muted text-ink-muted border-line",
        success: "bg-success-surface text-success border-success-border",
        warning: "bg-warning-surface text-warning border-warning-border",
        danger: "bg-danger-surface text-danger border-danger-border",
        info: "bg-info-surface text-info border-info-border",
        outline: "bg-transparent text-ink-muted border-line",
      },
      size: {
        xs: "px-1.5 py-0.5 text-xs rounded",
        sm: "px-2 py-0.5 text-xs rounded",
        default: "px-2.5 py-0.5 text-xs font-semibold rounded-control",
        pill: "px-2.5 py-0.5 text-xs font-semibold rounded-pill",
      },
      mono: {
        true: "font-mono",
        false: "",
      },
    },
    defaultVariants: { variant: "brand", size: "sm", mono: false },
  }
);

export type BadgeVariants = VariantProps<typeof badgeVariants>;
