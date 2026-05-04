import type { ReactNode } from "react";

type Props = {
  title: string;
  ariaLabel: string;
  open?: boolean;
  className?: string;
  children: ReactNode;
};

export function CollapsibleSection({ title, ariaLabel, open, className, children }: Props) {
  return (
    <details open={open} className={className}>
      <summary aria-label={ariaLabel}>{title}</summary>
      {children}
    </details>
  );
}
