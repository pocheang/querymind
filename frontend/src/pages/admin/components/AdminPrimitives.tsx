import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * The console's layout vocabulary, as components.
 *
 * These replace `styles/pages/admin/*`'s `.panel`, `.section-head`,
 * `.row-actions`, `.ops-kpi-*` and the long field class strings that were
 * being pasted into every `<select>` and `<input>` by hand. They are here
 * rather than in `components/ui/*` because they are the admin console's
 * register, not the app's: a KPI tile with an uppercase micro-label over a
 * mono number is a shape only this section uses.
 */

/**
 * A console panel.
 *
 * `glass-card` and nothing else, which is what the design prototype uses for
 * every surface in this view (30 of them). It carried a sci-fi corner bracket
 * until 2026-09-07 -- two borders on a `::before` -- inherited from the old
 * console's `.panel::before` rather than from the design. Migrating the old
 * ornament to Tailwind is not the same thing as adopting the new language.
 */
export function AdminPanel({
  children,
  className,
  as: Tag = "section",
}: Readonly<{ children: ReactNode; className?: string; as?: "section" | "main" | "article" | "div" }>) {
  return <Tag className={cn("glass-card rounded-card p-4", className)}>{children}</Tag>;
}

/**
 * Panel heading: uppercase title, optional description, room for actions.
 * The prototype writes every block title as plain `text-xs font-bold uppercase
 * tracking-wider` -- the amber tick this used to carry came from the old
 * `.section-head strong::before`.
 */
export function SectionHead({
  title,
  description,
  children,
  className,
}: Readonly<{ title: ReactNode; description?: ReactNode; children?: ReactNode; className?: string }>) {
  return (
    <div className={cn("flex items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        <h3 className="text-xs font-bold uppercase tracking-wider text-ink">{title}</h3>
        {description && <p className="mt-0.5 text-[11px] text-ink-muted">{description}</p>}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-1.5">{children}</div>}
    </div>
  );
}

/** A horizontal cluster of buttons. */
export function RowActions({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <div className={cn("flex flex-wrap items-center gap-1.5", className)}>{children}</div>;
}

/** Secondary copy: help text, hints, empty notes. */
export function Muted({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <p className={cn("text-[11px] leading-relaxed text-ink-muted", className)}>{children}</p>;
}

const KPI_TONE = {
  neutral: "text-brand-text-strong",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
} as const;

/**
 * A KPI tile, in the prototype's three-line rhythm: an uppercase micro-label,
 * a big mono number, and a note. The note is the line this was missing -- the
 * design uses it on 21 tiles to carry a delta or a breakdown ("P95: 1.24s |
 * P99: 2.85s"), and without it the tile is a number with no context.
 */
export function KpiCard({
  label,
  value,
  note,
  tone = "neutral",
}: Readonly<{ label: ReactNode; value: ReactNode; note?: ReactNode; tone?: keyof typeof KPI_TONE }>) {
  return (
    <div className="glass-card rounded-card p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">{label}</div>
      <div className={cn("mt-1 font-mono text-xl font-bold", KPI_TONE[tone])}>{value}</div>
      {note && <div className="mt-0.5 text-[10px] text-ink-muted">{note}</div>}
    </div>
  );
}

/**
 * The KPI grid. Explicit breakpoints, not `auto-fit minmax()`: the prototype
 * pins a column count per breakpoint so a row of six tiles becomes three then
 * two, rather than reflowing to whatever the container width divides into.
 */
export function KpiGrid({
  children,
  cols = 6,
  className,
}: Readonly<{ children: ReactNode; cols?: 4 | 5 | 6; className?: string }>) {
  const wide = { 4: "lg:grid-cols-4", 5: "lg:grid-cols-5", 6: "lg:grid-cols-6" }[cols];
  return <div className={cn("grid grid-cols-2 gap-3 md:grid-cols-3", wide, className)}>{children}</div>;
}

/** Two-up layout that collapses to one column when it runs out of room. */
export function TwoCol({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", className)}>{children}</div>;
}

/** A titled sub-panel: trend lists, chart frames, diagnostics blocks. */
export function AdminBlock({
  title,
  titleAs: TitleTag = "h4",
  children,
  className,
}: Readonly<{
  title?: ReactNode;
  titleAs?: "h3" | "h4" | "strong";
  children: ReactNode;
  className?: string;
}>) {
  return (
    <div className={cn("glass-card rounded-card space-y-3 p-4", className)}>
      {title && (
        <TitleTag className="text-xs font-bold uppercase tracking-wider text-ink">{title}</TitleTag>
      )}
      {children}
    </div>
  );
}

/** A standalone heading inside a block, in the same register as AdminBlock's. */
export function SubTitle({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <h3 className={cn("m-0 text-xs font-bold uppercase tracking-wider text-ink", className)}>{children}</h3>;
}

/** One labelled bar in a trend list. Omit `percent` for a label/value pair. */
export function TrendRow({
  label,
  title,
  value,
  percent,
}: Readonly<{ label: ReactNode; title?: string; value: ReactNode; percent?: number }>) {
  return (
    <div className="grid grid-cols-[minmax(0,140px)_1fr_auto] items-center gap-3 rounded-control p-2 transition-colors hover:bg-brand-surface-hover">
      <span className="truncate font-mono text-[11px] font-semibold text-ink-muted" title={title}>
        {label}
      </span>
      {percent === undefined ? (
        <span />
      ) : (
        <div className="relative h-3 overflow-hidden rounded-sm border border-line bg-surface-inset">
          <div
            className="relative h-full min-w-[4px] rounded-sm bg-[image:linear-gradient(90deg,var(--brand),var(--brand-hover))] transition-[width] duration-300 after:absolute after:inset-0 after:bg-[image:linear-gradient(90deg,transparent_85%,var(--bg-page)_85%)] after:bg-[length:6px_100%]"
            style={{ width: percent + "%" }}
          />
        </div>
      )}
      <strong className="min-w-10 text-right font-mono text-[11px] font-bold text-ink">{value}</strong>
    </div>
  );
}

/** A wide two-up grid: the console's `.admin-ops-grid`. */
export function OpsGrid({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <div className={cn("grid grid-cols-1 gap-4 lg:grid-cols-2", className)}>{children}</div>;
}

/** `.admin-section-block`: a spaced run of blocks under a section head. */
export function SectionBlock({
  children,
  className,
  as: Tag = "section",
}: Readonly<{ children: ReactNode; className?: string; as?: "section" | "div" }>) {
  return <Tag className={cn("mt-6 grid gap-3", className)}>{children}</Tag>;
}

/** A toolbar strip: a range picker on the left, a refresh toggle on the right. */
export function ControlsRow({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <div
      className={cn("glass-card flex flex-wrap items-center justify-between gap-3 rounded-card p-3", className)}
    >
      {children}
    </div>
  );
}

/** Fields side by side, each free to shrink. */
export function FilterRow({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <div className={cn("flex gap-3 [&>*]:min-w-0 [&>*]:flex-1", className)}>{children}</div>;
}

/** `.admin-filter-grid`: a two-column form block above a table. */
export function FilterGrid({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <div className={cn("grid grid-cols-1 gap-3.5 md:grid-cols-2", className)}>{children}</div>;
}

/**
 * A labelled control. The label WRAPS its control rather than pointing at it
 * with `htmlFor`, which is what gives the control its accessible name --
 * `AdminConfigEditor.test.tsx` finds every field by that name, so the
 * association has to survive a restyling. Same rule as `AdminFormField`.
 */
export function AdminField({
  label,
  required,
  children,
  className,
}: Readonly<{ label: ReactNode; required?: boolean; children: ReactNode; className?: string }>) {
  return (
    <label className={cn("grid gap-1.5", className)}>
      <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
        {label}
        {required && (
          <span className="ml-1 text-danger" aria-hidden="true">
            *
          </span>
        )}
      </span>
      {children}
    </label>
  );
}

/** A one-line note under a heading or a field. */
export function Hint({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return <p className={cn("-mt-1 font-mono text-[11px] text-ink-muted", className)}>{children}</p>;
}

const STATE_TONE = {
  neutral: "glass-card",
  error: "border border-danger-border bg-danger-surface",
  success: "border border-success-border bg-success-surface",
} as const;

/** The empty/error/success block a panel shows in place of its content. */
export function StatePanel({
  tone = "neutral",
  children,
  className,
}: Readonly<{ tone?: keyof typeof STATE_TONE; children: ReactNode; className?: string }>) {
  return <div className={cn("grid gap-2 rounded-card p-5", STATE_TONE[tone], className)}>{children}</div>;
}

const STATE_ICON_TONE = {
  success: "bg-success-surface text-success",
  danger: "bg-danger-surface text-danger",
  info: "bg-info-surface text-info",
  neutral: "bg-surface-muted text-ink-muted",
} as const;

/**
 * The round glyph beside a StatePanel's message. Its background is an OPAQUE
 * surface token, never an alpha tint of its own colour: an alpha tint has no
 * fixed contrast, and this exact pairing measured 4.82 over white but 4.34
 * over the aurora wash the console actually sits on.
 */
export function StateIcon({
  tone = "success",
  children,
}: Readonly<{ tone?: keyof typeof STATE_ICON_TONE; children: ReactNode }>) {
  return (
    <span
      className={cn(
        "inline-flex size-9 items-center justify-center rounded-pill text-xs font-extrabold tracking-widest",
        STATE_ICON_TONE[tone],
      )}
    >
      {children}
    </span>
  );
}

/** Loading placeholder, replacing the old `.skeleton-list`. */
export function AdminSkeleton({ rows = 3 }: Readonly<{ rows?: number }>) {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-card bg-brand-surface-hover" />
      ))}
    </div>
  );
}

/** A stacked pair of values in one table cell. */
export function CellStack({ children }: Readonly<{ children: ReactNode }>) {
  return <div className="grid min-w-0 gap-[3px]">{children}</div>;
}

const AUDIT_BADGE_TONE = {
  neutral: "border-line-strong bg-brand-surface-hover text-ink-muted",
  danger: "border-danger-border bg-danger-surface text-danger",
  warning: "border-warning-border bg-warning-surface text-warning",
  info: "border-info-border bg-info-surface text-info",
  success: "border-success-border bg-success-surface text-success",
} as const;

type BadgeTone = keyof typeof AUDIT_BADGE_TONE;

/**
 * Two vocabularies share this map, and they must: the audit log grades a row
 * `high`/`medium`/`low` while the system log carries a Python level name, and
 * both render the same chip. Anything unlisted is neutral rather than an
 * interpolated class that would silently match no rule.
 */
const SEVERITY_TONE: Record<string, BadgeTone> = {
  high: "danger",
  critical: "danger",
  error: "danger",
  medium: "warning",
  warning: "warning",
  warn: "warning",
  low: "info",
  info: "info",
  debug: "neutral",
};

const RESULT_TONE: Record<string, BadgeTone> = {
  success: "success",
  fail: "danger",
  failure: "danger",
};

/**
 * A severity or result chip.
 *
 * The tone comes from a lookup keyed on the lowered value, never from an
 * interpolated class name. A `className` built by template literal cannot be
 * checked against anything -- that is how this project once shipped a
 * `.tiny-btn.danger` rule no component ever emitted, leaving every Delete
 * button white on white.
 */
export function AuditBadge({ value, kind }: Readonly<{ value?: string | null; kind?: "severity" | "result" }>) {
  const key = (value || "").toLowerCase();
  let tone: BadgeTone = "neutral";
  if (kind === "severity") tone = SEVERITY_TONE[key] ?? "neutral";
  if (kind === "result") tone = RESULT_TONE[key] ?? "neutral";
  return (
    <span
      className={cn(
        "inline-flex min-w-16 items-center justify-center rounded border px-2 py-[3px] font-mono text-[10px] font-bold uppercase tracking-wider",
        AUDIT_BADGE_TONE[tone],
      )}
    >
      {value || "-"}
    </span>
  );
}
